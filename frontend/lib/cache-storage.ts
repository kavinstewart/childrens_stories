/**
 * Cache index storage utilities using AsyncStorage.
 * Manages metadata about cached stories for offline access.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const CACHE_INDEX_KEY = 'story_cache_index';

export interface CacheEntry {
  cachedAt: number;
  lastRead: number;
  sizeBytes: number;
  spreadCount: number;
  title: string;
}

export type CacheIndex = Record<string, CacheEntry>;

export const cacheStorage = {
  /**
   * Retrieve the entire cache index
   */
  getIndex: async (): Promise<CacheIndex> => {
    const raw = await AsyncStorage.getItem(CACHE_INDEX_KEY);
    return raw ? JSON.parse(raw) : {};
  },

  /**
   * Set or update a story entry in the cache index
   */
  setStoryEntry: async (storyId: string, entry: CacheEntry): Promise<void> => {
    const index = await cacheStorage.getIndex();
    index[storyId] = entry;
    await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
  },

  /**
   * Update the lastRead timestamp for a story
   */
  updateLastRead: async (storyId: string): Promise<void> => {
    const index = await cacheStorage.getIndex();
    if (index[storyId]) {
      index[storyId].lastRead = Date.now();
      await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
    }
  },

  /**
   * Remove a story entry from the cache index
   */
  removeStoryEntry: async (storyId: string): Promise<void> => {
    const index = await cacheStorage.getIndex();
    delete index[storyId];
    await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
  },
};
