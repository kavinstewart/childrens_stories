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

const DOWNLOAD_CONCURRENCY = 4;

// Track in-progress caching operations to deduplicate concurrent requests
const cachingInProgress = new Map<string, Promise<boolean>>();
const MAX_CACHE_SIZE = 500 * 1024 * 1024; // 500MB
const ESTIMATED_SPREAD_SIZE = 700 * 1024; // 700KB average per spread

export const StoryCacheManager = {
  /**
   * Cache a story for offline access.
   * Downloads all spread images and saves metadata.
   * Atomic: if any download fails, cleans up partial data.
   * Deduplicates concurrent requests for the same story.
   */
  cacheStory: async (story: Story): Promise<boolean> => {
    if (!story.is_illustrated || !story.spreads?.length) {
      return false;
    }

    const storyId = story.id;

    // Deduplicate concurrent requests - return existing promise if caching is in progress
    if (cachingInProgress.has(storyId)) {
      console.log(`[Cache] Deduplicating cache request for story ${storyId}`);
      return cachingInProgress.get(storyId)!;
    }

    // Create deferred promise and set in map BEFORE any async work
    // This prevents race conditions where multiple calls pass the check above
    let resolvePromise!: (value: boolean) => void;
    const cachePromise = new Promise<boolean>(resolve => {
      resolvePromise = resolve;
    });
    cachingInProgress.set(storyId, cachePromise);

    console.log(`[Cache] Starting cache for story ${storyId}`);

    // Now start the async caching work
    (async () => {
      try {
        // Ensure we have enough space (estimate based on spread count)
        const estimatedSize = (story.spreads?.length || 12) * ESTIMATED_SPREAD_SIZE;
        await StoryCacheManager.ensureCacheSpace(estimatedSize);

        // Create directory
        console.log(`[Cache] Creating directory for story ${storyId}`);
        await cacheFiles.ensureDirectoryExists(storyId);
        console.log(`[Cache] Directory created for story ${storyId}, starting downloads`);

        // Download all images with concurrency limit
        // Only download spreads that have an illustration_url (some may be text-only)
        const spreads = story.spreads.filter(s => s.illustration_url);
        console.log(`[Cache] Downloading ${spreads.length} spreads (filtered from ${story.spreads.length} total)`);
        let totalSize = 0;

        for (let i = 0; i < spreads.length; i += DOWNLOAD_CONCURRENCY) {
          const batch = spreads.slice(i, i + DOWNLOAD_CONCURRENCY);
          console.log(`[Cache] Starting batch ${Math.floor(i / DOWNLOAD_CONCURRENCY) + 1}: spreads ${batch.map(s => s.spread_number).join(', ')}`);
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

        // Save metadata with transformed URLs
        await cacheFiles.saveStoryMetadata(storyId, story);

        // Get metadata size
        const metadataSize = JSON.stringify(story).length;
        totalSize += metadataSize;

        // Update index - use count of spreads WITH illustrations (what we actually downloaded)
        const entry: CacheEntry = {
          cachedAt: Date.now(),
          lastRead: Date.now(),
          sizeBytes: totalSize,
          spreadCount: spreads.length, // spreads with illustrations, not total
          title: story.title || 'Untitled',
        };
        await cacheStorage.setStoryEntry(storyId, entry);

        console.log(`[Cache] Caching succeeded for story ${storyId}`);
        resolvePromise(true);
      } catch (error) {
        console.error(`Failed to cache story ${storyId}:`, error);
        // Cleanup partial download
        await cacheFiles.deleteStoryDirectory(storyId);
        console.log(`[Cache] Caching failed for story ${storyId}`);
        resolvePromise(false);
      } finally {
        // Remove from in-progress map when done
        cachingInProgress.delete(storyId);
      }
    })();

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
    return cacheFiles.verifyStoryFiles(storyId, entry.spreadCount);
  },

  /**
   * Load a cached story from disk.
   * Returns story with file:// URLs for illustrations.
   * Updates lastRead timestamp for LRU tracking.
   */
  loadCachedStory: async (storyId: string): Promise<Story | null> => {
    const story = await cacheFiles.loadStoryMetadata(storyId);
    if (story) {
      // Update lastRead timestamp
      await cacheStorage.updateLastRead(storyId);
    }
    return story;
  },

  /**
   * Remove a story from the cache.
   * Deletes all files and removes from index.
   */
  evictStory: async (storyId: string): Promise<void> => {
    await cacheFiles.deleteStoryDirectory(storyId);
    await cacheStorage.removeStoryEntry(storyId);
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
   */
  loadAllCachedStories: async (): Promise<Story[]> => {
    const storyIds = await StoryCacheManager.getCachedStoryIds();
    const stories: Story[] = [];

    for (const storyId of storyIds) {
      const story = await StoryCacheManager.loadCachedStory(storyId);
      if (story) {
        stories.push(story);
      }
    }

    // Sort by created_at descending (newest first) to match API behavior
    return stories.sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
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
      console.log(`Evicted story ${storyId} to free ${entry.sizeBytes} bytes`);
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
      const valid = await cacheFiles.verifyStoryFiles(storyId, entry.spreadCount);
      if (!valid) {
        orphanedIds.push(storyId);
      }
    }

    // Remove orphaned entries
    for (const storyId of orphanedIds) {
      console.log(`Removing orphaned cache entry: ${storyId}`);
      await cacheFiles.deleteStoryDirectory(storyId);
      await cacheStorage.removeStoryEntry(storyId);
    }

    if (orphanedIds.length > 0) {
      console.log(`Cache integrity check: removed ${orphanedIds.length} orphaned entries`);
    }
  },

};
