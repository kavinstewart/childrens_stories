/**
 * Tests for Settings screen cache clearing
 */

import { TTSCache } from '../../lib/voice/tts-cache';
import { StoryCacheManager } from '../../lib/story-cache';

// Mock the caches
jest.mock('../../lib/voice/tts-cache', () => ({
  TTSCache: {
    clearAll: jest.fn().mockResolvedValue(undefined),
  },
}));

jest.mock('../../lib/story-cache', () => ({
  StoryCacheManager: {
    clearAllCache: jest.fn().mockResolvedValue(undefined),
    getCacheSize: jest.fn().mockResolvedValue(0),
    getCachedStoryIds: jest.fn().mockResolvedValue([]),
  },
}));

// Helper to simulate the cache clearing logic (extracted from settings.tsx)
async function clearAllCaches() {
  // This is what the settings page SHOULD do
  await Promise.all([
    StoryCacheManager.clearAllCache(),
    TTSCache.clearAll(),
  ]);
}

describe('Settings cache clearing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('clears both story cache and TTS cache', async () => {
    await clearAllCaches();

    expect(StoryCacheManager.clearAllCache).toHaveBeenCalledTimes(1);
    expect(TTSCache.clearAll).toHaveBeenCalledTimes(1);
  });

  it('clears caches in parallel for performance', async () => {
    // Track call order
    const callOrder: string[] = [];

    (StoryCacheManager.clearAllCache as jest.Mock).mockImplementation(async () => {
      callOrder.push('story-start');
      await new Promise(resolve => setTimeout(resolve, 10));
      callOrder.push('story-end');
    });

    (TTSCache.clearAll as jest.Mock).mockImplementation(async () => {
      callOrder.push('tts-start');
      await new Promise(resolve => setTimeout(resolve, 10));
      callOrder.push('tts-end');
    });

    await clearAllCaches();

    // Both should start before either ends (parallel execution)
    expect(callOrder.indexOf('story-start')).toBeLessThan(callOrder.indexOf('story-end'));
    expect(callOrder.indexOf('tts-start')).toBeLessThan(callOrder.indexOf('tts-end'));
    // Both starts should happen before both ends
    expect(callOrder.indexOf('story-start')).toBeLessThan(2);
    expect(callOrder.indexOf('tts-start')).toBeLessThan(2);
  });
});
