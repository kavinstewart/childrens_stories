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
  shouldSyncWithSettings: jest.fn().mockResolvedValue(true),
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
    getStory: jest.fn().mockImplementation((id: string) => Promise.resolve({
      id,
      status: 'completed',
      goal: 'test goal',
      target_age_range: '4-8',
      generation_type: 'illustrated',
      is_illustrated: true,
      created_at: new Date().toISOString(),
      spreads: [{ spread_number: 1, text: 'test', word_count: 1, was_revised: false, illustration_url: 'http://test.com/1.png' }],
    })),
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
    mockNetworkAware.shouldSyncWithSettings.mockResolvedValue(true);
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
      expect(SYNC_CONFIG.FAILED_ENTRY_TTL_MS).toBe(24 * 60 * 60 * 1000); // 24 hours
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
      // cacheStory is called with full story from getStory, check by id
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'story-2' })
      );
    });

    it('skips non-completed stories', async () => {
      const pendingStory = createTestStory({ id: 'pending', status: 'pending' });
      const completedStory = createTestStory({ id: 'completed', status: 'completed' });

      await CacheSync.syncIfNeeded([pendingStory, completedStory]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      // cacheStory is called with full story from getStory, check by id
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'completed' })
      );
    });

    it('skips non-illustrated stories', async () => {
      const illustrated = createTestStory({ id: 'illustrated', is_illustrated: true });
      const notIllustrated = createTestStory({ id: 'not-illustrated', is_illustrated: false });

      await CacheSync.syncIfNeeded([illustrated, notIllustrated]);

      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      // cacheStory is called with full story from getStory, check by id
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'illustrated' })
      );
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

  describe('failedStories TTL cleanup', () => {
    it('cleans up old failure entries after TTL expires', async () => {
      // Mock Date.now to simulate time passing
      const originalDateNow = Date.now;
      let currentTime = 1000000000000; // Fixed start time
      Date.now = jest.fn(() => currentTime);

      try {
        // Trigger a failed download
        mockStoryCacheManager.cacheStory.mockResolvedValueOnce(false);
        const story = createTestStory({ id: 'failing-story' });

        await CacheSync.syncIfNeeded([story]);
        expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);

        // Move time forward past the backoff but within TTL
        currentTime += 70000; // 70 seconds (past max backoff of 60s)

        // Reset mocks but not CacheSync state
        mockStoryCacheManager.cacheStory.mockClear();
        mockStoryCacheManager.getCachedStoryIds.mockResolvedValue([]);

        // Move time past throttle window
        currentTime += SYNC_CONFIG.SYNC_THROTTLE_MS + 1000;

        // Story should be retried (backoff expired)
        mockStoryCacheManager.cacheStory.mockResolvedValueOnce(false);
        await CacheSync.syncIfNeeded([story]);
        expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);

        // Move time forward past the TTL (24 hours)
        currentTime += SYNC_CONFIG.FAILED_ENTRY_TTL_MS + 1000;

        // Reset mocks again
        mockStoryCacheManager.cacheStory.mockClear();
        mockStoryCacheManager.getCachedStoryIds.mockResolvedValue([]);

        // Move time past throttle window again
        currentTime += SYNC_CONFIG.SYNC_THROTTLE_MS + 1000;

        // Story should be retried with reset retry count (TTL cleanup removed old entry)
        mockStoryCacheManager.cacheStory.mockResolvedValueOnce(true);
        await CacheSync.syncIfNeeded([story]);

        // Should have been called - the old failure entry was cleaned up
        expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledTimes(1);
      } finally {
        Date.now = originalDateNow;
      }
    });
  });

  describe('network disconnect mid-sync', () => {
    it('checks shouldSyncWithSettings at start of each outer loop iteration', async () => {
      // When shouldSyncWithSettings returns false at the start of the loop,
      // no downloads should start for that iteration.
      // Note: The check happens per outer loop iteration, not per download.
      // More granular cancellation would require AbortController (see bead story-j9ql).

      mockNetworkAware.shouldSync.mockResolvedValue(true); // Initial check passes
      mockNetworkAware.shouldSyncWithSettings.mockResolvedValue(false); // Loop check fails

      const stories = [
        createTestStory({ id: 'story-1' }),
        createTestStory({ id: 'story-2' }),
      ];

      await CacheSync.syncIfNeeded(stories);

      // No stories should be downloaded because shouldSyncWithSettings returns false
      expect(mockStoryCacheManager.cacheStory).not.toHaveBeenCalled();
    });

    it('stops processing when shouldSyncWithSettings becomes false between batches', async () => {
      // This test verifies the outer loop break works when downloads stay active
      // long enough to hit the concurrency limit and exit the inner loop.
      const stories = Array.from({ length: 6 }, (_, i) =>
        createTestStory({ id: `story-${i}` })
      );

      let downloadCount = 0;
      let networkAvailable = true;

      // Downloads must stay active through the INTER_STORY_DELAY (500ms)
      // so activeDownloads.size stays at 2, forcing exit from inner loop
      mockStoryCacheManager.cacheStory.mockImplementation(async () => {
        downloadCount++;
        // Very long download so concurrency limit is reached and maintained
        await new Promise(r => setTimeout(r, 2000));
        // After 2 downloads complete, disable network
        if (downloadCount >= 2) {
          networkAvailable = false;
        }
        return true;
      });

      // Mock shouldSyncWithSettings to check our networkAvailable flag
      mockNetworkAware.shouldSyncWithSettings.mockImplementation(async () => networkAvailable);

      await CacheSync.syncIfNeeded(stories);

      // With 2000ms downloads:
      // - t=0: start s0, start s1 at t=500 (concurrency=2, exit inner loop)
      // - Wait for one to complete via Promise.race
      // - t=2000: s0 completes (count=1), outer loop checks network (still true)
      // - Inner loop starts s2, s3
      // - t=2500: s1 completes (count=2), network=false
      // - t=4000: s2 completes, outer loop checks network (now false), break
      // Expected downloads: 4 (s0, s1, s2, s3 started before network check fails)
      expect(downloadCount).toBeGreaterThanOrEqual(2);
      expect(downloadCount).toBeLessThan(6);
    }, 30000);
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
      // cacheStory is called with full story from getStory, check by id
      expect(mockStoryCacheManager.cacheStory).toHaveBeenCalledWith(
        expect.objectContaining({ id: 'api-story' })
      );
    });

    it('silently fails when API call fails', async () => {
      mockApi.listStories.mockRejectedValue(new Error('Network error'));

      // Should not throw
      await expect(CacheSync.triggerSync()).resolves.toBeUndefined();
    });
  });

  describe('cancelSync', () => {
    it('stops any in-progress sync', async () => {
      const stories = Array.from({ length: 5 }, (_, i) =>
        createTestStory({ id: `story-${i}` })
      );

      let downloadStarted = 0;

      // Mock getStory to have a delay so we can cancel during fetch
      mockApi.getStory.mockImplementation(async (id: string) => {
        await new Promise(r => setTimeout(r, 500));
        return {
          id,
          status: 'completed',
          goal: 'test goal',
          target_age_range: '4-8',
          generation_type: 'illustrated',
          is_illustrated: true,
          created_at: new Date().toISOString(),
          spreads: [{ spread_number: 1, text: 'test', word_count: 1, was_revised: false, illustration_url: 'http://test.com/1.png' }],
        };
      });

      mockStoryCacheManager.cacheStory.mockImplementation(async () => {
        downloadStarted++;
        // Long delay so we can cancel mid-sync
        await new Promise(r => setTimeout(r, 1000));
        return true;
      });

      // Start sync in background
      const syncPromise = CacheSync.syncIfNeeded(stories);

      // Wait for at least one download to start (getStory delay + some buffer)
      await new Promise(r => setTimeout(r, 600));

      // Cancel sync
      CacheSync.cancelSync();

      // Wait for sync to finish
      await syncPromise;

      // Should have started at least 1 but not all 5
      expect(downloadStarted).toBeGreaterThanOrEqual(1);
      expect(downloadStarted).toBeLessThan(5);
    }, 15000);

    it('does nothing if no sync is running', () => {
      // Should not throw
      expect(() => CacheSync.cancelSync()).not.toThrow();
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
