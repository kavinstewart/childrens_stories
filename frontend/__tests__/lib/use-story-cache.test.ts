/**
 * Unit tests for useStoryCache hook
 * Tests state transitions and cache behavior
 */

import { renderHook, act, waitFor, RenderHookResult } from '@testing-library/react-native';
import { useStoryCache, UseStoryCacheResult } from '@/lib/use-story-cache';
import { StoryCacheManager } from '@/lib/story-cache';
import { cacheFiles } from '@/lib/cache-files';
import { api, Story } from '@/lib/api';
import { cacheEvents } from '@/lib/cache-events';

// Mock dependencies
jest.mock('@/lib/story-cache', () => ({
  StoryCacheManager: {
    isStoryCached: jest.fn(),
    loadCachedStory: jest.fn(),
    cacheStory: jest.fn(),
  },
}));

jest.mock('@/lib/cache-files', () => ({
  cacheFiles: {
    getSpreadPath: jest.fn((storyId, spreadNumber) =>
      `file:///stories/${storyId}/spread_${spreadNumber}.png`
    ),
  },
}));

jest.mock('@/lib/api', () => ({
  api: {
    getSpreadImageUrl: jest.fn((storyId, spreadNumber) =>
      `https://example.com/stories/${storyId}/spreads/${spreadNumber}/image`
    ),
  },
}));

// Use real cache-events implementation (simple event emitter, no need to mock)

const mockStoryCacheManager = StoryCacheManager as jest.Mocked<typeof StoryCacheManager>;
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
    { spread_number: 1, text: 'Page 1', word_count: 10, was_revised: false, illustration_url: '/stories/test-story-123/spreads/1/image' },
    { spread_number: 2, text: 'Page 2', word_count: 12, was_revised: false, illustration_url: '/stories/test-story-123/spreads/2/image' },
  ],
  ...overrides,
});

describe('useStoryCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('initial state', () => {
    it('returns undefined story when no storyId provided', () => {
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);
      mockStoryCacheManager.cacheStory.mockResolvedValue(false);

      const { result } = renderHook(() => useStoryCache(undefined, undefined));

      expect(result.current.story).toBeUndefined();
      expect(result.current.isCached).toBe(false);
      expect(result.current.isCaching).toBe(false);
    });

    it('returns network story initially when not cached', async () => {
      const networkStory = createMockStory();
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);
      mockStoryCacheManager.cacheStory.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue({ ...networkStory, isCached: true });

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      // Initially should return network story
      expect(result.current.story).toEqual(networkStory);
      expect(result.current.isCached).toBe(false);
    });
  });

  describe('cache check', () => {
    it('loads cached story when available', async () => {
      const cachedStory = createMockStory({ isCached: true });
      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('test-story-123', undefined));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      expect(result.current.story).toEqual(cachedStory);
      expect(mockStoryCacheManager.loadCachedStory).toHaveBeenCalledWith('test-story-123');
    });

    it('handles cache check failure gracefully', async () => {
      const networkStory = createMockStory();
      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(null);
      mockStoryCacheManager.cacheStory.mockResolvedValue(true);

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      await waitFor(() => {
        expect(result.current.isCached).toBe(false);
      });

      expect(result.current.story).toEqual(networkStory);
    });
  });

  describe('background caching', () => {
    it('triggers caching for eligible illustrated stories', async () => {
      const networkStory = createMockStory({ status: 'completed', is_illustrated: true });
      const cachedStory = { ...networkStory, isCached: true };

      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);
      mockStoryCacheManager.cacheStory.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(networkStory);
    });

    it('does not trigger caching for non-illustrated stories', async () => {
      const networkStory = createMockStory({ is_illustrated: false });
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);

      renderHook(() => useStoryCache('test-story-123', networkStory));

      // Wait a bit to ensure effect has run
      await new Promise(r => setTimeout(r, 50));

      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });

    it('does not trigger caching for incomplete stories', async () => {
      const networkStory = createMockStory({ status: 'running' });
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);

      renderHook(() => useStoryCache('test-story-123', networkStory));

      await new Promise(r => setTimeout(r, 50));

      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });

    it('does not cache again if already cached', async () => {
      const cachedStory = createMockStory({ isCached: true });
      const networkStory = createMockStory();

      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      // Should not call cacheStory since we're already cached
      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });
  });

  describe('getImageUrl', () => {
    it('returns file:// URL when cached', async () => {
      const cachedStory = createMockStory({ isCached: true });
      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('test-story-123', undefined));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      const url = result.current.getImageUrl('test-story-123', cachedStory.spreads![0]);
      expect(url).toContain('file://');
      expect(mockCacheFiles.getSpreadPath).toHaveBeenCalledWith('test-story-123', 1);
    });

    it('returns server URL when not cached', async () => {
      const networkStory = createMockStory();
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      await waitFor(() => {
        expect(mockStoryCacheManager.isStoryCached).toHaveBeenCalled();
      });

      const url = result.current.getImageUrl('test-story-123', networkStory.spreads![0]);
      expect(url).toContain('https://');
      expect(mockApi.getSpreadImageUrl).toHaveBeenCalled();
    });

    it('returns null for spreads without illustration_url', async () => {
      const networkStory = createMockStory({
        spreads: [{ spread_number: 1, text: 'Text only', word_count: 5, was_revised: false }],
      });
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);

      const { result } = renderHook(() => useStoryCache('test-story-123', networkStory));

      const url = result.current.getImageUrl('test-story-123', networkStory.spreads![0]);
      expect(url).toBeNull();
    });
  });

  describe('story ID changes', () => {
    it('resets cache state when storyId changes', async () => {
      const story1 = createMockStory({ id: 'story-1', isCached: true });
      const story2 = createMockStory({ id: 'story-2' });

      mockStoryCacheManager.isStoryCached
        .mockResolvedValueOnce(true)
        .mockResolvedValueOnce(false);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(story1);

      const { result, rerender } = renderHook<
        UseStoryCacheResult,
        { id: string; story: Story | undefined }
      >(
        ({ id, story }) => useStoryCache(id, story),
        { initialProps: { id: 'story-1', story: undefined as Story | undefined } }
      );

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      // Change to different story
      rerender({ id: 'story-2', story: story2 });

      await waitFor(() => {
        expect(result.current.isCached).toBe(false);
      });

      expect(result.current.story).toEqual(story2);
    });
  });

  describe('cache invalidation', () => {
    it('re-checks cache status when invalidation event is emitted', async () => {
      const cachedStory = createMockStory({ isCached: true });
      // Use undefined networkStory to avoid triggering background caching
      // when state transitions to uncached

      // Initially cached
      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('test-story-123', undefined));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      // Verify initial cache check was made
      const initialCallCount = mockStoryCacheManager.isStoryCached.mock.calls.length;

      // Simulate cache invalidation by changing mock return value
      mockStoryCacheManager.isStoryCached.mockResolvedValue(false);

      // Emit invalidation event - this triggers re-check
      cacheEvents.emit('test-story-123');

      // Wait for the async re-check to complete and update state
      await waitFor(() => {
        // Verify isStoryCached was called again after the event
        expect(mockStoryCacheManager.isStoryCached.mock.calls.length).toBeGreaterThan(initialCallCount);
      });

      // Should re-check and update to uncached
      await waitFor(() => {
        expect(result.current.isCached).toBe(false);
      });

      // After invalidation, getImageUrl should use server URL
      const spread = cachedStory.spreads![0];
      const url = result.current.getImageUrl('test-story-123', spread);
      expect(url).toContain('https://');
    });

    it('ignores invalidation events for other stories', async () => {
      const cachedStory = createMockStory({ id: 'story-1', isCached: true });

      mockStoryCacheManager.isStoryCached.mockResolvedValue(true);
      mockStoryCacheManager.loadCachedStory.mockResolvedValue(cachedStory);

      const { result } = renderHook(() => useStoryCache('story-1', undefined));

      await waitFor(() => {
        expect(result.current.isCached).toBe(true);
      });

      // Emit invalidation for different story
      await act(async () => {
        cacheEvents.emit('story-2');
      });

      // Should still be cached (event was for different story)
      expect(result.current.isCached).toBe(true);
    });
  });
});
