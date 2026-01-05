/**
 * Cache index storage utilities using AsyncStorage.
 * Manages metadata about cached stories for offline access.
 *
 * Uses a simple promise-based mutex to prevent race conditions
 * in read-modify-write operations on the cache index.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const CACHE_INDEX_KEY = 'story_cache_index';

// Simple promise-based mutex for serializing index mutations
let indexMutex: Promise<void> = Promise.resolve();

/**
 * Execute a function with exclusive access to the cache index.
 * Ensures read-modify-write operations don't interleave.
 */
async function withIndexLock<T>(fn: () => Promise<T>): Promise<T> {
  // Capture current lock and create new one
  const previousLock = indexMutex;
  let releaseLock: () => void;
  indexMutex = new Promise(resolve => { releaseLock = resolve; });

  // Wait for previous operation to complete
  await previousLock;

  // Execute our operation
  try {
    return await fn();
  } finally {
    releaseLock!();
  }
}

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
   * Set or update a story entry in the cache index.
   * Protected by mutex to prevent race conditions.
   */
  setStoryEntry: async (storyId: string, entry: CacheEntry): Promise<void> => {
    await withIndexLock(async () => {
      const index = await cacheStorage.getIndex();
      index[storyId] = entry;
      await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
    });
  },

  /**
   * Update the lastRead timestamp for a story.
   * Protected by mutex to prevent race conditions.
   */
  updateLastRead: async (storyId: string): Promise<void> => {
    await withIndexLock(async () => {
      const index = await cacheStorage.getIndex();
      if (index[storyId]) {
        index[storyId].lastRead = Date.now();
        await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
      }
    });
  },

  /**
   * Remove a story entry from the cache index.
   * Protected by mutex to prevent race conditions.
   */
  removeStoryEntry: async (storyId: string): Promise<void> => {
    await withIndexLock(async () => {
      const index = await cacheStorage.getIndex();
      delete index[storyId];
      await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
    });
  },
};
