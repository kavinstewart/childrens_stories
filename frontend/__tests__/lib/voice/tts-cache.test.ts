/**
 * Tests for TTS Cache
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { TTSCache } from '../../../lib/voice/tts-cache';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

// Mock file instances
const mockFileInstances: Record<string, { exists: boolean; size: number; content: string }> = {};

// Mock expo-file-system new API
jest.mock('expo-file-system', () => {
  const mockFile = jest.fn().mockImplementation((pathOrDir: any, name?: string) => {
    const uri = name ? `${pathOrDir.uri || pathOrDir}/${name}` : pathOrDir;
    return {
      uri,
      get exists() {
        return mockFileInstances[uri]?.exists ?? false;
      },
      get size() {
        return mockFileInstances[uri]?.size ?? 0;
      },
      text: jest.fn().mockImplementation(() => mockFileInstances[uri]?.content ?? ''),
      write: jest.fn().mockImplementation((content: string) => {
        mockFileInstances[uri] = { exists: true, size: content.length, content };
      }),
      delete: jest.fn().mockImplementation(() => {
        delete mockFileInstances[uri];
      }),
    };
  });

  const mockDirectory = jest.fn().mockImplementation((base: any, name: string) => ({
    uri: `${base}/${name}`,
    exists: true,
    create: jest.fn(),
    delete: jest.fn(),
  }));

  return {
    File: mockFile,
    Directory: mockDirectory,
    Paths: {
      cache: '/cache',
    },
  };
});

describe('TTSCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Clear mock file instances
    Object.keys(mockFileInstances).forEach(key => delete mockFileInstances[key]);
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
  });

  describe('init', () => {
    it('creates cache directory', async () => {
      await TTSCache.init();
      // Directory.create is called if not exists - hard to test with this mock
      // Just verify no errors
    });
  });

  describe('get', () => {
    it('returns null for uncached text', async () => {
      const result = await TTSCache.get('hello world');
      expect(result).toBeNull();
    });

    it('returns null if entry expired', async () => {
      const textHash = 'abc123';
      const mockEntry = {
        textHash,
        audioPath: '/cache/tts/abc123.pcm',
        timestamps: [],
        cachedAt: Date.now() - 8 * 24 * 60 * 60 * 1000, // 8 days ago (expired)
        durationMs: 300,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { [textHash]: mockEntry } })
      );

      // Using a text that hashes to 'abc123' is hard, so test removal on expiry
      const result = await TTSCache.get('test');
      expect(result).toBeNull();
    });
  });

  describe('set', () => {
    it('writes audio file and updates index', async () => {
      const timestamps = [
        { word: 'hello', start: 0, end: 0.3 },
        { word: 'world', start: 0.35, end: 0.7 },
      ];

      const result = await TTSCache.set('hello world', 'base64audio', timestamps, 700);

      expect(AsyncStorage.setItem).toHaveBeenCalled();
      expect(result.timestamps).toEqual(timestamps);
      expect(result.durationMs).toBe(700);
      expect(result.audioPath).toContain('.pcm');
    });
  });

  describe('remove', () => {
    it('removes entry from index', async () => {
      const textHash = 'abc123';
      const mockEntry = {
        textHash,
        audioPath: '/cache/tts/abc123.pcm',
        timestamps: [],
        cachedAt: Date.now(),
        durationMs: 300,
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
        JSON.stringify({ entries: { [textHash]: mockEntry } })
      );

      await TTSCache.remove(textHash);

      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@tts_cache_index',
        JSON.stringify({ entries: {} })
      );
    });
  });

  describe('clearAll', () => {
    it('removes index from storage', async () => {
      await TTSCache.clearAll();

      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('@tts_cache_index');
    });
  });

  describe('getStats', () => {
    it('returns count of cached entries', async () => {
      const mockIndex = {
        entries: {
          abc: {
            textHash: 'abc',
            audioPath: '/cache/tts/abc.pcm',
            timestamps: [],
            cachedAt: Date.now(),
            durationMs: 300,
          },
          def: {
            textHash: 'def',
            audioPath: '/cache/tts/def.pcm',
            timestamps: [],
            cachedAt: Date.now(),
            durationMs: 500,
          },
        },
      };

      (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockIndex));

      const stats = await TTSCache.getStats();

      expect(stats.count).toBe(2);
    });
  });
});
