/**
 * StoryCacheManager - Orchestrates offline story caching
 *
 * Cached stories have their illustration_url fields transformed from API URLs
 * (e.g., '/stories/abc/spreads/1/image') to local file:// URLs
 * (e.g., 'file:///path/to/stories/abc/spread_01.png').
 * This allows the Image component to render from local disk without any
 * changes to the rendering code—it just sees a different URL scheme.
 */

import { Story, api } from './api';
import { cacheStorage, CacheEntry } from './cache-storage';
import { cacheFiles } from './cache-files';
import { queryClient } from './query-client';
import { storyKeys } from '@/features/stories/hooks';

const DOWNLOAD_CONCURRENCY = 4;
const MAX_CACHE_SIZE = 500 * 1024 * 1024; // 500MB
const ESTIMATED_SPREAD_SIZE = 700 * 1024; // 700KB average per spread

export const StoryCacheManager = {
  /**
   * Cache a story for offline access.
   * Downloads all spread images and saves metadata.
   * Atomic: if any download fails, cleans up partial data.
   */
  cacheStory: async (story: Story): Promise<boolean> => {
    if (!story.is_illustrated || !story.spreads?.length) {
      return false;
    }

    const storyId = story.id;

    try {
      // Ensure we have enough space (estimate based on spread count)
      const estimatedSize = (story.spreads?.length || 12) * ESTIMATED_SPREAD_SIZE;
      await StoryCacheManager.ensureCacheSpace(estimatedSize);

      // Create directory
      await cacheFiles.ensureDirectoryExists(storyId);

      // Download all images with concurrency limit
      const spreads = [...story.spreads];
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

      // Save metadata with transformed URLs
      await cacheFiles.saveStoryMetadata(storyId, story);

      // Get metadata size
      const metadataSize = JSON.stringify(story).length;
      totalSize += metadataSize;

      // Update index
      const entry: CacheEntry = {
        cachedAt: Date.now(),
        lastRead: Date.now(),
        sizeBytes: totalSize,
        spreadCount: story.spreads.length,
        title: story.title || 'Untitled',
      };
      await cacheStorage.setStoryEntry(storyId, entry);

      return true;
    } catch (error) {
      console.error(`Failed to cache story ${storyId}:`, error);
      // Cleanup partial download
      await cacheFiles.deleteStoryDirectory(storyId);
      return false;
    }
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

  /**
   * Hydrate the React Query client with cached story data.
   * Loads all cached stories and populates the query cache.
   */
  hydrateQueryClient: async (): Promise<void> => {
    const index = await cacheStorage.getIndex();
    const storyIds = Object.keys(index);

    if (storyIds.length === 0) return;

    console.log(`Hydrating ${storyIds.length} cached stories`);

    for (const storyId of storyIds) {
      const story = await cacheFiles.loadStoryMetadata(storyId);
      if (story) {
        queryClient.setQueryData(storyKeys.detail(storyId), story);
      }
    }
  },
};
