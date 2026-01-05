/**
 * Unit tests for automatic cache sync manager
 */
import { Story } from '../../lib/api';

// Mock dependencies BEFORE importing the module
jest.mock('../../lib/story-cache', () => ({
  StoryCacheManager: {
    cacheStory: jest.fn().mockResolvedValue(true),
    isStoryCached: jest.fn().mockResolvedValue(false),
    getCachedStoryIds: jest.fn().mockResolvedValue([]),
  },
}));

jest.mock('../../lib/network-aware', () => ({
  shouldSync: jest.fn().mockResolvedValue(true),
  getSyncSettings: jest.fn().mockResolvedValue({
    autoDownloadEnabled: true,
    allowCellular: false,
  }),
  subscribeToNetworkChanges: jest.fn().mockReturnValue(jest.fn()),
}));

jest.mock('../../lib/api', () => ({
  api: {
    listStories: jest.fn().mockResolvedValue({
      stories: [],
      total: 0,
      limit: 10,
      offset: 0,
    }),
  },
}));

// Import after mocks
import { CacheSync, SYNC_CONFIG } from '../../lib/cache-sync';
import { StoryCacheManager } from '../../lib/story-cache';
import * as networkAware from '../../lib/network-aware';
import { api } from '../../lib/api';

const mockStoryCacheManager = StoryCacheManager as jest.Mocked<typeof StoryCacheManager>;
const mockNetworkAware = networkAware as jest.Mocked<typeof networkAware>;
const mockApi = api as jest.Mocked<typeof api>;

// Helper to create test stories
const createTestStory = (overrides: Partial<Story> = {}): Story => ({
  id: `story-${Math.random().toString(36).slice(2, 8)}`,
  status: 'completed',
  goal: 'test goal',
  target_age_range: '4-8',
  generation_type: 'illustrated',
  is_illustrated: true,
  created_at: new Date().toISOString(),
  spreads: [{ spread_number: 1, text: 'test', word_count: 1, was_revised: false, illustration_url: 'http://test.com/1.png' }],
  ...overrides,
});

describe('CacheSync', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNetworkAware.shouldSync.mockResolvedValue(true);
    mockStoryCacheManager.getCachedStoryIds.mockResolvedValue([]);
    mockStoryCacheManager.cacheStory.mockResolvedValue(true);
    CacheSync.reset();
  });

  describe('SYNC_CONFIG', () => {
    it('has sensible defaults', () => {
      expect(SYNC_CONFIG.MAX_CONCURRENT_DOWNLOADS).toBe(2);
      expect(SYNC_CONFIG.MAX_STORIES_PER_SYNC).toBe(20);
      expect(SYNC_CONFIG.SYNC_THROTTLE_MS).toBeGreaterThan(0);
      expect(SYNC_CONFIG.INTER_STORY_DELAY_MS).toBeGreaterThan(0);
    });
  });

  describe('syncIfNeeded', () => {
    it('does nothing when shouldSync returns false', async () => {
      mockNetworkAware.shouldSync.mockResolvedValue(false);

      await CacheSync.syncIfNeeded([createTestStory()]);

      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });

    it('caches uncached completed illustrated stories', async () => {
      const story1 = createTestStory({ id: 'story-1' });
      const story2 = createTestStory({ id: 'story-2' });

      await CacheSync.syncIfNeeded([story1, story2]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(2);
    });

    it('skips already cached stories', async () => {
      mockStoryCacheManager.getCachedStoryIds.mockResolvedValue(['story-1']);

      const story1 = createTestStory({ id: 'story-1' });
      const story2 = createTestStory({ id: 'story-2' });

      await CacheSync.syncIfNeeded([story1, story2]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(story2);
    });

    it('skips non-completed stories', async () => {
      const pendingStory = createTestStory({ id: 'pending', status: 'pending' });
      const completedStory = createTestStory({ id: 'completed', status: 'completed' });

      await CacheSync.syncIfNeeded([pendingStory, completedStory]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(completedStory);
    });

    it('skips non-illustrated stories', async () => {
      const illustrated = createTestStory({ id: 'illustrated', is_illustrated: true });
      const notIllustrated = createTestStory({ id: 'not-illustrated', is_illustrated: false });

      await CacheSync.syncIfNeeded([illustrated, notIllustrated]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(illustrated);
    });

    it('respects MAX_STORIES_PER_SYNC limit', async () => {
      const stories = Array.from({ length: 30 }, (_, i) =>
        createTestStory({ id: `story-${i}` })
      );

      await CacheSync.syncIfNeeded(stories);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(SYNC_CONFIG.MAX_STORIES_PER_SYNC);
    }, 15000); // Longer timeout due to INTER_STORY_DELAY

    it('continues syncing remaining stories after failure', async () => {
      mockStoryCacheManager.cacheStory
        .mockResolvedValueOnce(false)
        .mockResolvedValueOnce(true);

      const story1 = createTestStory({ id: 'story-1' });
      const story2 = createTestStory({ id: 'story-2' });

      await CacheSync.syncIfNeeded([story1, story2]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(2);
    });

    it('throttles rapid sync calls within SYNC_THROTTLE_MS', async () => {
      const story = createTestStory({ id: 'story-1' });

      // First sync should succeed
      await CacheSync.syncIfNeeded([story]);
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);

      // Reset mock but not CacheSync state (don't call CacheSync.reset())
      mockStoryCacheManager.cacheStory.mockClear();
      mockStoryCacheManager.getCachedStoryIds.mockResolvedValue([]); // Story not cached

      // Immediate second sync should be throttled (within 5 minute window)
      await CacheSync.syncIfNeeded([story]);
      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });
  });

  describe('boostPriority', () => {
    it('does not throw when called', () => {
      expect(() => CacheSync.boostPriority('some-story-id')).not.toThrow();
    });
  });

  describe('getStatus', () => {
    it('returns current sync status', () => {
      const status = CacheSync.getStatus();

      expect(status).toHaveProperty('isRunning');
      expect(status).toHaveProperty('queueLength');
      expect(status).toHaveProperty('activeDownloads');
    });
  });

  describe('reset', () => {
    it('clears sync state', () => {
      CacheSync.reset();

      const status = CacheSync.getStatus();
      expect(status.queueLength).toBe(0);
      expect(status.activeDownloads).toBe(0);
    });
  });

  describe('priority ordering', () => {
    it('processes stories in order of creation (newest first)', async () => {
      const cacheOrder: string[] = [];
      mockStoryCacheManager.cacheStory.mockImplementation(async (story) => {
        cacheOrder.push(story.id);
        return true;
      });

      const oldStory = createTestStory({
        id: 'old',
        created_at: '2024-01-01T00:00:00Z'
      });
      const newStory = createTestStory({
        id: 'new',
        created_at: '2024-12-01T00:00:00Z'
      });

      await CacheSync.syncIfNeeded([oldStory, newStory]);

      expect(cacheOrder[0]).toBe('new');
      expect(cacheOrder[1]).toBe('old');
    });
  });

  describe('triggerSync', () => {
    it('fetches stories from API and syncs them', async () => {
      const stories = [createTestStory({ id: 'api-story' })];
      mockApi.listStories.mockResolvedValue({
        stories,
        total: 1,
        limit: 10,
        offset: 0,
      });

      await CacheSync.triggerSync();

      expect(mockApi.listStories).toHaveBeenCalled();
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(stories[0]);
    });

    it('silently fails when API call fails', async () => {
      mockApi.listStories.mockRejectedValue(new Error('Network error'));

      // Should not throw
      await expect(CacheSync.triggerSync()).resolves.toBeUndefined();
    });
  });

  describe('startAutoSync', () => {
    it('subscribes to network changes', () => {
      const unsubscribe = CacheSync.startAutoSync();

      expect(mockNetworkAware.subscribeToNetworkChanges).toHaveBeenCalled();
      expect(typeof unsubscribe).toBe('function');
    });

    it('triggers initial sync on start', async () => {
      mockApi.listStories.mockResolvedValue({
        stories: [createTestStory()],
        total: 1,
        limit: 10,
        offset: 0,
      });

      CacheSync.startAutoSync();

      // Give it a moment to trigger
      await new Promise(r => setTimeout(r, 10));

      expect(mockApi.listStories).toHaveBeenCalled();
    });

    it('returns unsubscribe function', () => {
      const mockUnsubscribe = jest.fn();
      mockNetworkAware.subscribeToNetworkChanges.mockReturnValue(mockUnsubscribe);

      const unsubscribe = CacheSync.startAutoSync();
      unsubscribe();

      expect(mockUnsubscribe).toHaveBeenCalled();
    });
  });
});
