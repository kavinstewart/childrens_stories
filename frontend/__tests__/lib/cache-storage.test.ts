/**
 * Unit tests for cache storage utilities
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { cacheStorage, CacheEntry, CacheIndex } from '../../lib/cache-storage';

describe('cacheStorage', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  const createTestEntry = (overrides: Partial<CacheEntry> = {}): CacheEntry => ({
    cachedAt: 1704067200000, // 2024-01-01T00:00:00.000Z
    lastRead: 1704067200000,
    sizeBytes: 1024000,
    spreadCount: 12,
    title: 'Test Story',
    ...overrides,
  });

  describe('getIndex', () => {
    it('returns empty object when no cache exists', async () => {
      const index = await cacheStorage.getIndex();
      expect(index).toEqual({});
    });

    it('returns parsed index when cache exists', async () => {
      const testIndex: CacheIndex = {
        'story-1': createTestEntry({ title: 'Story One' }),
        'story-2': createTestEntry({ title: 'Story Two' }),
      };
      await AsyncStorage.setItem('story_cache_index', JSON.stringify(testIndex));

      const index = await cacheStorage.getIndex();
      expect(index).toEqual(testIndex);
    });

    it('returns index with correct entry properties', async () => {
      const entry = createTestEntry({
        cachedAt: 1704153600000,
        lastRead: 1704240000000,
        sizeBytes: 2048000,
        spreadCount: 8,
        title: 'My Story',
      });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'abc': entry }));

      const index = await cacheStorage.getIndex();
      expect(index['abc']).toEqual(entry);
      expect(index['abc'].cachedAt).toBe(1704153600000);
      expect(index['abc'].lastRead).toBe(1704240000000);
      expect(index['abc'].sizeBytes).toBe(2048000);
      expect(index['abc'].spreadCount).toBe(8);
      expect(index['abc'].title).toBe('My Story');
    });
  });

  describe('setStoryEntry', () => {
    it('adds entry to empty index', async () => {
      const entry = createTestEntry({ title: 'New Story' });
      await cacheStorage.setStoryEntry('story-new', entry);

      const stored = await AsyncStorage.getItem('story_cache_index');
      expect(JSON.parse(stored!)).toEqual({ 'story-new': entry });
    });

    it('adds entry to existing index', async () => {
      const existingEntry = createTestEntry({ title: 'Existing' });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'existing': existingEntry }));

      const newEntry = createTestEntry({ title: 'New' });
      await cacheStorage.setStoryEntry('new', newEntry);

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['existing']).toEqual(existingEntry);
      expect(parsed['new']).toEqual(newEntry);
    });

    it('updates existing entry', async () => {
      const originalEntry = createTestEntry({ title: 'Original' });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'story-1': originalEntry }));

      const updatedEntry = createTestEntry({ title: 'Updated', sizeBytes: 999 });
      await cacheStorage.setStoryEntry('story-1', updatedEntry);

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1']).toEqual(updatedEntry);
      expect(parsed['story-1'].title).toBe('Updated');
      expect(parsed['story-1'].sizeBytes).toBe(999);
    });

    it('handles UUID story IDs', async () => {
      const uuid = '123e4567-e89b-12d3-a456-426614174000';
      const entry = createTestEntry({ title: 'UUID Story' });
      await cacheStorage.setStoryEntry(uuid, entry);

      const index = await cacheStorage.getIndex();
      expect(index[uuid]).toEqual(entry);
    });
  });

  describe('updateLastRead', () => {
    it('updates lastRead timestamp for existing entry', async () => {
      const entry = createTestEntry({ lastRead: 1000 });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'story-1': entry }));

      const beforeUpdate = Date.now();
      await cacheStorage.updateLastRead('story-1');
      const afterUpdate = Date.now();

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1'].lastRead).toBeGreaterThanOrEqual(beforeUpdate);
      expect(parsed['story-1'].lastRead).toBeLessThanOrEqual(afterUpdate);
    });

    it('does not modify other entry properties', async () => {
      const entry = createTestEntry({
        cachedAt: 5000,
        sizeBytes: 1234,
        spreadCount: 10,
        title: 'Test',
      });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'story-1': entry }));

      await cacheStorage.updateLastRead('story-1');

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1'].cachedAt).toBe(5000);
      expect(parsed['story-1'].sizeBytes).toBe(1234);
      expect(parsed['story-1'].spreadCount).toBe(10);
      expect(parsed['story-1'].title).toBe('Test');
    });

    it('does nothing for non-existent story', async () => {
      const entry = createTestEntry({ lastRead: 1000 });
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'story-1': entry }));

      await cacheStorage.updateLastRead('non-existent');

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1'].lastRead).toBe(1000);
      expect(parsed['non-existent']).toBeUndefined();
    });

    it('does nothing when index is empty', async () => {
      await cacheStorage.updateLastRead('any-story');

      const stored = await AsyncStorage.getItem('story_cache_index');
      expect(stored).toBeNull();
    });
  });

  describe('removeStoryEntry', () => {
    it('removes entry from index', async () => {
      const testIndex: CacheIndex = {
        'story-1': createTestEntry({ title: 'One' }),
        'story-2': createTestEntry({ title: 'Two' }),
      };
      await AsyncStorage.setItem('story_cache_index', JSON.stringify(testIndex));

      await cacheStorage.removeStoryEntry('story-1');

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1']).toBeUndefined();
      expect(parsed['story-2']).toEqual(testIndex['story-2']);
    });

    it('handles removing non-existent entry gracefully', async () => {
      const entry = createTestEntry();
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'story-1': entry }));

      await cacheStorage.removeStoryEntry('non-existent');

      const stored = await AsyncStorage.getItem('story_cache_index');
      const parsed = JSON.parse(stored!);
      expect(parsed['story-1']).toEqual(entry);
    });

    it('results in empty object when removing last entry', async () => {
      const entry = createTestEntry();
      await AsyncStorage.setItem('story_cache_index', JSON.stringify({ 'only-story': entry }));

      await cacheStorage.removeStoryEntry('only-story');

      const stored = await AsyncStorage.getItem('story_cache_index');
      expect(JSON.parse(stored!)).toEqual({});
    });
  });

  describe('integration scenarios', () => {
    it('handles typical cache lifecycle', async () => {
      // Add first story
      const story1 = createTestEntry({ title: 'Story 1', spreadCount: 10 });
      await cacheStorage.setStoryEntry('story-1', story1);

      // Add second story
      const story2 = createTestEntry({ title: 'Story 2', spreadCount: 8 });
      await cacheStorage.setStoryEntry('story-2', story2);

      // Verify both exist
      let index = await cacheStorage.getIndex();
      expect(Object.keys(index)).toHaveLength(2);

      // Update lastRead for story-1
      await cacheStorage.updateLastRead('story-1');
      index = await cacheStorage.getIndex();
      expect(index['story-1'].lastRead).toBeGreaterThan(story1.lastRead);

      // Remove story-2
      await cacheStorage.removeStoryEntry('story-2');
      index = await cacheStorage.getIndex();
      expect(Object.keys(index)).toHaveLength(1);
      expect(index['story-1']).toBeDefined();
      expect(index['story-2']).toBeUndefined();

      // Remove last story
      await cacheStorage.removeStoryEntry('story-1');
      index = await cacheStorage.getIndex();
      expect(index).toEqual({});
    });
  });
});
