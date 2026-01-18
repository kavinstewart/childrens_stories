/**
 * Download queue storage using SQLite.
 * Tracks story downloads and per-spread progress for background sync.
 *
 * Schema:
 * - download_queue: Story-level download status
 * - spread_downloads: Per-spread download tracking
 */

import * as SQLite from 'expo-sqlite';

const DATABASE_NAME = 'story_cache.db';

let db: SQLite.SQLiteDatabase | null = null;

export type DownloadStatus = 'queued' | 'downloading' | 'completed' | 'failed';

export interface DownloadQueueEntry {
  storyId: string;
  status: DownloadStatus;
  totalSpreads: number;
  completedSpreads: number;
  queuedAt: number;
  startedAt?: number;
  completedAt?: number;
  lastError?: string;
  retryCount?: number;
  nextRetryAt?: number;
}

export interface SpreadDownloadEntry {
  storyId: string;
  spreadNumber: number;
  status: DownloadStatus;
  url: string;
  destination: string;
  bytesDownloaded?: number;
  bytesTotal?: number;
  error?: string;
}

/**
 * Get the database instance, creating tables if needed.
 */
function getDb(): SQLite.SQLiteDatabase {
  if (!db) {
    db = SQLite.openDatabaseSync(DATABASE_NAME);

    // Create download_queue table
    db.execSync(`
      CREATE TABLE IF NOT EXISTS download_queue (
        story_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        total_spreads INTEGER NOT NULL,
        completed_spreads INTEGER NOT NULL DEFAULT 0,
        queued_at INTEGER NOT NULL,
        started_at INTEGER,
        completed_at INTEGER,
        last_error TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        next_retry_at INTEGER
      )
    `);

    // Create spread_downloads table
    db.execSync(`
      CREATE TABLE IF NOT EXISTS spread_downloads (
        id TEXT PRIMARY KEY,
        story_id TEXT NOT NULL,
        spread_number INTEGER NOT NULL,
        status TEXT NOT NULL,
        url TEXT NOT NULL,
        destination TEXT NOT NULL,
        bytes_downloaded INTEGER DEFAULT 0,
        bytes_total INTEGER DEFAULT 0,
        error TEXT
      )
    `);
  }
  return db;
}

/**
 * Convert a database row to a DownloadQueueEntry.
 */
function rowToQueueEntry(row: {
  story_id: string;
  status: string;
  total_spreads: number;
  completed_spreads: number;
  queued_at: number;
  started_at: number | null;
  completed_at: number | null;
  last_error: string | null;
  retry_count: number;
  next_retry_at: number | null;
}): DownloadQueueEntry {
  return {
    storyId: row.story_id,
    status: row.status as DownloadStatus,
    totalSpreads: row.total_spreads,
    completedSpreads: row.completed_spreads,
    queuedAt: row.queued_at,
    startedAt: row.started_at ?? undefined,
    completedAt: row.completed_at ?? undefined,
    lastError: row.last_error ?? undefined,
    retryCount: row.retry_count,
    nextRetryAt: row.next_retry_at ?? undefined,
  };
}

/**
 * Convert a database row to a SpreadDownloadEntry.
 */
function rowToSpreadEntry(row: {
  story_id: string;
  spread_number: number;
  status: string;
  url: string;
  destination: string;
  bytes_downloaded: number;
  bytes_total: number;
  error: string | null;
}): SpreadDownloadEntry {
  return {
    storyId: row.story_id,
    spreadNumber: row.spread_number,
    status: row.status as DownloadStatus,
    url: row.url,
    destination: row.destination,
    bytesDownloaded: row.bytes_downloaded,
    bytesTotal: row.bytes_total,
    error: row.error ?? undefined,
  };
}

export const downloadQueueStorage = {
  /**
   * Add a story to the download queue.
   */
  queueStory: async (entry: DownloadQueueEntry): Promise<void> => {
    const database = getDb();
    database.runSync(
      `INSERT OR REPLACE INTO download_queue
       (story_id, status, total_spreads, completed_spreads, queued_at, started_at, completed_at, last_error, retry_count, next_retry_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      entry.storyId,
      entry.status,
      entry.totalSpreads,
      entry.completedSpreads,
      entry.queuedAt,
      entry.startedAt ?? null,
      entry.completedAt ?? null,
      entry.lastError ?? null,
      entry.retryCount ?? 0,
      entry.nextRetryAt ?? null
    );
  },

  /**
   * Update a story's download status.
   */
  updateStoryStatus: async (
    storyId: string,
    status: DownloadStatus,
    updates?: {
      startedAt?: number;
      completedAt?: number;
      lastError?: string;
      retryCount?: number;
      nextRetryAt?: number;
    }
  ): Promise<void> => {
    const database = getDb();

    // Build dynamic update
    const setClauses = ['status = ?'];
    const params: (string | number | null)[] = [status];

    if (updates?.startedAt !== undefined) {
      setClauses.push('started_at = ?');
      params.push(updates.startedAt);
    }
    if (updates?.completedAt !== undefined) {
      setClauses.push('completed_at = ?');
      params.push(updates.completedAt);
    }
    if (updates?.lastError !== undefined) {
      setClauses.push('last_error = ?');
      params.push(updates.lastError);
    }
    if (updates?.retryCount !== undefined) {
      setClauses.push('retry_count = ?');
      params.push(updates.retryCount);
    }
    if (updates?.nextRetryAt !== undefined) {
      setClauses.push('next_retry_at = ?');
      params.push(updates.nextRetryAt);
    }

    params.push(storyId);

    database.runSync(
      `UPDATE download_queue SET ${setClauses.join(', ')} WHERE story_id = ?`,
      ...params
    );
  },

  /**
   * Increment the completed spread count for a story.
   */
  incrementCompletedSpreads: async (storyId: string): Promise<void> => {
    const database = getDb();
    database.runSync(
      'UPDATE download_queue SET completed_spreads = completed_spreads + 1 WHERE story_id = ?',
      storyId
    );
  },

  /**
   * Get all stories with 'queued' status.
   */
  getQueuedStories: async (): Promise<DownloadQueueEntry[]> => {
    const database = getDb();
    const rows = database.getAllSync<{
      story_id: string;
      status: string;
      total_spreads: number;
      completed_spreads: number;
      queued_at: number;
      started_at: number | null;
      completed_at: number | null;
      last_error: string | null;
      retry_count: number;
      next_retry_at: number | null;
    }>("SELECT * FROM download_queue WHERE status = 'queued' ORDER BY queued_at ASC");

    return rows.map(rowToQueueEntry);
  },

  /**
   * Get all incomplete stories (queued or downloading).
   */
  getIncompleteStories: async (): Promise<DownloadQueueEntry[]> => {
    const database = getDb();
    const rows = database.getAllSync<{
      story_id: string;
      status: string;
      total_spreads: number;
      completed_spreads: number;
      queued_at: number;
      started_at: number | null;
      completed_at: number | null;
      last_error: string | null;
      retry_count: number;
      next_retry_at: number | null;
    }>("SELECT * FROM download_queue WHERE status IN ('queued', 'downloading') ORDER BY queued_at ASC");

    return rows.map(rowToQueueEntry);
  },

  /**
   * Get download status for a specific story.
   */
  getStoryDownloadStatus: async (storyId: string): Promise<DownloadQueueEntry | null> => {
    const database = getDb();
    const row = database.getFirstSync<{
      story_id: string;
      status: string;
      total_spreads: number;
      completed_spreads: number;
      queued_at: number;
      started_at: number | null;
      completed_at: number | null;
      last_error: string | null;
      retry_count: number;
      next_retry_at: number | null;
    }>('SELECT * FROM download_queue WHERE story_id = ?', storyId);

    return row ? rowToQueueEntry(row) : null;
  },

  /**
   * Remove a story from the download queue.
   * Also removes associated spread downloads.
   */
  removeFromQueue: async (storyId: string): Promise<void> => {
    const database = getDb();
    database.runSync('DELETE FROM spread_downloads WHERE story_id = ?', storyId);
    database.runSync('DELETE FROM download_queue WHERE story_id = ?', storyId);
  },

  /**
   * Get IDs of all completed downloads.
   */
  getCompletedStoryIds: async (): Promise<string[]> => {
    const database = getDb();
    const rows = database.getAllSync<{ story_id: string }>(
      "SELECT story_id FROM download_queue WHERE status = 'completed'"
    );
    return rows.map(row => row.story_id);
  },

  /**
   * Add a spread to the download queue.
   */
  queueSpread: async (entry: SpreadDownloadEntry): Promise<void> => {
    const database = getDb();
    const id = `${entry.storyId}:${entry.spreadNumber}`;
    database.runSync(
      `INSERT OR REPLACE INTO spread_downloads
       (id, story_id, spread_number, status, url, destination, bytes_downloaded, bytes_total, error)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      id,
      entry.storyId,
      entry.spreadNumber,
      entry.status,
      entry.url,
      entry.destination,
      entry.bytesDownloaded ?? 0,
      entry.bytesTotal ?? 0,
      entry.error ?? null
    );
  },

  /**
   * Update a spread's download status.
   */
  updateSpreadStatus: async (
    storyId: string,
    spreadNumber: number,
    status: DownloadStatus,
    updates?: {
      bytesDownloaded?: number;
      bytesTotal?: number;
      error?: string;
    }
  ): Promise<void> => {
    const database = getDb();
    const id = `${storyId}:${spreadNumber}`;

    const setClauses = ['status = ?'];
    const params: (string | number | null)[] = [status];

    if (updates?.bytesDownloaded !== undefined) {
      setClauses.push('bytes_downloaded = ?');
      params.push(updates.bytesDownloaded);
    }
    if (updates?.bytesTotal !== undefined) {
      setClauses.push('bytes_total = ?');
      params.push(updates.bytesTotal);
    }
    if (updates?.error !== undefined) {
      setClauses.push('error = ?');
      params.push(updates.error);
    }

    params.push(id);

    database.runSync(
      `UPDATE spread_downloads SET ${setClauses.join(', ')} WHERE id = ?`,
      ...params
    );
  },

  /**
   * Get all spread downloads for a story.
   */
  getSpreadDownloads: async (storyId: string): Promise<SpreadDownloadEntry[]> => {
    const database = getDb();
    const rows = database.getAllSync<{
      story_id: string;
      spread_number: number;
      status: string;
      url: string;
      destination: string;
      bytes_downloaded: number;
      bytes_total: number;
      error: string | null;
    }>(
      'SELECT * FROM spread_downloads WHERE story_id = ? ORDER BY spread_number ASC',
      storyId
    );

    return rows.map(rowToSpreadEntry);
  },

  /**
   * Get spreads that are not yet completed for a story.
   */
  getPendingSpreads: async (storyId: string): Promise<SpreadDownloadEntry[]> => {
    const database = getDb();
    const rows = database.getAllSync<{
      story_id: string;
      spread_number: number;
      status: string;
      url: string;
      destination: string;
      bytes_downloaded: number;
      bytes_total: number;
      error: string | null;
    }>(
      "SELECT * FROM spread_downloads WHERE story_id = ? AND status != 'completed' ORDER BY spread_number ASC",
      storyId
    );

    return rows.map(rowToSpreadEntry);
  },

  /**
   * Remove all completed downloads from the queue.
   */
  clearCompletedDownloads: async (): Promise<void> => {
    const database = getDb();
    // First get completed story IDs to clean up spread_downloads
    const completed = database.getAllSync<{ story_id: string }>(
      "SELECT story_id FROM download_queue WHERE status = 'completed'"
    );
    for (const row of completed) {
      database.runSync('DELETE FROM spread_downloads WHERE story_id = ?', row.story_id);
    }
    database.runSync("DELETE FROM download_queue WHERE status = 'completed'");
  },

  /**
   * Clear all download queue data.
   */
  clearAllDownloads: async (): Promise<void> => {
    const database = getDb();
    database.runSync('DELETE FROM spread_downloads');
    database.runSync('DELETE FROM download_queue');
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
