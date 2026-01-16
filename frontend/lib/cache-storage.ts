/**
 * Cache index storage using SQLite.
 * Manages metadata about cached stories for offline access.
 *
 * SQLite provides transactional consistency - no manual mutex needed.
 */

import * as SQLite from 'expo-sqlite';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DATABASE_NAME = 'story_cache.db';
const ASYNC_STORAGE_KEY = 'story_cache_index';

let db: SQLite.SQLiteDatabase | null = null;

/**
 * Get the database instance, creating it if needed.
 */
function getDb(): SQLite.SQLiteDatabase {
  if (!db) {
    db = SQLite.openDatabaseSync(DATABASE_NAME);
    // Create table if not exists
    db.execSync(`
      CREATE TABLE IF NOT EXISTS cached_stories (
        id TEXT PRIMARY KEY,
        cached_at INTEGER NOT NULL,
        last_read INTEGER NOT NULL,
        size_bytes INTEGER NOT NULL,
        spread_count INTEGER NOT NULL,
        title TEXT NOT NULL,
        goal TEXT NOT NULL,
        is_illustrated INTEGER NOT NULL,
        cover_spread_number INTEGER NOT NULL
      )
    `);
  }
  return db;
}

export interface CacheEntry {
  cachedAt: number;
  lastRead: number;
  sizeBytes: number;
  spreadCount: number;
  title: string;
  /** Story goal/theme for icon selection */
  goal: string;
  /** Whether the story has illustrations */
  isIllustrated: boolean;
  /** Which spread to use as cover image (usually 1) */
  coverSpreadNumber: number;
}

export type CacheIndex = Record<string, CacheEntry>;

/**
 * Migrate data from AsyncStorage to SQLite (one-time, idempotent).
 * Call this at app startup before any cache operations.
 */
export async function migrateFromAsyncStorage(): Promise<void> {
  try {
    const raw = await AsyncStorage.getItem(ASYNC_STORAGE_KEY);
    if (!raw) return; // Nothing to migrate

    const oldIndex: CacheIndex = JSON.parse(raw);
    const database = getDb();

    // Insert all entries into SQLite
    for (const [storyId, entry] of Object.entries(oldIndex)) {
      database.runSync(
        `INSERT OR REPLACE INTO cached_stories
         (id, cached_at, last_read, size_bytes, spread_count, title, goal, is_illustrated, cover_spread_number)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        storyId,
        entry.cachedAt,
        entry.lastRead,
        entry.sizeBytes,
        entry.spreadCount,
        entry.title,
        entry.goal || '',
        entry.isIllustrated ? 1 : 0,
        entry.coverSpreadNumber || 1
      );
    }

    // Delete AsyncStorage key after successful migration
    await AsyncStorage.removeItem(ASYNC_STORAGE_KEY);
  } catch (error) {
    // Log but don't throw - migration failure shouldn't block the app
    console.error('Migration from AsyncStorage failed:', error);
  }
}

/**
 * Convert a database row to a CacheEntry.
 */
function rowToEntry(row: {
  cached_at: number;
  last_read: number;
  size_bytes: number;
  spread_count: number;
  title: string;
  goal: string;
  is_illustrated: number;
  cover_spread_number: number;
}): CacheEntry {
  return {
    cachedAt: row.cached_at,
    lastRead: row.last_read,
    sizeBytes: row.size_bytes,
    spreadCount: row.spread_count,
    title: row.title,
    goal: row.goal,
    isIllustrated: row.is_illustrated === 1,
    coverSpreadNumber: row.cover_spread_number,
  };
}

export const cacheStorage = {
  /**
   * Retrieve the entire cache index.
   */
  getIndex: async (): Promise<CacheIndex> => {
    const database = getDb();
    const rows = database.getAllSync<{
      id: string;
      cached_at: number;
      last_read: number;
      size_bytes: number;
      spread_count: number;
      title: string;
      goal: string;
      is_illustrated: number;
      cover_spread_number: number;
    }>('SELECT * FROM cached_stories');

    const index: CacheIndex = {};
    for (const row of rows) {
      index[row.id] = rowToEntry(row);
    }
    return index;
  },

  /**
   * Set or update a story entry in the cache index.
   */
  setStoryEntry: async (storyId: string, entry: CacheEntry): Promise<void> => {
    const database = getDb();
    database.runSync(
      `INSERT OR REPLACE INTO cached_stories
       (id, cached_at, last_read, size_bytes, spread_count, title, goal, is_illustrated, cover_spread_number)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      storyId,
      entry.cachedAt,
      entry.lastRead,
      entry.sizeBytes,
      entry.spreadCount,
      entry.title,
      entry.goal,
      entry.isIllustrated ? 1 : 0,
      entry.coverSpreadNumber
    );
  },

  /**
   * Update the lastRead timestamp for a story.
   */
  updateLastRead: async (storyId: string): Promise<void> => {
    const database = getDb();
    database.runSync(
      'UPDATE cached_stories SET last_read = ? WHERE id = ?',
      Date.now(),
      storyId
    );
  },

  /**
   * Remove a story entry from the cache index.
   */
  removeStoryEntry: async (storyId: string): Promise<void> => {
    const database = getDb();
    database.runSync('DELETE FROM cached_stories WHERE id = ?', storyId);
  },
};

/**
 * Reset the database connection (for testing).
 */
export function _resetDbForTesting(): void {
  if (db) {
    db.closeSync();
    db = null;
  }
}
