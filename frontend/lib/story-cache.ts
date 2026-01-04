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

const DOWNLOAD_CONCURRENCY = 4;

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

        if (results.some(r => !r.success)) {
          throw new Error('Some downloads failed');
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
};
