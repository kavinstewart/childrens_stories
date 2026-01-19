/**
 * Tests for native-downloader.ts
 * TDD: Write tests first, then implement
 *
 * This module wraps react-native-background-downloader to provide
 * a simple interface for downloading files without blocking the JS thread.
 */

// Mock the native module
jest.mock('@kesha-antonov/react-native-background-downloader', () => ({
  createDownloadTask: jest.fn(),
  getExistingDownloadTasks: jest.fn(),
  completeHandler: jest.fn(),
  directories: {
    documents: '/mock/documents',
  },
}));

import {
  createDownloadTask,
  getExistingDownloadTasks,
  completeHandler,
  directories,
} from '@kesha-antonov/react-native-background-downloader';
import { NativeDownloader } from '../../lib/native-downloader';

const mockCreateDownloadTask = createDownloadTask as jest.Mock;
const mockGetExistingDownloadTasks = getExistingDownloadTasks as jest.Mock;
const mockCompleteHandler = completeHandler as jest.Mock;

describe('NativeDownloader', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    NativeDownloader.reset();
  });

  describe('downloadFile', () => {
    it('should create a download task with correct parameters', async () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
        headers: { Authorization: 'Bearer token' },
        onProgress,
        onComplete,
        onError,
      });

      expect(mockCreateDownloadTask).toHaveBeenCalledWith({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
        headers: { Authorization: 'Bearer token' },
      });
      expect(mockTask.start).toHaveBeenCalled();
    });

    it('should call onProgress with percentage', async () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      const onProgress = jest.fn();

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
        onProgress,
      });

      // Simulate progress callback
      const progressCallback = mockTask.progress.mock.calls[0][0];
      progressCallback({ bytesDownloaded: 50, bytesTotal: 100 });

      expect(onProgress).toHaveBeenCalledWith({
        id: 'test-123',
        bytesDownloaded: 50,
        bytesTotal: 100,
        percent: 50,
      });
    });

    it('should call onComplete when download finishes', async () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      const onComplete = jest.fn();

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
        onComplete,
      });

      // Simulate done callback
      const doneCallback = mockTask.done.mock.calls[0][0];
      doneCallback({ bytesDownloaded: 100, bytesTotal: 100 });

      expect(onComplete).toHaveBeenCalledWith({
        id: 'test-123',
        bytesDownloaded: 100,
        bytesTotal: 100,
      });
      expect(mockCompleteHandler).toHaveBeenCalledWith('test-123');
    });

    it('should call onError when download fails', async () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      const onError = jest.fn();

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
        onError,
      });

      // Simulate error callback
      const errorCallback = mockTask.error.mock.calls[0][0];
      errorCallback({ error: 'Network error', errorCode: 500 });

      expect(onError).toHaveBeenCalledWith({
        id: 'test-123',
        error: 'Network error',
        errorCode: 500,
      });
    });

    it('should track active downloads', () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
      });

      expect(NativeDownloader.isDownloading('test-123')).toBe(true);
      expect(NativeDownloader.getActiveDownloadIds()).toContain('test-123');
    });

    it('should remove from active downloads when complete', () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
      });

      // Simulate done callback
      const doneCallback = mockTask.done.mock.calls[0][0];
      doneCallback({ bytesDownloaded: 100, bytesTotal: 100 });

      expect(NativeDownloader.isDownloading('test-123')).toBe(false);
    });
  });

  describe('cancelDownload', () => {
    it('should stop the download task', () => {
      const mockTask = createMockTask();
      mockCreateDownloadTask.mockReturnValue(mockTask);

      NativeDownloader.downloadFile({
        id: 'test-123',
        url: 'https://example.com/image.png',
        destination: '/path/to/file.png',
      });

      NativeDownloader.cancelDownload('test-123');

      expect(mockTask.stop).toHaveBeenCalled();
      expect(NativeDownloader.isDownloading('test-123')).toBe(false);
    });

    it('should not throw if download id does not exist', () => {
      expect(() => NativeDownloader.cancelDownload('nonexistent')).not.toThrow();
    });
  });

  describe('reattachExistingDownloads', () => {
    it('should reattach callbacks to existing downloads', async () => {
      const mockTask1 = createMockTask('task-1');
      const mockTask2 = createMockTask('task-2');
      mockGetExistingDownloadTasks.mockResolvedValue([mockTask1, mockTask2]);

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await NativeDownloader.reattachExistingDownloads({
        onProgress,
        onComplete,
        onError,
      });

      expect(mockGetExistingDownloadTasks).toHaveBeenCalled();
      expect(mockTask1.progress).toHaveBeenCalled();
      expect(mockTask1.done).toHaveBeenCalled();
      expect(mockTask1.error).toHaveBeenCalled();
      expect(mockTask2.progress).toHaveBeenCalled();
    });

    it('should return list of reattached task ids', async () => {
      const mockTask1 = createMockTask('task-1');
      const mockTask2 = createMockTask('task-2');
      mockGetExistingDownloadTasks.mockResolvedValue([mockTask1, mockTask2]);

      const ids = await NativeDownloader.reattachExistingDownloads({});

      expect(ids).toEqual(['task-1', 'task-2']);
    });
  });

  describe('getDocumentsDirectory', () => {
    it('should return the documents directory path', () => {
      expect(NativeDownloader.getDocumentsDirectory()).toBe('/mock/documents');
    });
  });
});

// Helper to create mock task with chainable methods
function createMockTask(id = 'mock-id') {
  const task = {
    id,
    begin: jest.fn().mockReturnThis(),
    progress: jest.fn().mockReturnThis(),
    done: jest.fn().mockReturnThis(),
    error: jest.fn().mockReturnThis(),
    start: jest.fn(),
    stop: jest.fn(),
    pause: jest.fn(),
    resume: jest.fn(),
  };
  return task;
}
