/**
 * useStoryCache - Custom hook for managing story cache state
 *
 * Uses a discriminated union state machine to prevent invalid state combinations.
 * Possible states: 'checking' | 'uncached' | 'caching' | 'cached'
 *
 * The return interface is computed from the state machine for backward compatibility.
 */

import { useState, useEffect, useCallback } from 'react';
import { Story, StorySpread, api } from './api';
import { StoryCacheManager } from './story-cache';
import { cacheFiles } from './cache-files';

interface UseStoryCacheResult {
  /** The story to display - cached version if available, otherwise network version */
  story: Story | undefined;
  /** The cached story, if available */
  cachedStory: Story | null;
  /** Whether the story is cached locally */
  isCached: boolean;
  /** Whether the initial cache check has completed */
  cacheCheckComplete: boolean;
  /** Whether a caching operation is in progress */
  isCaching: boolean;
  /** Helper to get the correct image URL (local file:// or server URL) */
  getImageUrl: (storyId: string, spread: StorySpread) => string | null;
}

/**
 * State machine for cache states.
 * Each state explicitly defines what data is available.
 */
type CacheState =
  | { status: 'checking' }
  | { status: 'uncached' }
  | { status: 'caching' }
  | { status: 'cached'; story: Story }
  | { status: 'cache_failed' };

export function useStoryCache(
  storyId: string | undefined,
  networkStory: Story | undefined
): UseStoryCacheResult {
  const [state, setState] = useState<CacheState>({ status: 'checking' });

  // Compute return values from state machine
  const isCached = state.status === 'cached';
  const cachedStory = state.status === 'cached' ? state.story : null;
  const cacheCheckComplete = state.status !== 'checking';
  const isCaching = state.status === 'caching';
  // Note: cache_failed is treated as uncached for consumers (shows network story)

  // Use cached story if available, otherwise prefer network story
  const story = cachedStory || networkStory;

  // Helper to get the correct image URL based on cache status
  const getImageUrl = useCallback(
    (storyIdParam: string, spread: StorySpread): string | null => {
      if (!spread.illustration_url) return null;
      if (isCached) {
        // Use local file path for cached stories
        return cacheFiles.getSpreadPath(storyIdParam, spread.spread_number);
      }
      // Use server URL with cache busting
      return api.getSpreadImageUrl(storyIdParam, spread.spread_number, spread.illustration_updated_at);
    },
    [isCached]
  );

  // Check if story is already cached on mount and load it
  useEffect(() => {
    if (!storyId) return;

    // Reset to checking state for new story
    setState({ status: 'checking' });

    StoryCacheManager.isStoryCached(storyId).then(async (cached) => {
      if (cached) {
        const loaded = await StoryCacheManager.loadCachedStory(storyId);
        if (loaded) {
          setState({ status: 'cached', story: loaded });
          return;
        }
      }
      // Not cached or load failed
      setState({ status: 'uncached' });
    });
  }, [storyId]);

  // Trigger background caching when story loads (if eligible)
  // Only runs after cache check completes to avoid race condition
  // Note: StoryCacheManager.cacheStory handles deduplication of concurrent requests
  useEffect(() => {
    if (state.status !== 'uncached') return; // Only cache from uncached state
    if (!networkStory?.is_illustrated) return;
    if (networkStory.status !== 'completed') return;

    setState({ status: 'caching' });
    StoryCacheManager.cacheStory(networkStory)
      .then(async (success) => {
        if (success) {
          const loaded = await StoryCacheManager.loadCachedStory(networkStory.id);
          if (loaded) {
            setState({ status: 'cached', story: loaded });
            return;
          }
        }
        // Caching failed - use cache_failed state to prevent retry loop
        setState({ status: 'cache_failed' });
      })
      .catch(() => {
        setState({ status: 'cache_failed' });
      });
  }, [networkStory, state.status]);

  return {
    story,
    cachedStory,
    isCached,
    cacheCheckComplete,
    isCaching,
    getImageUrl,
  };
}
