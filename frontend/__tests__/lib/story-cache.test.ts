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

const createMockStory = (overrides: Partial<Story> = {}): Story => ({
  id: 'test-story-123',
  status: 'completed',
  goal: 'A test story',
  target_age_range: '4-6',
  generation_type: 'illustrated',
  is_illustrated: true,
  title: 'Test Story Title',
  spreads: [
    { spread_number: 1, text: 'Page 1', word_count: 10, was_revised: false, illustration_url: '/stories/test-story-123/spreads/1/image' },
    { spread_number: 2, text: 'Page 2', word_count: 12, was_revised: false, illustration_url: '/stories/test-story-123/spreads/2/image' },
    { spread_number: 3, text: 'Page 3', word_count: 8, was_revised: false, illustration_url: '/stories/test-story-123/spreads/3/image' },
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
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache, plenty of space
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
          goal: 'A test story',
          isIllustrated: true,
          coverSpreadNumber: 1,
        })
      );
    });

    it('cleans up on download failure', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
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
          { spread_number: 1, text: 'P1', word_count: 10, was_revised: false, illustration_url: '/s/1' },
          { spread_number: 2, text: 'P2', word_count: 10, was_revised: false, illustration_url: '/s/2' },
          { spread_number: 3, text: 'P3', word_count: 10, was_revised: false, illustration_url: '/s/3' },
          { spread_number: 4, text: 'P4', word_count: 10, was_revised: false, illustration_url: '/s/4' },
          { spread_number: 5, text: 'P5', word_count: 10, was_revised: false, illustration_url: '/s/5' },
          { spread_number: 6, text: 'P6', word_count: 10, was_revised: false, illustration_url: '/s/6' },
        ],
      });

      let concurrentCalls = 0;
      let maxConcurrent = 0;

      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
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
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
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
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
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

    it('skips downloading images for spreads without illustration_url', async () => {
      // Story with 3 spreads: 2 have illustrations, 1 does not (spread 3)
      const story = createMockStory({
        spreads: [
          { spread_number: 1, text: 'Page 1', word_count: 10, was_revised: false, illustration_url: '/stories/test/spreads/1/image' },
          { spread_number: 2, text: 'Page 2', word_count: 12, was_revised: false, illustration_url: '/stories/test/spreads/2/image' },
          { spread_number: 3, text: 'Page 3', word_count: 8, was_revised: false }, // No illustration_url
        ],
      });
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 50000 });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.cacheStory(story);

      // Should only download 2 images (spreads 1 and 2), not 3
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledTimes(2);
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledWith(
        'test-story-123',
        1,
        expect.any(String)
      );
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledWith(
        'test-story-123',
        2,
        expect.any(String)
      );
      // Spread 3 should NOT have been downloaded
      expect(mockCacheFiles.downloadSpreadImage).not.toHaveBeenCalledWith(
        'test-story-123',
        3,
        expect.any(String)
      );
    });

    it('deduplicates concurrent cacheStory calls for the same story', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({}); // Empty cache
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      // Simulate slow downloads
      mockCacheFiles.downloadSpreadImage.mockImplementation(async () => {
        await new Promise(r => setTimeout(r, 50));
        return { success: true, size: 50000 };
      });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      // Start 3 concurrent cache attempts for the same story
      const promise1 = StoryCacheManager.cacheStory(story);
      const promise2 = StoryCacheManager.cacheStory(story);
      const promise3 = StoryCacheManager.cacheStory(story);

      const [result1, result2, result3] = await Promise.all([promise1, promise2, promise3]);

      // All should succeed
      expect(result1).toBe(true);
      expect(result2).toBe(true);
      expect(result3).toBe(true);

      // But ensureDirectoryExists should only be called ONCE (deduplication)
      expect(mockCacheFiles.ensureDirectoryExists).toHaveBeenCalledTimes(1);
      // Downloads should only happen once (3 spreads)
      expect(mockCacheFiles.downloadSpreadImage).toHaveBeenCalledTimes(3);
    });

    it('allows caching same story again after first attempt completes', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({});
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 50000 });
      mockCacheFiles.saveStoryMetadata.mockResolvedValue(undefined);
      mockCacheStorage.setStoryEntry.mockResolvedValue(undefined);

      // First cache attempt
      const result1 = await StoryCacheManager.cacheStory(story);
      expect(result1).toBe(true);

      // Second cache attempt (sequential, not concurrent)
      const result2 = await StoryCacheManager.cacheStory(story);
      expect(result2).toBe(true);

      // Both should have executed (sequential calls are not deduplicated)
      expect(mockCacheFiles.ensureDirectoryExists).toHaveBeenCalledTimes(2);
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
      expect(mockCacheFiles.verifyStoryFiles).toHaveBeenCalledWith('test-123');
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

    it('returns story with isCached flag and updates lastRead timestamp', async () => {
      const cachedStory = createMockStory();
      mockCacheFiles.loadStoryMetadata.mockResolvedValue(cachedStory);
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const result = await StoryCacheManager.loadCachedStory('test-story-123');

      expect(result).toEqual({ ...cachedStory, isCached: true });
      expect(result?.isCached).toBe(true);
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

  describe('getCacheSize', () => {
    it('returns 0 for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      const size = await StoryCacheManager.getCacheSize();

      expect(size).toBe(0);
    });

    it('returns sum of all story sizes', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
        'story-3': { cachedAt: 3000, lastRead: 3000, sizeBytes: 200000, spreadCount: 8, title: 'C' },
      });

      const size = await StoryCacheManager.getCacheSize();

      expect(size).toBe(1000000); // 500000 + 300000 + 200000
    });
  });

  describe('getCachedStoryIds', () => {
    it('returns empty array for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      const ids = await StoryCacheManager.getCachedStoryIds();

      expect(ids).toEqual([]);
    });

    it('returns all cached story IDs', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
      });

      const ids = await StoryCacheManager.getCachedStoryIds();

      expect(ids).toHaveLength(2);
      expect(ids).toContain('story-1');
      expect(ids).toContain('story-2');
    });
  });

  describe('loadAllCachedStories', () => {
    it('returns empty array for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      const stories = await StoryCacheManager.loadAllCachedStories();

      expect(stories).toEqual([]);
    });

    it('loads and returns all cached stories', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
      });
      mockCacheFiles.loadStoryMetadata
        .mockResolvedValueOnce(createMockStory({ id: 'story-1', title: 'Story A', created_at: '2024-01-01T00:00:00Z' }))
        .mockResolvedValueOnce(createMockStory({ id: 'story-2', title: 'Story B', created_at: '2024-01-02T00:00:00Z' }));
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const stories = await StoryCacheManager.loadAllCachedStories();

      expect(stories).toHaveLength(2);
      expect(mockCacheFiles.loadStoryMetadata).toHaveBeenCalledTimes(2);
    });

    it('sorts stories by created_at descending (newest first)', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-old': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'Old' },
        'story-new': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'New' },
      });
      mockCacheFiles.loadStoryMetadata
        .mockResolvedValueOnce(createMockStory({ id: 'story-old', title: 'Old Story', created_at: '2024-01-01T00:00:00Z' }))
        .mockResolvedValueOnce(createMockStory({ id: 'story-new', title: 'New Story', created_at: '2024-01-15T00:00:00Z' }));
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const stories = await StoryCacheManager.loadAllCachedStories();

      expect(stories[0].title).toBe('New Story');
      expect(stories[1].title).toBe('Old Story');
    });

    it('filters out stories that fail to load', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
        'story-3': { cachedAt: 3000, lastRead: 3000, sizeBytes: 400000, spreadCount: 11, title: 'C' },
      });
      mockCacheFiles.loadStoryMetadata
        .mockResolvedValueOnce(createMockStory({ id: 'story-1', title: 'Story A' }))
        .mockResolvedValueOnce(null) // story-2 fails to load
        .mockResolvedValueOnce(createMockStory({ id: 'story-3', title: 'Story C' }));
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const stories = await StoryCacheManager.loadAllCachedStories();

      expect(stories).toHaveLength(2);
      expect(stories.map(s => s.id)).toContain('story-1');
      expect(stories.map(s => s.id)).toContain('story-3');
      expect(stories.map(s => s.id)).not.toContain('story-2');
    });

    it('loads stories in parallel for better performance', async () => {
      // Create 5 stories to load
      const index: Record<string, { cachedAt: number; lastRead: number; sizeBytes: number; spreadCount: number; title: string }> = {};
      for (let i = 0; i < 5; i++) {
        index[`story-${i}`] = { cachedAt: i * 1000, lastRead: i * 1000, sizeBytes: 500000, spreadCount: 12, title: `Story ${i}` };
      }
      mockCacheStorage.getIndex.mockResolvedValue(index);

      // Track concurrent load count
      let concurrentLoads = 0;
      let maxConcurrent = 0;

      mockCacheFiles.loadStoryMetadata.mockImplementation(async (storyId: string) => {
        concurrentLoads++;
        maxConcurrent = Math.max(maxConcurrent, concurrentLoads);
        await new Promise(r => setTimeout(r, 20)); // Simulate I/O delay
        concurrentLoads--;
        return createMockStory({ id: storyId, title: `Story ${storyId}` });
      });
      mockCacheStorage.updateLastRead.mockResolvedValue(undefined);

      const startTime = Date.now();
      const stories = await StoryCacheManager.loadAllCachedStories();
      const elapsed = Date.now() - startTime;

      expect(stories).toHaveLength(5);
      // If parallel: all 5 load concurrently, maxConcurrent should be 5, elapsed ~20ms
      // If sequential: maxConcurrent would be 1, elapsed ~100ms (5 * 20ms)
      expect(maxConcurrent).toBe(5); // All loads should happen concurrently
      expect(elapsed).toBeLessThan(80); // Should complete much faster than sequential (100ms+)
    });
  });

  describe('getCachedStorySummaries', () => {
    it('returns empty array for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      const summaries = await StoryCacheManager.getCachedStorySummaries();

      expect(summaries).toEqual([]);
    });

    it('returns summaries from index without loading metadata files', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': {
          cachedAt: 2000,
          lastRead: 2000,
          sizeBytes: 500000,
          spreadCount: 12,
          title: 'Story One',
          goal: 'A brave adventure',
          isIllustrated: true,
          coverSpreadNumber: 1,
        },
        'story-2': {
          cachedAt: 1000,
          lastRead: 1000,
          sizeBytes: 300000,
          spreadCount: 10,
          title: 'Story Two',
          goal: 'A kind tale',
          isIllustrated: false,
          coverSpreadNumber: 1,
        },
      });

      const summaries = await StoryCacheManager.getCachedStorySummaries();

      // Should NOT load metadata files - this is the key optimization
      expect(mockCacheFiles.loadStoryMetadata).not.toHaveBeenCalled();

      expect(summaries).toHaveLength(2);
      // Verify summary structure
      expect(summaries[0]).toMatchObject({
        id: expect.any(String),
        title: expect.any(String),
        goal: expect.any(String),
        is_illustrated: expect.any(Boolean),
        isCached: true,
        coverSpreadNumber: 1,
      });
    });

    it('sorts summaries by cachedAt descending (newest first)', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-old': {
          cachedAt: 1000,
          lastRead: 1000,
          sizeBytes: 500000,
          spreadCount: 12,
          title: 'Old Story',
          goal: 'Old goal',
          isIllustrated: true,
          coverSpreadNumber: 1,
        },
        'story-new': {
          cachedAt: 3000,
          lastRead: 3000,
          sizeBytes: 300000,
          spreadCount: 10,
          title: 'New Story',
          goal: 'New goal',
          isIllustrated: true,
          coverSpreadNumber: 1,
        },
      });

      const summaries = await StoryCacheManager.getCachedStorySummaries();

      expect(summaries[0].title).toBe('New Story');
      expect(summaries[1].title).toBe('Old Story');
    });

    it('includes all fields needed for StoryCard rendering', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': {
          cachedAt: 1000,
          lastRead: 1000,
          sizeBytes: 500000,
          spreadCount: 12,
          title: 'Test Story',
          goal: 'A space adventure',
          isIllustrated: true,
          coverSpreadNumber: 2,
        },
      });

      const summaries = await StoryCacheManager.getCachedStorySummaries();

      expect(summaries[0]).toEqual({
        id: 'story-1',
        title: 'Test Story',
        goal: 'A space adventure',
        is_illustrated: true,
        isCached: true,
        coverSpreadNumber: 2,
      });
    });
  });

  describe('ensureCacheSpace', () => {
    it('does nothing when there is enough space', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 100000000, spreadCount: 12, title: 'A' },
      });

      await StoryCacheManager.ensureCacheSpace(50000000); // Need 50MB, have 400MB free

      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalled();
    });

    it('evicts oldest-read stories when over budget', async () => {
      // Setup: 450MB used, need 100MB, so need to free 50MB
      // Story-A (oldest) should be evicted
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-a': { cachedAt: 1000, lastRead: 1000, sizeBytes: 100000000, spreadCount: 12, title: 'A' }, // oldest
        'story-b': { cachedAt: 2000, lastRead: 3000, sizeBytes: 150000000, spreadCount: 12, title: 'B' },
        'story-c': { cachedAt: 3000, lastRead: 2000, sizeBytes: 200000000, spreadCount: 12, title: 'C' },
      }); // Total: 450MB
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.ensureCacheSpace(100000000); // Need 100MB

      // story-a has oldest lastRead (1000), should be evicted
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-a');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-a');
    });

    it('evicts multiple stories if needed', async () => {
      // Setup: 480MB used, need 100MB, so need to free 80MB
      // Both story-a (50MB) and story-c (60MB) should be evicted (sorted by lastRead)
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-a': { cachedAt: 1000, lastRead: 1000, sizeBytes: 50000000, spreadCount: 12, title: 'A' }, // oldest
        'story-b': { cachedAt: 2000, lastRead: 3000, sizeBytes: 200000000, spreadCount: 12, title: 'B' }, // newest
        'story-c': { cachedAt: 3000, lastRead: 2000, sizeBytes: 60000000, spreadCount: 12, title: 'C' }, // middle
        'story-d': { cachedAt: 4000, lastRead: 4000, sizeBytes: 170000000, spreadCount: 12, title: 'D' },
      }); // Total: 480MB
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.ensureCacheSpace(100000000); // Need 100MB

      // story-a (lastRead 1000) evicted first, then story-c (lastRead 2000)
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-a');
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-c');
      // story-b and story-d should not be evicted
      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalledWith('story-b');
      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalledWith('story-d');
    });
  });

  describe('clearAllCache', () => {
    it('does nothing for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      await StoryCacheManager.clearAllCache();

      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalled();
    });

    it('evicts all cached stories', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
      });
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.clearAllCache();

      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-1');
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-2');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-1');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-2');
    });
  });

  describe('atomicity and crash recovery', () => {
    it('removes index entry before file deletion (index-first ordering)', async () => {
      // This tests the fail-safe ordering: index is removed first, so isStoryCached returns false
      // even if we crash between index removal and file deletion
      const callOrder: string[] = [];
      mockCacheStorage.removeStoryEntry.mockImplementation(async () => {
        callOrder.push('removeStoryEntry');
      });
      mockCacheFiles.deleteStoryDirectory.mockImplementation(async () => {
        callOrder.push('deleteStoryDirectory');
      });

      await StoryCacheManager.evictStory('test-123');

      // Index should be removed BEFORE file deletion
      expect(callOrder).toEqual(['removeStoryEntry', 'deleteStoryDirectory']);
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('test-123');
    });

    it('cleans up index on directory creation failure', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({});
      mockCacheFiles.ensureDirectoryExists.mockRejectedValue(new Error('Cannot create directory'));
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);

      const result = await StoryCacheManager.cacheStory(story);

      expect(result).toBe(false);
      // Cleanup should have been attempted
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('test-story-123');
    });

    it('cleans up index on metadata save failure', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({});
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: true, size: 50000 });
      mockCacheFiles.saveStoryMetadata.mockRejectedValue(new Error('Cannot save metadata'));
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);

      const result = await StoryCacheManager.cacheStory(story);

      expect(result).toBe(false);
      // Cleanup should have removed index entry and attempted file deletion
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('test-story-123');
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('test-story-123');
    });

    it('handles cleanup failure gracefully (no throw)', async () => {
      const story = createMockStory();
      mockCacheStorage.getIndex.mockResolvedValue({});
      mockCacheFiles.ensureDirectoryExists.mockResolvedValue(undefined);
      mockCacheFiles.downloadSpreadImage.mockResolvedValue({ success: false, size: 0 });
      // Both cleanup operations fail
      mockCacheStorage.removeStoryEntry.mockRejectedValue(new Error('Index error'));
      mockCacheFiles.deleteStoryDirectory.mockRejectedValue(new Error('File error'));

      // Should not throw despite cleanup failures
      const result = await StoryCacheManager.cacheStory(story);

      expect(result).toBe(false);
    });
  });

  describe('verifyCacheIntegrity', () => {
    it('does nothing for empty cache', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({});

      await StoryCacheManager.verifyCacheIntegrity();

      expect(mockCacheFiles.verifyStoryFiles).not.toHaveBeenCalled();
      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalled();
    });

    it('keeps valid cache entries', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
      });
      mockCacheFiles.verifyStoryFiles.mockResolvedValue(true);

      await StoryCacheManager.verifyCacheIntegrity();

      expect(mockCacheFiles.verifyStoryFiles).toHaveBeenCalledWith('story-1');
      expect(mockCacheFiles.verifyStoryFiles).toHaveBeenCalledWith('story-2');
      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalled();
      expect(mockCacheStorage.removeStoryEntry).not.toHaveBeenCalled();
    });

    it('removes orphaned cache entries with missing files', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
        'story-2': { cachedAt: 2000, lastRead: 2000, sizeBytes: 300000, spreadCount: 10, title: 'B' },
        'story-3': { cachedAt: 3000, lastRead: 3000, sizeBytes: 200000, spreadCount: 8, title: 'C' },
      });
      mockCacheFiles.verifyStoryFiles
        .mockResolvedValueOnce(true)   // story-1 valid
        .mockResolvedValueOnce(false)  // story-2 orphaned
        .mockResolvedValueOnce(false); // story-3 orphaned
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.verifyCacheIntegrity();

      // story-1 should not be deleted
      expect(mockCacheFiles.deleteStoryDirectory).not.toHaveBeenCalledWith('story-1');
      expect(mockCacheStorage.removeStoryEntry).not.toHaveBeenCalledWith('story-1');

      // story-2 and story-3 should be deleted
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-2');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-2');
      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-3');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-3');
    });

    it('removes all entries when all are orphaned', async () => {
      mockCacheStorage.getIndex.mockResolvedValue({
        'story-1': { cachedAt: 1000, lastRead: 1000, sizeBytes: 500000, spreadCount: 12, title: 'A' },
      });
      mockCacheFiles.verifyStoryFiles.mockResolvedValue(false);
      mockCacheFiles.deleteStoryDirectory.mockResolvedValue(undefined);
      mockCacheStorage.removeStoryEntry.mockResolvedValue(undefined);

      await StoryCacheManager.verifyCacheIntegrity();

      expect(mockCacheFiles.deleteStoryDirectory).toHaveBeenCalledWith('story-1');
      expect(mockCacheStorage.removeStoryEntry).toHaveBeenCalledWith('story-1');
    });
  });

});
