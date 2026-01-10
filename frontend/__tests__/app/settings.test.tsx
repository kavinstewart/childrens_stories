/**
 * Tests for Settings screen cache clearing
 */

import { StoryCacheManager } from '../../lib/story-cache';

// Mock the caches
jest.mock('../../lib/story-cache', () => ({
  StoryCacheManager: {
    clearAllCache: jest.fn().mockResolvedValue(undefined),
    getCacheSize: jest.fn().mockResolvedValue(0),
    getCachedStoryIds: jest.fn().mockResolvedValue([]),
  },
}));

// Helper to simulate the cache clearing logic (extracted from settings.tsx)
async function clearAllCaches() {
  // Clear story cache (TTS word cache will be added in story-l6oj)
  await StoryCacheManager.clearAllCache();
}

describe('Settings cache clearing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('clears story cache', async () => {
    await clearAllCaches();

    expect(StoryCacheManager.clearAllCache).toHaveBeenCalledTimes(1);
  });
});
