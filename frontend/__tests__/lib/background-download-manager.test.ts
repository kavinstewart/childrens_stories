/**
 * Tests for background-download-manager.ts
 * TDD: Write tests first, then implement
 *
 * This module orchestrates background downloads:
 * - Queues stories/spreads to SQLite
 * - Uses NativeDownloader for actual downloads
 * - Updates progress and handles completion
 */

// Mock dependencies
jest.mock('../../lib/native-downloader', () => ({
  NativeDownloader: {
    downloadFile: jest.fn(),
    cancelDownload: jest.fn(),
    isDownloading: jest.fn(() => false),
    getActiveDownloadIds: jest.fn(() => []),
    reattachExistingDownloads: jest.fn(() => Promise.resolve([])),
    getDocumentsDirectory: jest.fn(() => '/mock/documents'),
    reset: jest.fn(),
  },
}));

jest.mock('../../lib/download-queue-storage', () => ({
  downloadQueueStorage: {
    queueStory: jest.fn(),
    updateStoryStatus: jest.fn(),
    incrementCompletedSpreads: jest.fn(),
    getQueuedStories: jest.fn(() => []),
    getIncompleteStories: jest.fn(() => []),
    getStoryDownloadStatus: jest.fn(),
    removeFromQueue: jest.fn(),
    getCompletedStoryIds: jest.fn(() => []),
    queueSpread: jest.fn(),
    updateSpreadStatus: jest.fn(),
    getSpreadDownloads: jest.fn(() => []),
    getPendingSpreads: jest.fn(() => []),
    clearCompletedDownloads: jest.fn(),
    clearAllDownloads: jest.fn(),
  },
  _resetDbForTesting: jest.fn(),
}));

jest.mock('../../lib/cache-files', () => ({
  cacheFiles: {
    getStoryDir: jest.fn((storyId: string) => `/mock/documents/stories/${storyId}`),
    getSpreadPath: jest.fn((storyId: string, num: number) => `/mock/documents/stories/${storyId}/spread_${num}.png`),
    ensureDirectoryExists: jest.fn(),
    saveStoryMetadata: jest.fn(),
    loadStoryMetadata: jest.fn(),
    deleteStoryDirectory: jest.fn(),
    verifyStoryFiles: jest.fn(() => true),
  },
}));

jest.mock('../../lib/auth-storage', () => ({
  authStorage: {
    getToken: jest.fn(() => Promise.resolve('mock-token')),
  },
}));

import { NativeDownloader } from '../../lib/native-downloader';
import { downloadQueueStorage } from '../../lib/download-queue-storage';
import { cacheFiles } from '../../lib/cache-files';
import {
  BackgroundDownloadManager,
  DownloadCallbacks,
} from '../../lib/background-download-manager';

const mockNativeDownloader = NativeDownloader as jest.Mocked<typeof NativeDownloader>;
const mockQueueStorage = downloadQueueStorage as jest.Mocked<typeof downloadQueueStorage>;
const mockCacheFiles = cacheFiles as jest.Mocked<typeof cacheFiles>;

describe('BackgroundDownloadManager', () => {
  let callbacks: DownloadCallbacks;

  beforeEach(() => {
    jest.clearAllMocks();
    BackgroundDownloadManager.reset();

    callbacks = {
      onStoryComplete: jest.fn(),
      onStoryFailed: jest.fn(),
      onStoryProgress: jest.fn(),
    };
  });

  describe('queueStoryDownload', () => {
    const mockStory = {
      id: 'story-123',
      title: 'Test Story',
      goal: 'adventure',
      spreads: [
        { spread_number: 1, illustration_url: 'https://example.com/1.png' },
        { spread_number: 2, illustration_url: 'https://example.com/2.png' },
        { spread_number: 3, illustration_url: 'https://example.com/3.png' },
      ],
    };

    it('should add story to download queue', async () => {
      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      expect(mockQueueStorage.queueStory).toHaveBeenCalledWith(
        expect.objectContaining({
          storyId: 'story-123',
          status: 'queued',
          totalSpreads: 3,
          completedSpreads: 0,
        })
      );
    });

    it('should queue each spread for download', async () => {
      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      expect(mockQueueStorage.queueSpread).toHaveBeenCalledTimes(3);
      expect(mockQueueStorage.queueSpread).toHaveBeenCalledWith(
        expect.objectContaining({
          storyId: 'story-123',
          spreadNumber: 1,
          status: 'queued',
        })
      );
    });

    it('should ensure story directory exists', async () => {
      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      expect(mockCacheFiles.ensureDirectoryExists).toHaveBeenCalledWith('story-123');
    });

    it('should start downloading spreads', async () => {
      // Mock getPendingSpreads to return spreads that need downloading
      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 1, status: 'queued', url: 'https://example.com/1.png', destination: '/path/1.png' },
        { storyId: 'story-123', spreadNumber: 2, status: 'queued', url: 'https://example.com/2.png', destination: '/path/2.png' },
      ]);

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      expect(mockNativeDownloader.downloadFile).toHaveBeenCalled();
    });

    it('should not queue story that is already downloading', async () => {
      mockQueueStorage.getStoryDownloadStatus.mockResolvedValueOnce({
        storyId: 'story-123',
        status: 'downloading',
        totalSpreads: 3,
        completedSpreads: 1,
        queuedAt: Date.now(),
      });

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      expect(mockQueueStorage.queueStory).not.toHaveBeenCalled();
    });
  });

  describe('spread download completion', () => {
    it('should increment completed count when spread finishes', async () => {
      let onCompleteCallback: ((result: any) => void) | undefined;

      mockNativeDownloader.downloadFile.mockImplementation((options) => {
        onCompleteCallback = options.onComplete;
      });

      // Mock getPendingSpreads to return the spread initially
      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 1, status: 'queued', url: 'https://example.com/1.png', destination: '/path/1.png' },
      ]);

      const mockStory = {
        id: 'story-123',
        spreads: [{ spread_number: 1, illustration_url: 'https://example.com/1.png' }],
      };

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      // Mock for after completion check
      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([]);

      // Simulate download completion (using pipe delimiter)
      onCompleteCallback?.({ id: 'story-123|1', bytesDownloaded: 50000, bytesTotal: 50000 });

      // Wait for async
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(mockQueueStorage.updateSpreadStatus).toHaveBeenCalledWith(
        'story-123',
        1,
        'completed',
        expect.anything()
      );
      expect(mockQueueStorage.incrementCompletedSpreads).toHaveBeenCalledWith('story-123');
    });

    it('should call onStoryComplete when all spreads finish', async () => {
      let onCompleteCallback: ((result: any) => void) | undefined;

      mockNativeDownloader.downloadFile.mockImplementation((options) => {
        onCompleteCallback = options.onComplete;
      });

      // Mock getPendingSpreads - first for queueing, second for completion check
      mockQueueStorage.getPendingSpreads
        .mockResolvedValueOnce([
          { storyId: 'story-123', spreadNumber: 1, status: 'queued', url: 'https://example.com/1.png', destination: '/path/1.png' },
        ])
        .mockResolvedValueOnce([]); // No pending after completion

      const mockStory = {
        id: 'story-123',
        spreads: [
          { spread_number: 1, illustration_url: 'https://example.com/1.png' },
        ],
      };

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      // Simulate completion (using pipe delimiter)
      onCompleteCallback?.({ id: 'story-123|1', bytesDownloaded: 50000, bytesTotal: 50000 });

      // Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(callbacks.onStoryComplete).toHaveBeenCalledWith('story-123');
    });
  });

  describe('spread download failure', () => {
    it('should mark spread as failed on error', async () => {
      let onErrorCallback: ((error: any) => void) | undefined;

      mockNativeDownloader.downloadFile.mockImplementation((options) => {
        onErrorCallback = options.onError;
      });

      // Mock getPendingSpreads to return the spread
      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 1, status: 'queued', url: 'https://example.com/1.png', destination: '/path/1.png' },
      ]);

      const mockStory = {
        id: 'story-123',
        spreads: [{ spread_number: 1, illustration_url: 'https://example.com/1.png' }],
      };

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);

      // Simulate error (using pipe delimiter)
      onErrorCallback?.({ id: 'story-123|1', error: 'Network error' });

      // Wait for async
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(mockQueueStorage.updateSpreadStatus).toHaveBeenCalledWith(
        'story-123',
        1,
        'failed',
        expect.objectContaining({ error: 'Network error' })
      );
    });

    it('should call onStoryFailed when a spread fails', async () => {
      let onErrorCallback: ((error: any) => void) | undefined;

      mockNativeDownloader.downloadFile.mockImplementation((options) => {
        onErrorCallback = options.onError;
      });

      // Mock getPendingSpreads to return the spread
      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 1, status: 'queued', url: 'https://example.com/1.png', destination: '/path/1.png' },
      ]);

      const mockStory = {
        id: 'story-123',
        spreads: [{ spread_number: 1, illustration_url: 'https://example.com/1.png' }],
      };

      await BackgroundDownloadManager.queueStoryDownload(mockStory as any, callbacks);
      onErrorCallback?.({ id: 'story-123|1', error: 'Network error' });

      await new Promise(resolve => setTimeout(resolve, 10));

      expect(callbacks.onStoryFailed).toHaveBeenCalledWith('story-123', expect.any(String));
    });
  });

  describe('cancelStoryDownload', () => {
    it('should cancel all active downloads for a story', async () => {
      mockQueueStorage.getSpreadDownloads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 1, status: 'downloading', url: '', destination: '' },
        { storyId: 'story-123', spreadNumber: 2, status: 'queued', url: '', destination: '' },
      ]);

      await BackgroundDownloadManager.cancelStoryDownload('story-123');

      expect(mockNativeDownloader.cancelDownload).toHaveBeenCalledWith('story-123|1');
      expect(mockNativeDownloader.cancelDownload).toHaveBeenCalledWith('story-123|2');
    });

    it('should remove story from queue', async () => {
      mockQueueStorage.getSpreadDownloads.mockResolvedValueOnce([]);

      await BackgroundDownloadManager.cancelStoryDownload('story-123');

      expect(mockQueueStorage.removeFromQueue).toHaveBeenCalledWith('story-123');
    });
  });

  describe('resumeIncompleteDownloads', () => {
    it('should resume downloading pending spreads on startup', async () => {
      mockQueueStorage.getIncompleteStories.mockResolvedValueOnce([
        {
          storyId: 'story-123',
          status: 'downloading',
          totalSpreads: 3,
          completedSpreads: 1,
          queuedAt: Date.now(),
        },
      ]);

      mockQueueStorage.getPendingSpreads.mockResolvedValueOnce([
        { storyId: 'story-123', spreadNumber: 2, status: 'queued', url: 'https://example.com/2.png', destination: '/path/2.png' },
        { storyId: 'story-123', spreadNumber: 3, status: 'queued', url: 'https://example.com/3.png', destination: '/path/3.png' },
      ]);

      await BackgroundDownloadManager.resumeIncompleteDownloads(callbacks);

      expect(mockNativeDownloader.downloadFile).toHaveBeenCalledTimes(2);
    });
  });

  describe('getDownloadProgress', () => {
    it('should return progress for a story', async () => {
      mockQueueStorage.getStoryDownloadStatus.mockResolvedValueOnce({
        storyId: 'story-123',
        status: 'downloading',
        totalSpreads: 10,
        completedSpreads: 7,
        queuedAt: Date.now(),
      });

      const progress = await BackgroundDownloadManager.getDownloadProgress('story-123');

      expect(progress).toEqual({
        storyId: 'story-123',
        status: 'downloading',
        totalSpreads: 10,
        completedSpreads: 7,
        percent: 70,
      });
    });

    it('should return null if story not in queue', async () => {
      mockQueueStorage.getStoryDownloadStatus.mockResolvedValueOnce(null);

      const progress = await BackgroundDownloadManager.getDownloadProgress('nonexistent');

      expect(progress).toBeNull();
    });
  });
});
