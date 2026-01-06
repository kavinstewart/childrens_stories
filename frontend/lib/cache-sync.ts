/**
 * CacheSync - Automatic background sync manager for offline story caching
 *
 * Uses BackgroundDownloadManager for native background downloads that don't
 * block the JS thread or touch events.
 *
 * Features:
 * - Event-driven download completion via callbacks
 * - Priority ordering (newest stories first)
 * - Failure tracking with backoff
 * - Resume incomplete downloads on app restart
 * - Idempotent (safe to call multiple times)
 */

import { InteractionManager } from 'react-native';
import { Story, api } from './api';
import { StoryCacheManager } from './story-cache';
import { BackgroundDownloadManager, DownloadCallbacks } from './background-download-manager';
import { getSyncSettings, SyncSettings } from './network-aware';

// Debug logging for cache sync - set to false in production
const DEBUG = true;
const log = (...args: unknown[]) => DEBUG && console.log('[CacheSync]', ...args);

export const SYNC_CONFIG = {
  /** Maximum concurrent story downloads (global limit) */
  MAX_CONCURRENT_DOWNLOADS: 2,
  /** Maximum stories to sync in one batch */
  MAX_STORIES_PER_SYNC: 20,
  /** Minimum time between sync attempts (5 minutes) */
  SYNC_THROTTLE_MS: 5 * 60 * 1000,
  /** Delay between starting story downloads */
  INTER_STORY_DELAY_MS: 500,
  /** Base backoff time for failed downloads */
  BACKOFF_BASE_MS: 2000,
  /** Maximum backoff time */
  BACKOFF_MAX_MS: 60000,
  /** TTL for failed story entries - entries older than this are cleaned up (24 hours) */
  FAILED_ENTRY_TTL_MS: 24 * 60 * 60 * 1000,
};

interface QueuedStory {
  story: Story;
  priority: number; // Higher = more important
}

interface FailedStory {
  retryCount: number;
  nextRetryTime: number;
  firstFailedAt: number;
}

interface SyncState {
  isRunning: boolean;
  queue: QueuedStory[];
  activeDownloads: Set<string>;
  lastSyncTime: number;
  failedStories: Map<string, FailedStory>;
  abortController: AbortController | null;
}

const state: SyncState = {
  isRunning: false,
  queue: [],
  activeDownloads: new Set(),
  lastSyncTime: 0,
  failedStories: new Map(),
  abortController: null,
};

/**
 * Calculate priority score for a story (higher = download sooner)
 */
function calculatePriority(story: Story): number {
  const createdAt = story.created_at ? new Date(story.created_at).getTime() : 0;
  // Use timestamp as priority - newer stories get higher priority
  return createdAt;
}

/**
 * Check if a story is eligible for caching
 */
function isEligibleForCache(story: Story): boolean {
  return story.status === 'completed' && story.is_illustrated === true;
}

/**
 * Check if a story is in backoff period after failure
 */
function isInBackoff(storyId: string): boolean {
  const failed = state.failedStories.get(storyId);
  if (!failed) return false;
  return Date.now() < failed.nextRetryTime;
}

/**
 * Record a failed download attempt with exponential backoff
 */
function recordFailure(storyId: string): void {
  const existing = state.failedStories.get(storyId);
  const retryCount = existing ? existing.retryCount + 1 : 1;
  const backoffMs = Math.min(
    SYNC_CONFIG.BACKOFF_BASE_MS * Math.pow(2, retryCount - 1),
    SYNC_CONFIG.BACKOFF_MAX_MS
  );
  state.failedStories.set(storyId, {
    retryCount,
    nextRetryTime: Date.now() + backoffMs,
    firstFailedAt: existing?.firstFailedAt ?? Date.now(),
  });
}

/**
 * Clear failure record on success
 */
function clearFailure(storyId: string): void {
  state.failedStories.delete(storyId);
}

/**
 * Clean up old failed story entries that have exceeded the TTL.
 * This prevents unbounded memory growth from permanently failing stories.
 */
function cleanupExpiredFailures(): void {
  const now = Date.now();
  for (const [storyId, entry] of state.failedStories.entries()) {
    if (now - entry.firstFailedAt > SYNC_CONFIG.FAILED_ENTRY_TTL_MS) {
      state.failedStories.delete(storyId);
    }
  }
}

/**
 * Create download callbacks for event-driven completion handling
 */
function createDownloadCallbacks(): DownloadCallbacks {
  return {
    onStoryComplete: (storyId: string) => {
      log('Story download complete:', storyId);
      state.activeDownloads.delete(storyId);
      clearFailure(storyId);
    },
    onStoryFailed: (storyId: string, error: string) => {
      log('Story download failed:', storyId, error);
      state.activeDownloads.delete(storyId);
      recordFailure(storyId);
    },
    onStoryProgress: (storyId: string, completed: number, total: number) => {
      log('Story download progress:', storyId, `${completed}/${total}`);
    },
  };
}

export const CacheSync = {
  /**
   * Trigger a sync if conditions allow.
   * Idempotent - safe to call multiple times.
   *
   * @param stories - List of stories to potentially cache
   */
  async syncIfNeeded(stories: Story[]): Promise<void> {
    log('syncIfNeeded called with', stories.length, 'stories');

    // Check if sync is already running
    if (state.isRunning) {
      log('SKIP: sync already running');
      return;
    }

    // Check throttle - don't sync if we synced recently
    const timeSinceLastSync = Date.now() - state.lastSyncTime;
    if (state.lastSyncTime > 0 && timeSinceLastSync < SYNC_CONFIG.SYNC_THROTTLE_MS) {
      log('SKIP: throttled, last sync was', Math.round(timeSinceLastSync / 1000), 'seconds ago');
      return;
    }

    // Clean up old failure entries to prevent unbounded memory growth
    cleanupExpiredFailures();

    // Cache settings for the duration of this sync batch
    const _cachedSettings = await getSyncSettings();

    // Create AbortController for this sync session
    state.abortController = new AbortController();

    state.isRunning = true;
    state.lastSyncTime = Date.now();
    log('Starting sync...');

    try {
      await this.runSync(stories);
    } finally {
      log('Sync finished');
      state.isRunning = false;
      state.queue = [];
      state.abortController = null;
    }
  },

  /**
   * Run the actual sync process - queues stories to BackgroundDownloadManager
   * @param stories - Stories to potentially cache
   */
  async runSync(stories: Story[]): Promise<void> {
    // Get already cached story IDs
    const cachedIds = new Set(await StoryCacheManager.getCachedStoryIds());
    log('Already cached:', cachedIds.size, 'stories');

    // Filter and prioritize stories
    const eligible = stories.filter(isEligibleForCache);
    const notCached = eligible.filter(s => !cachedIds.has(s.id));
    const notDownloading = notCached.filter(s => !BackgroundDownloadManager.isDownloading(s.id));
    const notInBackoff = notDownloading.filter(s => !isInBackoff(s.id));
    const toCache = notInBackoff.slice(0, SYNC_CONFIG.MAX_STORIES_PER_SYNC);

    log('Filter results:', {
      total: stories.length,
      eligible: eligible.length,
      notCached: notCached.length,
      notDownloading: notDownloading.length,
      notInBackoff: notInBackoff.length,
      toCache: toCache.length,
    });

    if (toCache.length === 0) {
      log('Nothing to cache - all stories already cached or ineligible');
      return;
    }

    // Sort by priority (newest first)
    toCache.sort((a, b) => calculatePriority(b) - calculatePriority(a));

    // Build queue
    state.queue = toCache.map(story => ({
      story,
      priority: calculatePriority(story),
    }));
    log('Queue built with', state.queue.length, 'stories');

    // Create callbacks for download events
    const callbacks = createDownloadCallbacks();

    // Queue stories to BackgroundDownloadManager
    // The actual downloads run on native threads and won't block the JS thread
    for (const item of state.queue) {
      // Check if sync was cancelled
      if (state.abortController?.signal.aborted) {
        log('Sync cancelled, stopping queue processing');
        break;
      }

      // Fetch full story data (listStories returns summaries without spreads)
      try {
        log('Fetching full story data for:', item.story.id);
        const fullStory = await api.getStory(item.story.id);

        // Queue the download - runs on native thread
        state.activeDownloads.add(item.story.id);
        await BackgroundDownloadManager.queueStoryDownload(fullStory, callbacks);
        log('Queued story for download:', item.story.id);
      } catch (error) {
        log('Failed to fetch/queue story:', item.story.id, error);
        recordFailure(item.story.id);
      }
    }
  },

  /**
   * Boost priority of a specific story (e.g., when user opens it)
   * Moves the story to the front of the queue if it's waiting.
   */
  boostPriority(storyId: string): void {
    const idx = state.queue.findIndex(q => q.story.id === storyId);
    if (idx > 0) {
      const [item] = state.queue.splice(idx, 1);
      state.queue.unshift(item);
    }
  },

  /**
   * Get current sync status for UI display
   */
  getStatus(): { isRunning: boolean; queueLength: number; activeDownloads: number } {
    return {
      isRunning: state.isRunning,
      queueLength: state.queue.length,
      activeDownloads: state.activeDownloads.size,
    };
  },

  /**
   * Reset sync state (for testing)
   */
  reset(): void {
    state.isRunning = false;
    state.queue = [];
    state.activeDownloads.clear();
    state.lastSyncTime = 0;
    state.failedStories.clear();
    state.abortController = null;
  },

  /**
   * Cancel any in-progress sync.
   * Safe to call even if no sync is running.
   */
  cancelSync(): void {
    if (state.abortController) {
      state.abortController.abort();
    }
  },

  /**
   * Trigger a sync by fetching stories from API.
   * Convenience method for when caller doesn't have stories already.
   */
  async triggerSync(): Promise<void> {
    log('triggerSync called');
    try {
      const response = await api.listStories();
      log('API returned', response.stories.length, 'stories');
      await this.syncIfNeeded(response.stories);
    } catch (error) {
      log('triggerSync API error:', error);
      // Silently fail - network may be unavailable
    }
  },

  /**
   * Resume incomplete downloads from previous sessions.
   * Call this on app startup to continue downloads that were interrupted.
   */
  async resumeIncompleteDownloads(): Promise<void> {
    log('Resuming incomplete downloads...');
    const callbacks = createDownloadCallbacks();
    await BackgroundDownloadManager.resumeIncompleteDownloads(callbacks);
  },

  /**
   * Start automatic sync with periodic polling.
   * Call this once on app mount. Returns unsubscribe function.
   *
   * NOTE: We use polling instead of NetInfo.addEventListener because the event
   * listener blocks touch events on React Native's new architecture (Expo Go).
   * Polling every 60 seconds is a reasonable trade-off for reliable touch handling.
   *
   * All sync operations are wrapped in InteractionManager.runAfterInteractions
   * to ensure user touch events are always prioritized over background sync.
   */
  startAutoSync(): () => void {
    log('startAutoSync called - using polling (no netinfo subscription)');

    let intervalId: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;

    // Resume incomplete downloads immediately (don't wait for initial sync)
    this.resumeIncompleteDownloads();

    // Delay initial sync by 5 seconds to let app fully settle
    const initialTimeout = setTimeout(() => {
      if (cancelled) return;

      // Use InteractionManager to defer sync until after any pending interactions
      InteractionManager.runAfterInteractions(() => {
        if (cancelled) return;
        log('Initial sync after interactions complete');
        this.triggerSync();
      });

      // Then poll every 60 seconds, always deferring to interactions
      intervalId = setInterval(() => {
        if (cancelled) return;
        InteractionManager.runAfterInteractions(() => {
          if (cancelled) return;
          log('Periodic sync check after interactions');
          this.triggerSync();
        });
      }, 60_000);
    }, 5000);

    return () => {
      cancelled = true;
      clearTimeout(initialTimeout);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  },
};
