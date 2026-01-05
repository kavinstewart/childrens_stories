/**
 * StoryCacheManager - Orchestrates offline story caching
 *
 * Downloads spread images to local storage. Cached story metadata retains
 * original server URLs - file:// paths are computed at render time using
 * cacheFiles.getSpreadPath() when isCached is true.
 */

import { Story, api } from './api';
import { cacheStorage, CacheEntry } from './cache-storage';
import { cacheFiles } from './cache-files';
// NOTE: Do NOT import CacheSync here - it creates a require cycle that can freeze the JS thread

// Debug logging for story cache - set to false in production
const DEBUG = true;
const log = (...args: unknown[]) => DEBUG && console.log('[StoryCache]', ...args);

const DOWNLOAD_CONCURRENCY = 4;

// Track in-progress caching operations to deduplicate concurrent requests
const cachingInProgress = new Map<string, Promise<boolean>>();
const MAX_CACHE_SIZE = 500 * 1024 * 1024; // 500MB
const ESTIMATED_SPREAD_SIZE = 700 * 1024; // 700KB average per spread

/**
 * Lightweight story summary for list views.
 * Contains only the fields needed for StoryCard rendering,
 * avoiding the need to load full metadata files.
 */
export interface CachedStorySummary {
  id: string;
  title: string;
  goal: string;
  is_illustrated: boolean;
  isCached: true;
  coverSpreadNumber: number;
}

export const StoryCacheManager = {
  /**
   * Cache a story for offline access.
   * Downloads all spread images and saves metadata.
   * Atomic: if any download fails, cleans up partial data.
   * Deduplicates concurrent requests for the same story.
   */
  cacheStory: async (story: Story): Promise<boolean> => {
    log('cacheStory called for:', story.id, 'is_illustrated:', story.is_illustrated, 'spreads:', story.spreads?.length);
    if (!story.is_illustrated || !story.spreads?.length) {
      log('SKIP: not illustrated or no spreads');
      return false;
    }

    const storyId = story.id;

    // Deduplicate concurrent requests - return existing promise if caching is in progress
    if (cachingInProgress.has(storyId)) {
      return cachingInProgress.get(storyId)!;
    }

    // Create the caching work as a self-contained promise
    // This replaces the deferred pattern to ensure the promise always resolves
    const cachePromise = (async (): Promise<boolean> => {
      try {
        // Ensure we have enough space (estimate based on spread count)
        const estimatedSize = (story.spreads?.length || 12) * ESTIMATED_SPREAD_SIZE;
        log('Ensuring cache space for', estimatedSize, 'bytes');
        await StoryCacheManager.ensureCacheSpace(estimatedSize);

        // Create directory
        log('Creating directory for', storyId);
        await cacheFiles.ensureDirectoryExists(storyId);

        // Download all images with concurrency limit
        // Only download spreads that have an illustration_url (some may be text-only)
        const spreads = story.spreads!.filter(s => s.illustration_url);
        log('Downloading', spreads.length, 'spreads with illustrations');
        let totalSize = 0;

        for (let i = 0; i < spreads.length; i += DOWNLOAD_CONCURRENCY) {
          const batch = spreads.slice(i, i + DOWNLOAD_CONCURRENCY);
          const results = await Promise.all(
            batch.map(spread => {
              const url = api.getSpreadImageUrl(
                storyId,
                spread.spread_number,
                spread.illustration_updated_at
              );
              return cacheFiles.downloadSpreadImage(storyId, spread.spread_number, url);
            })
          );

          const failedIndices = results
            .map((r, idx) => (!r.success ? batch[idx].spread_number : null))
            .filter((n): n is number => n !== null);
          if (failedIndices.length > 0) {
            throw new Error(`Downloads failed for spreads: ${failedIndices.join(', ')}`);
          }

          totalSize += results.reduce((sum, r) => sum + r.size, 0);
        }

        // Save metadata
        await cacheFiles.saveStoryMetadata(storyId, story);

        // Get metadata size
        const metadataSize = JSON.stringify(story).length;
        totalSize += metadataSize;

        // Update index - use count of spreads WITH illustrations (what we actually downloaded)
        // Find the first spread with an illustration for the cover
        const coverSpread = story.spreads?.find(s => s.illustration_url);
        const entry: CacheEntry = {
          cachedAt: Date.now(),
          lastRead: Date.now(),
          sizeBytes: totalSize,
          spreadCount: spreads.length, // spreads with illustrations, not total
          title: story.title || 'Untitled',
          goal: story.goal || '',
          isIllustrated: story.is_illustrated ?? false,
          coverSpreadNumber: coverSpread?.spread_number ?? 1,
        };
        await cacheStorage.setStoryEntry(storyId, entry);

        return true;
      } catch (error) {
        log('ERROR caching story', storyId, ':', error);
        // Cleanup partial data - remove from index first (atomic), then files
        try {
          await cacheStorage.removeStoryEntry(storyId);
          await cacheFiles.deleteStoryDirectory(storyId);
        } catch {
          // Ignore cleanup errors
        }
        return false;
      } finally {
        // Remove from in-progress map when done - this ALWAYS runs
        cachingInProgress.delete(storyId);
      }
    })();

    // Set in map BEFORE returning so concurrent calls can deduplicate
    cachingInProgress.set(storyId, cachePromise);

    return cachePromise;
  },

  /**
   * Check if a story is cached and all files are present.
   */
  isStoryCached: async (storyId: string): Promise<boolean> => {
    const index = await cacheStorage.getIndex();
    const entry = index[storyId];
    if (!entry) return false;

    // Verify files actually exist
    return cacheFiles.verifyStoryFiles(storyId);
  },

  /**
   * Load a cached story from disk.
   * Returns story with isCached flag set - file:// paths computed at render time.
   * Updates lastRead timestamp for LRU tracking.
   */
  loadCachedStory: async (storyId: string): Promise<Story | null> => {
    const story = await cacheFiles.loadStoryMetadata(storyId);
    if (story) {
      // Mark as cached so UI can compute file:// paths at render time
      story.isCached = true;
      // Update lastRead timestamp
      await cacheStorage.updateLastRead(storyId);
    }
    return story;
  },

  /**
   * Remove a story from the cache.
   * Removes from index FIRST (fail-safe), then deletes files.
   * If crash between: orphaned files are cleaned up by verifyCacheIntegrity().
   */
  evictStory: async (storyId: string): Promise<void> => {
    // Remove from index first - ensures isStoryCached() returns false even if file delete fails
    await cacheStorage.removeStoryEntry(storyId);
    await cacheFiles.deleteStoryDirectory(storyId);
  },

  /**
   * Invalidate a cached story (forces re-download on next read).
   * Currently same as evict.
   */
  invalidateStory: async (storyId: string): Promise<void> => {
    await StoryCacheManager.evictStory(storyId);
  },

  /**
   * Get total size of all cached stories in bytes.
   */
  getCacheSize: async (): Promise<number> => {
    const index = await cacheStorage.getIndex();
    return Object.values(index).reduce((sum, entry) => sum + entry.sizeBytes, 0);
  },

  /**
   * Get list of all cached story IDs.
   */
  getCachedStoryIds: async (): Promise<string[]> => {
    const index = await cacheStorage.getIndex();
    return Object.keys(index);
  },

  /**
   * Load all cached stories from disk.
   * Returns array of stories with file:// URLs for illustrations.
   * Loads stories in parallel for better performance.
   */
  loadAllCachedStories: async (): Promise<Story[]> => {
    const storyIds = await StoryCacheManager.getCachedStoryIds();

    // Load all stories in parallel - file reads don't contend
    const loadedStories = await Promise.all(
      storyIds.map(storyId => StoryCacheManager.loadCachedStory(storyId))
    );

    // Filter out null results (stories that failed to load)
    const stories = loadedStories.filter((story): story is Story => story !== null);

    // Sort by created_at descending (newest first) to match API behavior
    return stories.sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
    });
  },

  /**
   * Get lightweight summaries of all cached stories from the index.
   * Does NOT load metadata files - uses only index data.
   * Ideal for list views where only basic info is needed for StoryCard rendering.
   */
  getCachedStorySummaries: async (): Promise<CachedStorySummary[]> => {
    const index = await cacheStorage.getIndex();
    const entries = Object.entries(index);

    // Map index entries to summaries with the shape StoryCard needs
    const summaries: CachedStorySummary[] = entries.map(([storyId, entry]) => ({
      id: storyId,
      title: entry.title,
      goal: entry.goal,
      is_illustrated: entry.isIllustrated,
      isCached: true,
      coverSpreadNumber: entry.coverSpreadNumber,
    }));

    // Sort by cachedAt descending (newest first)
    return summaries.sort((a, b) => {
      const entryA = index[a.id];
      const entryB = index[b.id];
      return entryB.cachedAt - entryA.cachedAt;
    });
  },

  /**
   * Ensure there's enough space for a new story.
   * Evicts oldest-read stories (LRU) if needed.
   */
  ensureCacheSpace: async (neededBytes: number): Promise<void> => {
    const index = await cacheStorage.getIndex();
    const currentSize = Object.values(index).reduce((sum, e) => sum + e.sizeBytes, 0);

    if (currentSize + neededBytes <= MAX_CACHE_SIZE) {
      return; // Enough space
    }

    // Sort by lastRead ascending (oldest first)
    const sorted = Object.entries(index).sort(([, a], [, b]) => a.lastRead - b.lastRead);

    let freedSpace = 0;
    const needed = currentSize + neededBytes - MAX_CACHE_SIZE;

    for (const [storyId, entry] of sorted) {
      if (freedSpace >= needed) break;

      await StoryCacheManager.evictStory(storyId);
      freedSpace += entry.sizeBytes;
    }
  },

  /**
   * Clear all cached stories.
   */
  clearAllCache: async (): Promise<void> => {
    const storyIds = await StoryCacheManager.getCachedStoryIds();
    for (const storyId of storyIds) {
      await StoryCacheManager.evictStory(storyId);
    }
  },

  /**
   * Verify cache integrity by checking that all indexed stories have valid files.
   * Removes orphaned entries where files are missing.
   */
  verifyCacheIntegrity: async (): Promise<void> => {
    const index = await cacheStorage.getIndex();
    const orphanedIds: string[] = [];

    for (const [storyId, entry] of Object.entries(index)) {
      const valid = await cacheFiles.verifyStoryFiles(storyId);
      if (!valid) {
        orphanedIds.push(storyId);
      }
    }

    // Remove orphaned entries (index first for crash safety)
    for (const storyId of orphanedIds) {
      await cacheStorage.removeStoryEntry(storyId);
      await cacheFiles.deleteStoryDirectory(storyId);
    }
  },

  /**
   * Boost the priority of a story in the sync queue.
   * Call this when a user views a story to ensure it downloads first.
   * NOTE: Callers should use CacheSync.boostPriority() directly to avoid require cycle.
   * @deprecated Use CacheSync.boostPriority() directly
   */
  boostStoryPriority: (_storyId: string): void => {
    // No-op: removed to break require cycle. Use CacheSync.boostPriority() directly.
  },

};
