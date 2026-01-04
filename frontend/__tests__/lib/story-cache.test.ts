/**
 * Unit tests for StoryCacheManager
 * Mocks cache-storage, cache-files, and api dependencies
 */

import { StoryCacheManager } from '@/lib/story-cache';
import { cacheStorage } from '@/lib/cache-storage';
import { cacheFiles } from '@/lib/cache-files';
import { api, Story } from '@/lib/api';

// Mock dependencies
jest.mock('@/lib/cache-storage', () => ({
  cacheStorage: {
    getIndex: jest.fn(),
    setStoryEntry: jest.fn(),
    updateLastRead: jest.fn(),
    removeStoryEntry: jest.fn(),
  },
}));

jest.mock('@/lib/cache-files', () => ({
  cacheFiles: {
    ensureDirectoryExists: jest.fn(),
    downloadSpreadImage: jest.fn(),
    saveStoryMetadata: jest.fn(),
    loadStoryMetadata: jest.fn(),
    deleteStoryDirectory: jest.fn(),
    verifyStoryFiles: jest.fn(),
  },
}));

jest.mock('@/lib/api', () => ({
  api: {
    getSpreadImageUrl: jest.fn((storyId, spreadNumber) =>
      `https://example.com/stories/${storyId}/spreads/${spreadNumber}/image`
    ),
  },
}));

const mockCacheStorage = cacheStorage as jest.Mocked<typeof cacheStorage>;
const mockCacheFiles = cacheFiles as jest.Mocked<typeof cacheFiles>;
const mockApi = api as jest.Mocked<typeof api>;

const createMockStory = (overrides: Partial<Story> = {}): Story => ({
  id: 'test-story-123',
  status: 'completed',
  goal: 'A test story',
  target_age_range: '4-6',
  generation_type: 'illustrated',
  is_illustrated: true,
  title: 'Test Story Title',
  spreads: [
    { spread_number: 1, text: 'Page 1', word_count: 10, was_revised: false },
    { spread_number: 2, text: 'Page 2', word_count: 12, was_revised: false },
    { spread_number: 3, text: 'Page 3', word_count: 8, was_revised: false },
  ],
  ...overrides,
});

describe('StoryCacheManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('cacheStory', () => {
    it('returns false for non-illustrated stories', async () => {
      const story = createMockStory({ is_illustrated: false });
      const result = await StoryCacheManager.cacheStory(story);
      expect(result).toBe(false);
      expect(mockCacheFiles.ensureDirectoryExists).not.toHaveBeenCalled();
    });

    it('returns false for stories without spreads', async () => {
      const story = createMockStory({ spreads: [] });
      const result = await StoryCacheManager.cacheStory(story);
      expect(result).toBe(false);
    });

    it('returns false for stories with undefined spreads', async () => {
      const story = createMockStory({ spreads: undefined });
      const result = await StoryCacheManager.cacheStory(story);
      expect(result).toBe(false);
    });

    it('creates directory and downloads all spreads', async () => {
      const story = createMockStory();
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 50000 });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      const result = await StoryCacheManager.cacheStory(story);

      expect(result).toBe(true);
      expect(mockCacheFiles.ensureDirectoryExists).toHaveBeenCalledWith('test-story-123');
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledTimes(3);
      expect(mockCacheFiles.saveStoryMetadata).toHaveBeenCalledWith('test-story-123', story);
      expect(mockCacheStorage.setStoryEntry).toHaveBeenCalledWith(
        'test-story-123',
        expect.objectContaining({
          spreadCount: 3,
          title: 'Test Story Title',
        })
      );
    });

    it('cleans up on download failure', async () => {
      const story = createMockStory();
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage
        .mockResolvedValueOnce({ success: true, size: 50000 })
        .mockResolvedValueOnce({ success: false, size: 0 });
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);

      const result = await StoryCacheManager.cacheStory(story);

      expect(result).toBe(false);
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('test-story-123');
      expect(mockCacheStorage.setStoryEntry).not.toHaveBeenCalled();
    });

    it('respects download concurrency limit', async () => {
      // Create a story with 6 spreads to test batching (DOWNLOAD_CONCURRENCY = 4)
      const story = createMockStory({
        spreads: [
          { spread_number: 1, text: 'P1', word_count: 10, was_revised: false },
          { spread_number: 2, text: 'P2', word_count: 10, was_revised: false },
          { spread_number: 3, text: 'P3', word_count: 10, was_revised: false },
          { spread_number: 4, text: 'P4', word_count: 10, was_revised: false },
          { spread_number: 5, text: 'P5', word_count: 10, was_revised: false },
          { spread_number: 6, text: 'P6', word_count: 10, was_revised: false },
        ],
      });

      let concurrentCalls = 0;
      let maxConcurrent = 0;

      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockImplementation(async () => {
        concurrentCalls++;
        maxConcurrent = Math.max(maxConcurrent, concurrentCalls);
        await new Promise(r => setTimeout(r, 10));
        concurrentCalls--;
        return { success: true, size: 50000 };
      });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.cacheStory(story);

      // Should batch in groups of 4, so max concurrent should be 4
      expect(maxConcurrent).toBeLessThanOrEqual(4);
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledTimes(6);
    });

    it('calculates total size correctly', async () => {
      const story = createMockStory();
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 100000 });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.cacheStory(story);

      const setEntryCall = mockCacheStorage.setStoryEntry.mock.calls[0];
      const entry = setEntryCall[1];
      // 3 spreads * 100000 bytes + metadata size
      expect(entry.sizeBytes).toBeGreaterThan(300000);
    });

    it('uses Untitled for stories without title', async () => {
      const story = createMockStory({ title: undefined });
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 50000 });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.cacheStory(story);

      expect(mockCacheStorage.setStoryEntry).toHaveBeenCalledWith(
        'test-story-123',
        expect.objectContaining({ title: 'Untitled' })
      );
    });
  });

  describe('isStoryCached', () => {
    it('returns false when story not in index', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      const result = await StoryCacheManager.isStoryCached('nonexistent');

      expect(result).toBe(false);
      expect(mockCacheFiles.verifyStoryFiles).not.toHaveBeenCalled();
    });

    it('returns false when files are missing', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'test-123': {
          cachedAt: Date.now(),
          lastRead: Date.now(),
          sizeBytes: 500000,
          spreadCount: 12,
          title: 'Test',
        },
      });
      mockCacheFiles.verifyStoryFiles.mockResolvedValue(false);

      const result = await StoryCacheManager.isStoryCached('test-123');

      expect(result).toBe(false);
      expect(mockCacheFiles.verifyStoryFiles).toHaveBeenCalledWith('test-123', 12);
    });

    it('returns true when index entry exists and files verified', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'test-123': {
          cachedAt: Date.now(),
          lastRead: Date.now(),
          sizeBytes: 500000,
          spreadCount: 12,
          title: 'Test',
        },
      });
      mockCacheFiles.verifyStoryFiles.mockResolvedValue(true);

      const result = await StoryCacheManager.isStoryCached('test-123');

      expect(result).toBe(true);
    });
  });

  describe('loadCachedStory', () => {
    it('returns null when story not cached', async () => {
      mockCacheFiles.loadStoryMetadata.mockResolvedValue(null);

      const result = await StoryCacheManager.loadCachedStory('nonexistent');

      expect(result).toBeNull();
      expect(mockCacheStorage.updateLastRead).not.toHaveBeenCalled();
    });

    it('returns story and updates lastRead timestamp', async () => {
      const cachedStory = createMockStory();
      mockCacheFiles.loadStoryMetadata.mockResolvedValue(cachedStory);
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const result = await StoryCacheManager.loadCachedStory('test-story-123');

      expect(result).toEqual(cachedStory);
      expect(mockCacheStorage.updateLastRead).toHaveBeenCalledWith('test-story-123');
    });
  });

  describe('evictStory', () => {
    it('deletes directory and removes from index', async () => {
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.evictStory('test-123');

      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('test-123');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('test-123');
    });
  });

  describe('invalidateStory', () => {
    it('calls evictStory (same behavior)', async () => {
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.invalidateStory('test-123');

      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('test-123');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('test-123');
    });
  });
});
