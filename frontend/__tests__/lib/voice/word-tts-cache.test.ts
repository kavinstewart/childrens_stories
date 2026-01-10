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
    it('builds key with all components', () => {
      const key = buildCacheKey({
        word: 'Hello',
        position: 'start',
        punctuation: ',',
        sentenceType: 'statement',
      });
      expect(key).toBe('hello|start|,|statement');
    });

    it('handles empty punctuation', () => {
      const key = buildCacheKey({
        word: 'world',
        position: 'mid',
        punctuation: '',
        sentenceType: 'question',
      });
      expect(key).toBe('world|mid||question');
    });

    it('normalizes the word', () => {
      const key = buildCacheKey({
        word: 'HELLO!',
        position: 'end',
        punctuation: '!',
        sentenceType: 'exclamation',
      });
      expect(key).toBe('hello|end|!|exclamation');
    });
  });

  describe('WordTTSCache.get', () => {
    it('returns null for cache miss', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify({ entries: {} }));

      const result = await WordTTSCache.get({
        word: 'hello',
        position: 'start',
        punctuation: '',
        sentenceType: 'statement',
      });

      expect(result).toBeNull();
    });

    it('returns entry for cache hit', async () => {
      const mockEntry = {
        cacheKey: 'hello|start||statement',
        audioPath: 'file://cache/tts-words/hello_start_statement.pcm',
        cachedAt: Date.now(),
        durationMs: 250,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { 'hello|start||statement': mockEntry } })
      );

      const result = await WordTTSCache.get({
        word: 'hello',
        position: 'start',
        punctuation: '',
        sentenceType: 'statement',
      });

      expect(result).not.toBeNull();
      expect(result?.cacheKey).toBe('hello|start||statement');
    });

    it('returns null for expired entry', async () => {
      const expiredEntry = {
        cacheKey: 'hello|start||statement',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now() - (8 * 24 * 60 * 60 * 1000), // 8 days ago
        durationMs: 250,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { 'hello|start||statement': expiredEntry } })
      );

      const result = await WordTTSCache.get({
        word: 'hello',
        position: 'start',
        punctuation: '',
        sentenceType: 'statement',
      });

      expect(result).toBeNull();
    });
  });

  describe('WordTTSCache.set', () => {
    it('stores entry with correct cache key', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify({ entries: {} }));

      const audioData = new Uint8Array([1, 2, 3, 4]);
      await WordTTSCache.set(
        {
          word: 'hello',
          position: 'start',
          punctuation: '',
          sentenceType: 'statement',
        },
        audioData,
        250
      );

      expect(AsyncStorage.setItem).toHaveBeenCalled();
      const setItemCall = (AsyncStorage.setItem as jest.Mock).mock.calls[0];
      const savedIndex = JSON.parse(setItemCall[1]);
      expect(savedIndex.entries['hello|start||statement']).toBeDefined();
      expect(savedIndex.entries['hello|start||statement'].durationMs).toBe(250);
    });
  });

  describe('WordTTSCache.clearAll', () => {
    it('removes index from AsyncStorage', async () => {
      await WordTTSCache.clearAll();
      expect(AsyncStorage.removeItem).toHaveBeenCalled();
    });
  });

  describe('context-aware caching scenarios', () => {
    it('differentiates same word in different positions', async () => {
      const keyStart = buildCacheKey({
        word: 'cat',
        position: 'start',
        punctuation: '',
        sentenceType: 'statement',
      });
      const keyMid = buildCacheKey({
        word: 'cat',
        position: 'mid',
        punctuation: '',
        sentenceType: 'statement',
      });
      const keyEnd = buildCacheKey({
        word: 'cat',
        position: 'end',
        punctuation: '.',
        sentenceType: 'statement',
      });

      expect(keyStart).not.toBe(keyMid);
      expect(keyMid).not.toBe(keyEnd);
      expect(keyStart).not.toBe(keyEnd);
    });

    it('differentiates same word in different sentence types', async () => {
      const keyStatement = buildCacheKey({
        word: 'why',
        position: 'start',
        punctuation: '',
        sentenceType: 'statement',
      });
      const keyQuestion = buildCacheKey({
        word: 'why',
        position: 'start',
        punctuation: '',
        sentenceType: 'question',
      });

      expect(keyStatement).not.toBe(keyQuestion);
    });

    it('differentiates same word with different punctuation', async () => {
      const keyComma = buildCacheKey({
        word: 'hello',
        position: 'mid',
        punctuation: ',',
        sentenceType: 'statement',
      });
      const keyNone = buildCacheKey({
        word: 'hello',
        position: 'mid',
        punctuation: '',
        sentenceType: 'statement',
      });

      expect(keyComma).not.toBe(keyNone);
    });
  });
});
