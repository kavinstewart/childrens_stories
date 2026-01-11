/**
 * Tests for word-level TTS cache with context-aware keys
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { WordTTSCache, WordCacheKey, buildCacheKey, normalizeWord } from '../../../lib/voice/word-tts-cache';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

// Mock expo-file-system
jest.mock('expo-file-system', () => ({
  File: jest.fn().mockImplementation((dir, filename) => ({
    uri: `file://${dir?.uri || dir}/${filename || ''}`,
    exists: true,
    write: jest.fn(),
    bytes: jest.fn().mockResolvedValue(new Uint8Array([1, 2, 3])),
    delete: jest.fn(),
    size: 100,
  })),
  Directory: jest.fn().mockImplementation((base, name) => ({
    uri: `${base}/${name}`,
    exists: true,
    create: jest.fn(),
    delete: jest.fn(),
  })),
  Paths: {
    cache: 'file://cache',
  },
}));

describe('word-tts-cache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
  });

  describe('normalizeWord', () => {
    it('converts to lowercase', () => {
      expect(normalizeWord('Hello')).toBe('hello');
      expect(normalizeWord('WORLD')).toBe('world');
    });

    it('strips punctuation', () => {
      expect(normalizeWord('hello,')).toBe('hello');
      expect(normalizeWord('world!')).toBe('world');
      expect(normalizeWord('"hello"')).toBe('hello');
      expect(normalizeWord('said.')).toBe('said');
    });

    it('preserves contractions', () => {
      expect(normalizeWord("don't")).toBe("don't");
      expect(normalizeWord("it's")).toBe("it's");
    });

    it('handles hyphenated words', () => {
      expect(normalizeWord('well-known')).toBe('well-known');
    });
  });

  describe('buildCacheKey', () => {
    it('builds key from normalized word', () => {
      const key = buildCacheKey({ word: 'Hello' });
      expect(key).toBe('hello');
    });

    it('normalizes the word', () => {
      const key = buildCacheKey({ word: 'HELLO!' });
      expect(key).toBe('hello');
    });

    it('includes pronunciationIndex when provided', () => {
      const key = buildCacheKey({ word: 'read', pronunciationIndex: 1 });
      expect(key).toBe('read|p1');
    });

    it('omits pronunciationIndex when not provided', () => {
      const key = buildCacheKey({ word: 'hello' });
      expect(key).toBe('hello');
      expect(key).not.toContain('|p');
    });
  });

  describe('WordTTSCache.get', () => {
    it('returns null for cache miss', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify({ entries: {} }));

      const result = await WordTTSCache.get({ word: 'hello' });

      expect(result).toBeNull();
    });

    it('returns entry for cache hit', async () => {
      const mockEntry = {
        cacheKey: 'hello',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now(),
        durationMs: 250,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { 'hello': mockEntry } })
      );

      const result = await WordTTSCache.get({ word: 'hello' });

      expect(result).not.toBeNull();
      expect(result?.cacheKey).toBe('hello');
    });

    it('returns null for expired entry', async () => {
      const expiredEntry = {
        cacheKey: 'hello',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now() - (8 * 24 * 60 * 60 * 1000), // 8 days ago
        durationMs: 250,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { 'hello': expiredEntry } })
      );

      const result = await WordTTSCache.get({ word: 'hello' });

      expect(result).toBeNull();
    });
  });

  describe('WordTTSCache.set', () => {
    it('stores entry with correct cache key', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify({ entries: {} }));

      const audioData = new Uint8Array([1, 2, 3, 4]);
      await WordTTSCache.set({ word: 'hello' }, audioData, 250);

      expect(AsyncStorage.setItem).toHaveBeenCalled();
      const setItemCall = (AsyncStorage.setItem as jest.Mock).mock.calls[0];
      const savedIndex = JSON.parse(setItemCall[1]);
      expect(savedIndex.entries['hello']).toBeDefined();
      expect(savedIndex.entries['hello'].durationMs).toBe(250);
    });

    it('stores homograph with pronunciationIndex in key', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify({ entries: {} }));

      const audioData = new Uint8Array([1, 2, 3, 4]);
      await WordTTSCache.set({ word: 'read', pronunciationIndex: 1 }, audioData, 300);

      expect(AsyncStorage.setItem).toHaveBeenCalled();
      const setItemCall = (AsyncStorage.setItem as jest.Mock).mock.calls[0];
      const savedIndex = JSON.parse(setItemCall[1]);
      expect(savedIndex.entries['read|p1']).toBeDefined();
      expect(savedIndex.entries['read|p1'].durationMs).toBe(300);
    });
  });

  describe('WordTTSCache.clearAll', () => {
    it('removes index from AsyncStorage', async () => {
      await WordTTSCache.clearAll();
      expect(AsyncStorage.removeItem).toHaveBeenCalled();
    });
  });

  describe('homograph caching', () => {
    it('differentiates homographs with different pronunciations', () => {
      const keyPresent = buildCacheKey({
        word: 'read',
        pronunciationIndex: 0, // present tense "reed"
      });
      const keyPast = buildCacheKey({
        word: 'read',
        pronunciationIndex: 1, // past tense "red"
      });

      expect(keyPresent).toBe('read|p0');
      expect(keyPast).toBe('read|p1');
      expect(keyPresent).not.toBe(keyPast);
    });

    it('same word without pronunciationIndex produces same key', () => {
      // Without prosodic context, same word always gets same key
      const key1 = buildCacheKey({ word: 'cat' });
      const key2 = buildCacheKey({ word: 'cat' });

      expect(key1).toBe(key2);
      expect(key1).toBe('cat');
    });
  });
});
