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

export function useStoryCache(
  storyId: string | undefined,
  networkStory: Story | undefined
): UseStoryCacheResult {
  const [isCached, setIsCached] = useState(false);
  const [cachedStory, setCachedStory] = useState<Story | null>(null);
  const [cacheCheckComplete, setCacheCheckComplete] = useState(false);
  const [isCaching, setIsCaching] = useState(false);

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

    // Reset cache state for new story
    setIsCached(false);
    setCachedStory(null);
    setCacheCheckComplete(false);

    StoryCacheManager.isStoryCached(storyId).then(async (cached) => {
      if (cached) {
        const loaded = await StoryCacheManager.loadCachedStory(storyId);
        if (loaded) {
          setIsCached(true);
          setCachedStory(loaded);
          setCacheCheckComplete(true);
          return;
        }
      }
      // Not cached or load failed
      setCacheCheckComplete(true);
    });
  }, [storyId]);

  // Trigger background caching when story loads (if eligible)
  // Only runs after cache check completes to avoid race condition
  // Note: StoryCacheManager.cacheStory handles deduplication of concurrent requests
  useEffect(() => {
    if (!cacheCheckComplete) return; // Wait for cache check to finish
    if (!networkStory?.is_illustrated) return;
    if (networkStory.status !== 'completed') return;
    if (isCached) return;

    setIsCaching(true);
    StoryCacheManager.cacheStory(networkStory)
      .then(async (success) => {
        if (success) {
          const loaded = await StoryCacheManager.loadCachedStory(networkStory.id);
          if (loaded) {
            setIsCached(true);
            setCachedStory(loaded);
          }
        }
      })
      .finally(() => {
        setIsCaching(false);
      });
  }, [networkStory, isCached, cacheCheckComplete]);

  return {
    story,
    cachedStory,
    isCached,
    cacheCheckComplete,
    isCaching,
    getImageUrl,
  };
}
