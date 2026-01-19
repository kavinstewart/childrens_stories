/**
 * Cache invalidation event emitter for story cache.
 * Allows components to subscribe to cache invalidation events
 * and re-check cache status when a story's cache is invalidated.
 */

type Callback = () => void;

class CacheEventEmitter {
  private listeners = new Map<string, Set<Callback>>();

  /**
   * Subscribe to cache invalidation events for a specific story.
   * @param storyId The story ID to listen for
   * @param callback Called when the story's cache is invalidated
   * @returns Unsubscribe function
   */
  subscribe(storyId: string, callback: Callback): () => void {
    if (!this.listeners.has(storyId)) {
      this.listeners.set(storyId, new Set());
    }
    this.listeners.get(storyId)!.add(callback);

    return () => {
      this.listeners.get(storyId)?.delete(callback);
      // Clean up empty sets
      if (this.listeners.get(storyId)?.size === 0) {
        this.listeners.delete(storyId);
      }
    };
  }

  /**
   * Emit a cache invalidation event for a story.
   * @param storyId The story ID that was invalidated
   */
  emit(storyId: string): void {
    this.listeners.get(storyId)?.forEach((cb) => cb());
  }
}

export const cacheEvents = new CacheEventEmitter();
