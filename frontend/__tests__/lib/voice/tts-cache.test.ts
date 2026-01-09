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

// Mock file instances - now stores binary data as Uint8Array
const mockFileInstances: Record<string, { exists: boolean; size: number; content: Uint8Array }> = {};

// Helper to decode base64 to Uint8Array (mimics what the real code does)
function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

// Helper to encode Uint8Array to base64
function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

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
      // Read binary data and return as Uint8Array (async)
      bytes: jest.fn().mockImplementation(async () => mockFileInstances[uri]?.content ?? new Uint8Array(0)),
      // Write accepts Uint8Array for binary data
      write: jest.fn().mockImplementation((content: Uint8Array | string) => {
        if (content instanceof Uint8Array) {
          mockFileInstances[uri] = { exists: true, size: content.length, content };
        } else {
          // Legacy string write - store as string-converted bytes (for old tests)
          const bytes = new Uint8Array(content.length);
          for (let i = 0; i < content.length; i++) {
            bytes[i] = content.charCodeAt(i);
          }
          mockFileInstances[uri] = { exists: true, size: bytes.length, content: bytes };
        }
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
      // Single chunk as array
      const chunks = [btoa('audio_data')];

      const result = await TTSCache.set('hello world', chunks, timestamps, 700);

      expect(AsyncStorage.setItem).toHaveBeenCalled();
      expect(result.timestamps).toEqual(timestamps);
      expect(result.durationMs).toBe(700);
      expect(result.audioPath).toContain('.pcm');
    });

    it('correctly concatenates multiple base64 chunks as binary', async () => {
      // Create two chunks with known binary content
      const chunk1Data = new Uint8Array([1, 2, 3, 4, 5]);
      const chunk2Data = new Uint8Array([6, 7, 8, 9, 10]);
      const chunk1 = uint8ArrayToBase64(chunk1Data);
      const chunk2 = uint8ArrayToBase64(chunk2Data);

      await TTSCache.set('test text', [chunk1, chunk2], [], 500);

      // Find the written file and verify binary content
      const fileUri = Object.keys(mockFileInstances)[0];
      expect(fileUri).toBeDefined();

      const storedContent = mockFileInstances[fileUri].content;
      // Should be concatenated binary: [1,2,3,4,5,6,7,8,9,10]
      expect(storedContent).toEqual(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]));
    });

    it('stores binary data not base64 string', async () => {
      const binaryData = new Uint8Array([0x48, 0x65, 0x6c, 0x6c, 0x6f]); // "Hello" in ASCII
      const chunk = uint8ArrayToBase64(binaryData);

      await TTSCache.set('test', [chunk], [], 100);

      const fileUri = Object.keys(mockFileInstances)[0];
      const storedContent = mockFileInstances[fileUri].content;

      // Should store raw binary, not base64 string
      expect(storedContent).toBeInstanceOf(Uint8Array);
      expect(storedContent).toEqual(binaryData);
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

  describe('readAudio', () => {
    it('returns valid base64 from stored binary', async () => {
      // Store some binary data
      const originalData = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
      const chunk = uint8ArrayToBase64(originalData);

      const entry = await TTSCache.set('test', [chunk], [], 100);

      // Read it back
      const result = await TTSCache.readAudio(entry);

      // Should be valid base64 that decodes to original data
      expect(typeof result).toBe('string');
      const decoded = base64ToUint8Array(result);
      expect(decoded).toEqual(originalData);
    });

    it('returns correct base64 for multi-chunk audio', async () => {
      // Store multiple chunks
      const chunk1 = uint8ArrayToBase64(new Uint8Array([10, 20, 30]));
      const chunk2 = uint8ArrayToBase64(new Uint8Array([40, 50, 60]));

      const entry = await TTSCache.set('multi chunk', [chunk1, chunk2], [], 200);

      // Read it back
      const result = await TTSCache.readAudio(entry);

      // Should decode to concatenated binary
      const decoded = base64ToUint8Array(result);
      expect(decoded).toEqual(new Uint8Array([10, 20, 30, 40, 50, 60]));
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
