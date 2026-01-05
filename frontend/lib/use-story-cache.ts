/**
 * useStoryCache - Custom hook for managing story cache state
 *
 * Encapsulates:
 * - Cache check on mount
 * - Loading cached story
 * - Triggering background cache for eligible stories
 * - State consistency management
 */

import { useState, useEffect, useCallback } from 'react';
import { Story, StorySpread, api } from './api';
import { StoryCacheManager } from './story-cache';
import { cacheFiles } from './cache-files';

interface CacheState {
  isCached: boolean;
  story: Story | null;
  checkComplete: boolean;
}

interface UseStoryCacheResult {
  /** The story to display - cached version if available, otherwise network version */
  story: Story | undefined;
  /** Whether the story is cached locally */
  isCached: boolean;
  /** Whether a caching operation is in progress */
  isCaching: boolean;
  /** Helper to get the correct image URL (local file:// or server URL) */
  getImageUrl: (storyId: string, spread: StorySpread) => string | null;
}

export function useStoryCache(
  storyId: string | undefined,
  networkStory: Story | undefined
): UseStoryCacheResult {
  const [isCaching, setIsCaching] = useState(false);
  const [cacheState, setCacheState] = useState<CacheState>({
    isCached: false,
    story: null,
    checkComplete: false,
  });

  // Use cached story if available, otherwise prefer network story
  const story = cacheState.story || networkStory;

  // Helper to get the correct image URL based on cache status
  const getImageUrl = useCallback(
    (storyIdParam: string, spread: StorySpread): string | null => {
      if (!spread.illustration_url) return null;
      if (cacheState.isCached) {
        // Use local file path for cached stories
        return cacheFiles.getSpreadPath(storyIdParam, spread.spread_number);
      }
      // Use server URL with cache busting
      return api.getSpreadImageUrl(storyIdParam, spread.spread_number, spread.illustration_updated_at);
    },
    [cacheState.isCached]
  );

  // Check if story is already cached on mount and load it
  useEffect(() => {
    if (!storyId) return;

    // Reset cache state atomically for new story
    setCacheState({ isCached: false, story: null, checkComplete: false });

    StoryCacheManager.isStoryCached(storyId).then(async (cached) => {
      console.log(`[Cache] isStoryCached(${storyId}): ${cached}`);
      if (cached) {
        const loaded = await StoryCacheManager.loadCachedStory(storyId);
        if (loaded) {
          console.log(`[Cache] Loaded cached story (isCached=true, URLs computed at render)`);
          // Set all cache state atomically
          setCacheState({ isCached: true, story: loaded, checkComplete: true });
          return;
        }
      }
      // Not cached or load failed
      setCacheState({ isCached: false, story: null, checkComplete: true });
    });
  }, [storyId]);

  // Trigger background caching when story loads (if eligible)
  // Only runs after cache check completes to avoid race condition
  // Note: StoryCacheManager.cacheStory handles deduplication of concurrent requests
  useEffect(() => {
    if (!cacheState.checkComplete) return; // Wait for cache check to finish
    if (!networkStory?.is_illustrated) return;
    if (networkStory.status !== 'completed') return;
    if (cacheState.isCached) return;

    setIsCaching(true);
    console.log(`[Reader] Triggering cache for story ${networkStory.id}`);
    StoryCacheManager.cacheStory(networkStory)
      .then(async (success) => {
        console.log(`[Reader] Cache result for story ${networkStory.id}: ${success ? 'succeeded' : 'failed'}`);
        if (success) {
          // Load and set atomically
          const loaded = await StoryCacheManager.loadCachedStory(networkStory.id);
          if (loaded) {
            setCacheState(prev => ({ ...prev, isCached: true, story: loaded }));
          }
        }
      })
      .finally(() => {
        setIsCaching(false);
      });
  }, [networkStory, cacheState.isCached, cacheState.checkComplete]);

  return {
    story,
    isCached: cacheState.isCached,
    isCaching,
    getImageUrl,
  };
}
