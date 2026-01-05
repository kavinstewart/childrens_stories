/**
 * Unit tests for SQLite-based cache storage
 */
import { cacheStorage, CacheEntry, CacheIndex, _resetDbForTesting, migrateFromAsyncStorage } from '../../lib/cache-storage';
import AsyncStorage from '@react-native-async-storage/async-storage';

// In-memory SQLite store for testing
let mockStore: Map<string, CacheEntry> = new Map();

// Mock expo-sqlite with in-memory implementation
jest.mock('expo-sqlite', () => ({
  openDatabaseSync: jest.fn(() => ({
    execSync: jest.fn(),
    getAllSync: jest.fn(() => {
      return Array.from(mockStore.entries()).map(([id, entry]) => ({
        id,
        cached_at: entry.cachedAt,
        last_read: entry.lastRead,
        size_bytes: entry.sizeBytes,
        spread_count: entry.spreadCount,
        title: entry.title,
        goal: entry.goal,
        is_illustrated: entry.isIllustrated ? 1 : 0,
        cover_spread_number: entry.coverSpreadNumber,
      }));
    }),
    runSync: jest.fn((sql: string, ...params: unknown[]) => {
      if (sql.includes('INSERT OR REPLACE')) {
        const [id, cachedAt, lastRead, sizeBytes, spreadCount, title, goal, isIllustrated, coverSpreadNumber] = params;
        mockStore.set(id as string, {
          cachedAt: cachedAt as number,
          lastRead: lastRead as number,
          sizeBytes: sizeBytes as number,
          spreadCount: spreadCount as number,
          title: title as string,
          goal: goal as string,
          isIllustrated: (isIllustrated as number) === 1,
          coverSpreadNumber: coverSpreadNumber as number,
        });
      } else if (sql.includes('UPDATE')) {
        const [lastRead, id] = params;
        const entry = mockStore.get(id as string);
        if (entry) {
          entry.lastRead = lastRead as number;
        }
      } else if (sql.includes('DELETE')) {
        const [id] = params;
        mockStore.delete(id as string);
      }
    }),
    closeSync: jest.fn(),
  })),
}));

describe('cacheStorage', () => {
  beforeEach(async () => {
    mockStore.clear();
    await AsyncStorage.clear();
    _resetDbForTesting();
  });

  const createTestEntry = (overrides: Partial<CacheEntry> = {}): CacheEntry => ({
    cachedAt: 1704067200000,
    lastRead: 1704067200000,
    sizeBytes: 1024000,
    spreadCount: 12,
    title: 'Test Story',
    goal: 'adventure',
    isIllustrated: true,
    coverSpreadNumber: 1,
    ...overrides,
  });

  describe('getIndex', () => {
    it('returns empty object when no cache exists', async () => {
      const index = await cacheStorage.getIndex();
      expect(index).toEqual({});
    });

    it('returns all entries from database', async () => {
      mockStore.set('story-1', createTestEntry({ title: 'Story One' }));
      mockStore.set('story-2', createTestEntry({ title: 'Story Two' }));

      const index = await cacheStorage.getIndex();
      expect(Object.keys(index)).toHaveLength(2);
      expect(index['story-1'].title).toBe('Story One');
      expect(index['story-2'].title).toBe('Story Two');
    });

    it('returns index with correct entry properties', async () => {
      const entry = createTestEntry({
        cachedAt: 1704153600000,
        lastRead: 1704240000000,
        sizeBytes: 2048000,
        spreadCount: 8,
        title: 'My Story',
        goal: 'friendship',
        isIllustrated: false,
        coverSpreadNumber: 2,
      });
      mockStore.set('abc', entry);

      const index = await cacheStorage.getIndex();
      expect(index['abc']).toEqual(entry);
    });
  });

  describe('setStoryEntry', () => {
    it('adds entry to empty index', async () => {
      const entry = createTestEntry({ title: 'New Story' });
      await cacheStorage.setStoryEntry('story-new', entry);

      expect(mockStore.get('story-new')).toEqual(entry);
    });

    it('adds entry to existing index', async () => {
      mockStore.set('existing', createTestEntry({ title: 'Existing' }));

      const newEntry = createTestEntry({ title: 'New' });
      await cacheStorage.setStoryEntry('new', newEntry);

      expect(mockStore.get('existing')?.title).toBe('Existing');
      expect(mockStore.get('new')).toEqual(newEntry);
    });

    it('updates existing entry', async () => {
      mockStore.set('story-1', createTestEntry({ title: 'Original' }));

      const updatedEntry = createTestEntry({ title: 'Updated', sizeBytes: 999 });
      await cacheStorage.setStoryEntry('story-1', updatedEntry);

      expect(mockStore.get('story-1')?.title).toBe('Updated');
      expect(mockStore.get('story-1')?.sizeBytes).toBe(999);
    });

    it('handles UUID story IDs', async () => {
      const uuid = '123e4567-e89b-12d3-a456-426614174000';
      const entry = createTestEntry({ title: 'UUID Story' });
      await cacheStorage.setStoryEntry(uuid, entry);

      expect(mockStore.get(uuid)).toEqual(entry);
    });
  });

  describe('updateLastRead', () => {
    it('updates lastRead timestamp for existing entry', async () => {
      mockStore.set('story-1', createTestEntry({ lastRead: 1000 }));

      const beforeUpdate = Date.now();
      await cacheStorage.updateLastRead('story-1');
      const afterUpdate = Date.now();

      const updated = mockStore.get('story-1');
      expect(updated?.lastRead).toBeGreaterThanOrEqual(beforeUpdate);
      expect(updated?.lastRead).toBeLessThanOrEqual(afterUpdate);
    });

    it('does not modify other entry properties', async () => {
      const entry = createTestEntry({
        cachedAt: 5000,
        sizeBytes: 1234,
        spreadCount: 10,
        title: 'Test',
      });
      mockStore.set('story-1', entry);

      await cacheStorage.updateLastRead('story-1');

      const updated = mockStore.get('story-1');
      expect(updated?.cachedAt).toBe(5000);
      expect(updated?.sizeBytes).toBe(1234);
      expect(updated?.spreadCount).toBe(10);
      expect(updated?.title).toBe('Test');
    });

    it('does nothing for non-existent story', async () => {
      mockStore.set('story-1', createTestEntry({ lastRead: 1000 }));

      await cacheStorage.updateLastRead('non-existent');

      expect(mockStore.get('story-1')?.lastRead).toBe(1000);
      expect(mockStore.has('non-existent')).toBe(false);
    });
  });

  describe('removeStoryEntry', () => {
    it('removes entry from index', async () => {
      mockStore.set('story-1', createTestEntry({ title: 'One' }));
      mockStore.set('story-2', createTestEntry({ title: 'Two' }));

      await cacheStorage.removeStoryEntry('story-1');

      expect(mockStore.has('story-1')).toBe(false);
      expect(mockStore.has('story-2')).toBe(true);
    });

    it('handles removing non-existent entry gracefully', async () => {
      mockStore.set('story-1', createTestEntry());

      await cacheStorage.removeStoryEntry('non-existent');

      expect(mockStore.has('story-1')).toBe(true);
    });

    it('results in empty store when removing last entry', async () => {
      mockStore.set('only-story', createTestEntry());

      await cacheStorage.removeStoryEntry('only-story');

      expect(mockStore.size).toBe(0);
    });
  });

  describe('concurrent operations', () => {
    it('preserves all entries during concurrent setStoryEntry calls', async () => {
      const entries = Array.from({ length: 10 }, (_, i) => ({
        id: `story-${i}`,
        entry: createTestEntry({ title: `Story ${i}` }),
      }));

      await Promise.all(
        entries.map(({ id, entry }) => cacheStorage.setStoryEntry(id, entry))
      );

      expect(mockStore.size).toBe(10);
      for (const { id, entry } of entries) {
        expect(mockStore.get(id)).toEqual(entry);
      }
    });

    it('handles concurrent mixed operations correctly', async () => {
      await cacheStorage.setStoryEntry('story-1', createTestEntry({ title: 'Story 1' }));
      await cacheStorage.setStoryEntry('story-2', createTestEntry({ title: 'Story 2' }));

      await Promise.all([
        cacheStorage.setStoryEntry('story-3', createTestEntry({ title: 'Story 3' })),
        cacheStorage.updateLastRead('story-1'),
        cacheStorage.removeStoryEntry('story-2'),
      ]);

      expect(mockStore.size).toBe(2);
      expect(mockStore.has('story-1')).toBe(true);
      expect(mockStore.has('story-2')).toBe(false);
      expect(mockStore.has('story-3')).toBe(true);
    });
  });

  describe('migrateFromAsyncStorage', () => {
    it('migrates data from AsyncStorage to SQLite', async () => {
      const oldIndex: CacheIndex = {
        'story-1': createTestEntry({ title: 'Story One' }),
        'story-2': createTestEntry({ title: 'Story Two' }),
      };
      await AsyncStorage.setItem('story_cache_index', JSON.stringify(oldIndex));

      await migrateFromAsyncStorage();

      // Data should be in SQLite
      expect(mockStore.size).toBe(2);
      expect(mockStore.get('story-1')?.title).toBe('Story One');
      expect(mockStore.get('story-2')?.title).toBe('Story Two');

      // AsyncStorage should be cleared
      const remaining = await AsyncStorage.getItem('story_cache_index');
      expect(remaining).toBeNull();
    });

    it('does nothing when AsyncStorage is empty', async () => {
      await migrateFromAsyncStorage();
      expect(mockStore.size).toBe(0);
    });

    it('is idempotent (safe to call multiple times)', async () => {
      const oldIndex: CacheIndex = {
        'story-1': createTestEntry({ title: 'Story One' }),
      };
      await AsyncStorage.setItem('story_cache_index', JSON.stringify(oldIndex));

      await migrateFromAsyncStorage();
      await migrateFromAsyncStorage();

      expect(mockStore.size).toBe(1);
    });

    it('handles entries missing new fields with defaults', async () => {
      // Simulate old format without goal, isIllustrated, coverSpreadNumber
      const oldIndex = {
        'story-1': {
          cachedAt: 1704067200000,
          lastRead: 1704067200000,
          sizeBytes: 1024000,
          spreadCount: 12,
          title: 'Old Story',
        },
      };
      await AsyncStorage.setItem('story_cache_index', JSON.stringify(oldIndex));

      await migrateFromAsyncStorage();

      const migrated = mockStore.get('story-1');
      expect(migrated?.goal).toBe('');
      expect(migrated?.isIllustrated).toBe(false);
      expect(migrated?.coverSpreadNumber).toBe(1);
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
