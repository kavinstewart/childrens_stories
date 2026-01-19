/**
 * Tests for download-queue-storage.ts
 * TDD: Write tests first, then implement
 *
 * This module extends the SQLite schema to track:
 * - Download queue (story-level status)
 * - Per-spread download progress
 */

// Mock expo-sqlite
jest.mock('expo-sqlite', () => {
  const mockDb = {
    execSync: jest.fn(),
    runSync: jest.fn(),
    getAllSync: jest.fn(() => []),
    getFirstSync: jest.fn(() => null),
    closeSync: jest.fn(),
  };
  return {
    openDatabaseSync: jest.fn(() => mockDb),
    __mockDb: mockDb,
  };
});

import * as SQLite from 'expo-sqlite';
import {
  downloadQueueStorage,
  DownloadQueueEntry,
  SpreadDownloadEntry,
  DownloadStatus,
  _resetDbForTesting,
} from '../../lib/download-queue-storage';

const mockDb = (SQLite as unknown as { __mockDb: ReturnType<typeof SQLite.openDatabaseSync> }).__mockDb;

describe('downloadQueueStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    _resetDbForTesting();
  });

  describe('schema creation', () => {
    it('should create download_queue table on first access', async () => {
      await downloadQueueStorage.getQueuedStories();

      expect(mockDb.execSync).toHaveBeenCalledWith(
        expect.stringContaining('CREATE TABLE IF NOT EXISTS download_queue')
      );
    });

    it('should create spread_downloads table on first access', async () => {
      await downloadQueueStorage.getQueuedStories();

      expect(mockDb.execSync).toHaveBeenCalledWith(
        expect.stringContaining('CREATE TABLE IF NOT EXISTS spread_downloads')
      );
    });
  });

  describe('queueStory', () => {
    it('should insert a new story into the download queue', async () => {
      const entry: DownloadQueueEntry = {
        storyId: 'story-123',
        status: 'queued',
        totalSpreads: 12,
        completedSpreads: 0,
        queuedAt: Date.now(),
      };

      await downloadQueueStorage.queueStory(entry);

      expect(mockDb.runSync).toHaveBeenCalledWith(
        expect.stringContaining('INSERT OR REPLACE INTO download_queue'),
        'story-123',  // storyId
        'queued',     // status
        12,           // totalSpreads
        0,            // completedSpreads
        expect.any(Number), // queuedAt
        null,         // startedAt
        null,         // completedAt
        null,         // lastError
        0,            // retryCount
        null          // nextRetryAt
      );
    });
  });

  describe('updateStoryStatus', () => {
    it('should update story status to downloading', async () => {
      await downloadQueueStorage.updateStoryStatus('story-123', 'downloading', {
        startedAt: Date.now(),
      });

      expect(mockDb.runSync).toHaveBeenCalledWith(
        expect.stringContaining('UPDATE download_queue'),
        expect.anything(),
        expect.anything(),
        expect.anything()
      );
    });

    it('should update story status to completed', async () => {
      await downloadQueueStorage.updateStoryStatus('story-123', 'completed', {
        completedAt: Date.now(),
      });

      expect(mockDb.runSync).toHaveBeenCalled();
    });

    it('should update story status to failed with error', async () => {
      await downloadQueueStorage.updateStoryStatus('story-123', 'failed', {
        lastError: 'Network error',
        retryCount: 1,
        nextRetryAt: Date.now() + 5000,
      });

      expect(mockDb.runSync).toHaveBeenCalled();
    });
  });

  describe('incrementCompletedSpreads', () => {
    it('should increment the completed spread count', async () => {
      await downloadQueueStorage.incrementCompletedSpreads('story-123');

      expect(mockDb.runSync).toHaveBeenCalledWith(
        expect.stringContaining('UPDATE download_queue SET completed_spreads = completed_spreads + 1'),
        expect.anything()
      );
    });
  });

  describe('getQueuedStories', () => {
    it('should return all stories with queued status', async () => {
      const mockRows = [
        {
          story_id: 'story-1',
          status: 'queued',
          total_spreads: 12,
          completed_spreads: 0,
          queued_at: 1000,
          started_at: null,
          completed_at: null,
          last_error: null,
          retry_count: 0,
          next_retry_at: null,
        },
      ];
      (mockDb.getAllSync as jest.Mock).mockReturnValueOnce(mockRows);

      const result = await downloadQueueStorage.getQueuedStories();

      expect(result).toHaveLength(1);
      expect(result[0].storyId).toBe('story-1');
      expect(result[0].status).toBe('queued');
    });
  });

  describe('getStoryDownloadStatus', () => {
    it('should return null if story not in queue', async () => {
      (mockDb.getFirstSync as jest.Mock).mockReturnValueOnce(null);

      const result = await downloadQueueStorage.getStoryDownloadStatus('nonexistent');

      expect(result).toBeNull();
    });

    it('should return story download status if exists', async () => {
      const mockRow = {
        story_id: 'story-123',
        status: 'downloading',
        total_spreads: 12,
        completed_spreads: 5,
        queued_at: 1000,
        started_at: 2000,
        completed_at: null,
        last_error: null,
        retry_count: 0,
        next_retry_at: null,
      };
      (mockDb.getFirstSync as jest.Mock).mockReturnValueOnce(mockRow);

      const result = await downloadQueueStorage.getStoryDownloadStatus('story-123');

      expect(result).not.toBeNull();
      expect(result?.status).toBe('downloading');
      expect(result?.completedSpreads).toBe(5);
    });
  });

  describe('removeFromQueue', () => {
    it('should delete story from download queue', async () => {
      await downloadQueueStorage.removeFromQueue('story-123');

      expect(mockDb.runSync).toHaveBeenCalledWith(
        expect.stringContaining('DELETE FROM download_queue'),
        expect.anything()
      );
    });

    it('should also delete associated spread downloads', async () => {
      await downloadQueueStorage.removeFromQueue('story-123');

      expect(mockDb.runSync).toHaveBeenCalledWith(
        expect.stringContaining('DELETE FROM spread_downloads'),
        expect.anything()
      );
    });
  });

  describe('getCompletedStoryIds', () => {
    it('should return IDs of all completed downloads', async () => {
      const mockRows = [{ story_id: 'story-1' }, { story_id: 'story-2' }];
      (mockDb.getAllSync as jest.Mock).mockReturnValueOnce(mockRows);

      const result = await downloadQueueStorage.getCompletedStoryIds();

      expect(result).toEqual(['story-1', 'story-2']);
    });
  });

  describe('spread downloads', () => {
    describe('queueSpread', () => {
      it('should insert a spread download entry', async () => {
        const entry: SpreadDownloadEntry = {
          storyId: 'story-123',
          spreadNumber: 1,
          status: 'queued',
          url: 'https://example.com/spread1.png',
          destination: '/path/to/spread1.png',
        };

        await downloadQueueStorage.queueSpread(entry);

        expect(mockDb.runSync).toHaveBeenCalledWith(
          expect.stringContaining('INSERT OR REPLACE INTO spread_downloads'),
          'story-123:1', // id
          'story-123',   // storyId
          1,             // spreadNumber
          'queued',      // status
          'https://example.com/spread1.png', // url
          '/path/to/spread1.png', // destination
          0,             // bytesDownloaded
          0,             // bytesTotal
          null           // error
        );
      });
    });

    describe('updateSpreadStatus', () => {
      it('should update spread download status', async () => {
        await downloadQueueStorage.updateSpreadStatus('story-123', 1, 'completed', {
          bytesDownloaded: 50000,
          bytesTotal: 50000,
        });

        expect(mockDb.runSync).toHaveBeenCalled();
      });
    });

    describe('getSpreadDownloads', () => {
      it('should return all spreads for a story', async () => {
        const mockRows = [
          {
            story_id: 'story-123',
            spread_number: 1,
            status: 'completed',
            url: 'https://example.com/1.png',
            destination: '/path/1.png',
            bytes_downloaded: 50000,
            bytes_total: 50000,
            error: null,
          },
          {
            story_id: 'story-123',
            spread_number: 2,
            status: 'queued',
            url: 'https://example.com/2.png',
            destination: '/path/2.png',
            bytes_downloaded: 0,
            bytes_total: 0,
            error: null,
          },
        ];
        (mockDb.getAllSync as jest.Mock).mockReturnValueOnce(mockRows);

        const result = await downloadQueueStorage.getSpreadDownloads('story-123');

        expect(result).toHaveLength(2);
        expect(result[0].spreadNumber).toBe(1);
        expect(result[0].status).toBe('completed');
      });
    });

    describe('getPendingSpreads', () => {
      it('should return spreads that are not completed', async () => {
        const mockRows = [
          {
            story_id: 'story-123',
            spread_number: 2,
            status: 'queued',
            url: 'https://example.com/2.png',
            destination: '/path/2.png',
            bytes_downloaded: 0,
            bytes_total: 0,
            error: null,
          },
        ];
        (mockDb.getAllSync as jest.Mock).mockReturnValueOnce(mockRows);

        const result = await downloadQueueStorage.getPendingSpreads('story-123');

        expect(result).toHaveLength(1);
        expect(result[0].status).toBe('queued');
      });
    });
  });

  describe('cleanup', () => {
    describe('clearCompletedDownloads', () => {
      it('should remove all completed entries from queue', async () => {
        await downloadQueueStorage.clearCompletedDownloads();

        expect(mockDb.runSync).toHaveBeenCalledWith(
          expect.stringContaining("DELETE FROM download_queue WHERE status = 'completed'")
        );
      });
    });

    describe('clearAllDownloads', () => {
      it('should remove all entries from both tables', async () => {
        await downloadQueueStorage.clearAllDownloads();

        expect(mockDb.runSync).toHaveBeenCalledWith(
          expect.stringContaining('DELETE FROM spread_downloads')
        );
        expect(mockDb.runSync).toHaveBeenCalledWith(
          expect.stringContaining('DELETE FROM download_queue')
        );
      });
    });
  });
});
