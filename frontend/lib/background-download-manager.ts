/**
 * BackgroundDownloadManager - Orchestrates native background downloads
 *
 * This module:
 * - Queues stories and spreads to SQLite for persistence
 * - Uses NativeDownloader for actual downloads (native thread)
 * - Updates progress and handles completion/failure
 * - Supports resuming incomplete downloads on app restart
 *
 * Downloads run on native iOS/Android threads and do NOT block the JS thread,
 * ensuring touch events remain responsive.
 */

import { Story, api } from './api';
import { NativeDownloader } from './native-downloader';
import {
  downloadQueueStorage,
  DownloadQueueEntry,
  SpreadDownloadEntry,
} from './download-queue-storage';
import { cacheFiles } from './cache-files';
import { authStorage } from './auth-storage';

// Get full absolute URL for a spread image
// Uses api.getSpreadImageUrl to ensure correct base URL
function getAbsoluteSpreadUrl(
  storyId: string,
  spreadNumber: number,
  updatedAt?: string
): string {
  return api.getSpreadImageUrl(storyId, spreadNumber, updatedAt);
}

// Convert expo-file-system URI to native path
// expo-file-system returns file:// URIs but native downloader expects plain paths
export function uriToNativePath(uri: string): string {
  // Strip file:// prefix if present
  if (uri.startsWith('file://')) {
    return uri.slice(7);
  }
  return uri;
}

export interface DownloadCallbacks {
  /** Called when all spreads for a story have been downloaded */
  onStoryComplete?: (storyId: string) => void;
  /** Called when a story download fails */
  onStoryFailed?: (storyId: string, error: string) => void;
  /** Called periodically with download progress */
  onStoryProgress?: (storyId: string, completedSpreads: number, totalSpreads: number) => void;
}

export interface DownloadProgress {
  storyId: string;
  status: 'queued' | 'downloading' | 'completed' | 'failed';
  totalSpreads: number;
  completedSpreads: number;
  percent: number;
}

// Store callbacks per story
const storyCallbacks = new Map<string, DownloadCallbacks>();

// Track stories being downloaded to avoid duplicate processing
const activeStories = new Set<string>();

// Use pipe as delimiter since story IDs are UUIDs and won't contain pipes
const DOWNLOAD_ID_DELIMITER = '|';

/**
 * Parse a download ID back to storyId and spreadNumber.
 * ID format: "storyId|spreadNumber"
 */
function parseDownloadId(id: string): { storyId: string; spreadNumber: number } | null {
  const delimiterIndex = id.lastIndexOf(DOWNLOAD_ID_DELIMITER);
  if (delimiterIndex === -1) return null;

  const storyId = id.substring(0, delimiterIndex);
  const spreadNumber = parseInt(id.substring(delimiterIndex + 1), 10);

  if (isNaN(spreadNumber)) return null;
  return { storyId, spreadNumber };
}

/**
 * Create a download ID from storyId and spreadNumber.
 */
function makeDownloadId(storyId: string, spreadNumber: number): string {
  return `${storyId}${DOWNLOAD_ID_DELIMITER}${spreadNumber}`;
}

/**
 * Handle spread download completion.
 */
async function handleSpreadComplete(
  storyId: string,
  spreadNumber: number,
  bytesDownloaded: number,
  bytesTotal: number
): Promise<void> {
  // Update spread status in SQLite
  await downloadQueueStorage.updateSpreadStatus(storyId, spreadNumber, 'completed', {
    bytesDownloaded,
    bytesTotal,
  });

  // Increment completed count
  await downloadQueueStorage.incrementCompletedSpreads(storyId);

  // Check if all spreads are done
  const pendingSpreads = await downloadQueueStorage.getPendingSpreads(storyId);

  if (pendingSpreads.length === 0) {
    // All spreads complete - mark story as complete
    await downloadQueueStorage.updateStoryStatus(storyId, 'completed', {
      completedAt: Date.now(),
    });

    // Notify callback
    const callbacks = storyCallbacks.get(storyId);
    callbacks?.onStoryComplete?.(storyId);
    storyCallbacks.delete(storyId);
    activeStories.delete(storyId);
  } else {
    // Notify progress
    const status = await downloadQueueStorage.getStoryDownloadStatus(storyId);
    if (status) {
      const callbacks = storyCallbacks.get(storyId);
      callbacks?.onStoryProgress?.(storyId, status.completedSpreads, status.totalSpreads);
    }
  }
}

/**
 * Handle spread download failure.
 */
async function handleSpreadError(
  storyId: string,
  spreadNumber: number,
  error: string
): Promise<void> {
  // Update spread status
  await downloadQueueStorage.updateSpreadStatus(storyId, spreadNumber, 'failed', {
    error,
  });

  // Mark story as failed
  await downloadQueueStorage.updateStoryStatus(storyId, 'failed', {
    lastError: `Spread ${spreadNumber} failed: ${error}`,
  });

  // Notify callback
  const callbacks = storyCallbacks.get(storyId);
  callbacks?.onStoryFailed?.(storyId, `Spread ${spreadNumber} failed: ${error}`);
  storyCallbacks.delete(storyId);
  activeStories.delete(storyId);
}

/**
 * Start downloading a spread.
 */
async function startSpreadDownload(spread: SpreadDownloadEntry): Promise<void> {
  const downloadId = makeDownloadId(spread.storyId, spread.spreadNumber);

  // Get auth token for header
  const token = await authStorage.getToken();

  // Update status to downloading
  await downloadQueueStorage.updateSpreadStatus(spread.storyId, spread.spreadNumber, 'downloading');

  // Start native download
  NativeDownloader.downloadFile({
    id: downloadId,
    url: spread.url,
    destination: spread.destination,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    onProgress: (progress) => {
      // Update progress in SQLite (fire and forget - errors logged but not blocking)
      downloadQueueStorage.updateSpreadStatus(spread.storyId, spread.spreadNumber, 'downloading', {
        bytesDownloaded: progress.bytesDownloaded,
        bytesTotal: progress.bytesTotal,
      }).catch(err => console.warn('[BackgroundDownloadManager] Failed to update progress:', err));
    },
    onComplete: (result) => {
      const parsed = parseDownloadId(result.id);
      if (parsed) {
        handleSpreadComplete(parsed.storyId, parsed.spreadNumber, result.bytesDownloaded, result.bytesTotal);
      }
    },
    onError: (error) => {
      const parsed = parseDownloadId(error.id);
      if (parsed) {
        handleSpreadError(parsed.storyId, parsed.spreadNumber, error.error);
      }
    },
  });
}

export const BackgroundDownloadManager = {
  /**
   * Queue a story for background download.
   * Returns immediately - actual download happens on native thread.
   */
  async queueStoryDownload(story: Story, callbacks?: DownloadCallbacks): Promise<void> {
    const storyId = story.id;

    // Check if already downloading
    const existingStatus = await downloadQueueStorage.getStoryDownloadStatus(storyId);
    if (existingStatus && (existingStatus.status === 'downloading' || existingStatus.status === 'queued')) {
      // Already in progress, just update callbacks
      if (callbacks) {
        storyCallbacks.set(storyId, callbacks);
      }
      return;
    }

    // Get spreads with illustrations
    const spreadsWithImages = story.spreads?.filter(s => s.illustration_url) || [];
    if (spreadsWithImages.length === 0) {
      callbacks?.onStoryFailed?.(storyId, 'No spreads with illustrations');
      return;
    }

    // Ensure directory exists (uses expo-file-system, creates at correct location)
    await cacheFiles.ensureDirectoryExists(storyId);

    // Log the destination path for debugging
    const samplePath = uriToNativePath(cacheFiles.getSpreadPath(storyId, 1));
    console.log('[BackgroundDownloadManager] Download destination:', samplePath);

    // Save story metadata
    await cacheFiles.saveStoryMetadata(storyId, story);

    // Queue story in SQLite
    const queueEntry: DownloadQueueEntry = {
      storyId,
      status: 'queued',
      totalSpreads: spreadsWithImages.length,
      completedSpreads: 0,
      queuedAt: Date.now(),
    };
    await downloadQueueStorage.queueStory(queueEntry);

    // Queue each spread
    for (const spread of spreadsWithImages) {
      // Use absolute URL - the API returns relative paths like /stories/{id}/spreads/{num}/image
      // but the native downloader needs full https:// URLs
      const absoluteUrl = getAbsoluteSpreadUrl(
        storyId,
        spread.spread_number,
        spread.illustration_updated_at
      );
      // Convert expo-file-system URI to native path (strip file:// prefix)
      const destination = uriToNativePath(cacheFiles.getSpreadPath(storyId, spread.spread_number));
      const spreadEntry: SpreadDownloadEntry = {
        storyId,
        spreadNumber: spread.spread_number,
        status: 'queued',
        url: absoluteUrl,
        destination,
      };
      await downloadQueueStorage.queueSpread(spreadEntry);
    }

    // Store callbacks
    if (callbacks) {
      storyCallbacks.set(storyId, callbacks);
    }

    // Mark story as downloading
    await downloadQueueStorage.updateStoryStatus(storyId, 'downloading', {
      startedAt: Date.now(),
    });

    activeStories.add(storyId);

    // Start downloading spreads
    const pendingSpreads = await downloadQueueStorage.getPendingSpreads(storyId);
    for (const spread of pendingSpreads) {
      await startSpreadDownload(spread);
    }
  },

  /**
   * Cancel all downloads for a story.
   */
  async cancelStoryDownload(storyId: string): Promise<void> {
    // Get all spreads to cancel
    const spreads = await downloadQueueStorage.getSpreadDownloads(storyId);

    // Cancel each native download
    for (const spread of spreads) {
      const downloadId = makeDownloadId(spread.storyId, spread.spreadNumber);
      NativeDownloader.cancelDownload(downloadId);
    }

    // Remove from queue
    await downloadQueueStorage.removeFromQueue(storyId);

    // Cleanup
    storyCallbacks.delete(storyId);
    activeStories.delete(storyId);
  },

  /**
   * Resume incomplete downloads on app startup.
   * Call this when the app initializes.
   */
  async resumeIncompleteDownloads(callbacks?: DownloadCallbacks): Promise<void> {
    // Get all incomplete stories (queued or downloading)
    const allIncomplete = await downloadQueueStorage.getIncompleteStories();

    for (const story of allIncomplete) {
      if (activeStories.has(story.storyId)) continue;

      // Store callbacks
      if (callbacks) {
        storyCallbacks.set(story.storyId, callbacks);
      }

      activeStories.add(story.storyId);

      // Mark as downloading
      await downloadQueueStorage.updateStoryStatus(story.storyId, 'downloading', {
        startedAt: Date.now(),
      });

      // Resume pending spreads
      const pendingSpreads = await downloadQueueStorage.getPendingSpreads(story.storyId);
      for (const spread of pendingSpreads) {
        await startSpreadDownload(spread);
      }
    }

    // Also reattach to any native downloads still in progress
    await NativeDownloader.reattachExistingDownloads({
      onComplete: (result) => {
        const parsed = parseDownloadId(result.id);
        if (parsed) {
          handleSpreadComplete(parsed.storyId, parsed.spreadNumber, result.bytesDownloaded, result.bytesTotal);
        }
      },
      onError: (error) => {
        const parsed = parseDownloadId(error.id);
        if (parsed) {
          handleSpreadError(parsed.storyId, parsed.spreadNumber, error.error);
        }
      },
    });
  },

  /**
   * Get download progress for a story.
   */
  async getDownloadProgress(storyId: string): Promise<DownloadProgress | null> {
    const status = await downloadQueueStorage.getStoryDownloadStatus(storyId);
    if (!status) return null;

    const percent = status.totalSpreads > 0
      ? Math.round((status.completedSpreads / status.totalSpreads) * 100)
      : 0;

    return {
      storyId: status.storyId,
      status: status.status,
      totalSpreads: status.totalSpreads,
      completedSpreads: status.completedSpreads,
      percent,
    };
  },

  /**
   * Check if a story is currently being downloaded.
   */
  isDownloading(storyId: string): boolean {
    return activeStories.has(storyId);
  },

  /**
   * Reset state (for testing).
   */
  reset(): void {
    storyCallbacks.clear();
    activeStories.clear();
    NativeDownloader.reset();
  },
};
