/**
 * Tests for useWordTTS hook
 *
 * Note: Some async tests are challenging due to the complex interaction between
 * useTTS callbacks and React hook state. Core functionality is tested, with
 * integration tests covering full async flows.
 */

import { renderHook, act } from '@testing-library/react-native';
import { useWordTTS } from '../../../lib/voice/use-word-tts';
import { WordContext } from '../../../components/TappableText';

// Mock expo-audio-stream before anything else
const mockPlaySound = jest.fn();
const mockStopSound = jest.fn();
const mockSetSoundConfig = jest.fn();

jest.mock('@mykin-ai/expo-audio-stream', () => ({
  ExpoPlayAudioStream: {
    playSound: (...args: any[]) => mockPlaySound(...args),
    stopSound: (...args: any[]) => mockStopSound(...args),
    setSoundConfig: (...args: any[]) => mockSetSoundConfig(...args),
  },
  EncodingTypes: {
    PCM_S16LE: 'pcm_s16le',
  },
}));

jest.mock('@mykin-ai/expo-audio-stream/build/events', () => ({
  subscribeToEvent: jest.fn(() => ({ remove: jest.fn() })),
}));

// Mock word cache
const mockCacheGet = jest.fn();
const mockCacheSet = jest.fn();
const mockCacheGetAudioData = jest.fn();

jest.mock('../../../lib/voice/word-tts-cache', () => ({
  WordTTSCache: {
    get: (...args: any[]) => mockCacheGet(...args),
    set: (...args: any[]) => mockCacheSet(...args),
    getAudioData: (...args: any[]) => mockCacheGetAudioData(...args),
    clearAll: jest.fn(),
  },
  buildCacheKey: jest.fn((key: any) => `${key.word}|${key.position}|${key.punctuation}|${key.sentenceType}`),
}));

jest.mock('../../../lib/voice/wav-utils', () => ({
  extractAudioSlice: jest.fn(() => new Uint8Array([1, 2, 3, 4])),
  uint8ArrayToBase64: jest.fn(() => 'base64data'),
  base64ToUint8Array: jest.fn(() => new Uint8Array([1, 2, 3, 4])),
  createWavFromPcm: jest.fn(() => new Uint8Array([1, 2, 3, 4])),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

// Mock useTTS
const mockSpeak = jest.fn();
const mockStopPlayback = jest.fn();

type TTSCallback = {
  onTimestamps?: (words: Array<{ word: string; start: number; end: number }>, contextId: string) => void;
  onAudioChunk?: (data: string, contextId: string) => void;
  onDone?: (contextId: string) => void;
  onError?: (error: string) => void;
};

let ttsCallbacks: TTSCallback = {};

jest.mock('../../../lib/voice/use-tts', () => ({
  useTTS: jest.fn((options: TTSCallback) => {
    ttsCallbacks = options || {};
    return {
      status: 'ready',
      speak: mockSpeak,
      stopPlayback: mockStopPlayback,
      connect: jest.fn(),
      disconnect: jest.fn(),
      isSpeaking: false,
      error: null,
    };
  }),
}));

jest.mock('../../../lib/auth-storage', () => ({
  authStorage: {
    getToken: jest.fn().mockResolvedValue('test-token'),
  },
}));

describe('useWordTTS', () => {
  const mockContext: WordContext = {
    position: 'start',
    punctuation: '',
    sentenceType: 'statement',
    sentence: 'Hello world today.',
    sentenceWordIndex: 0,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    ttsCallbacks = {};
    mockCacheGet.mockResolvedValue(null);
    mockCacheSet.mockResolvedValue({});
    mockCacheGetAudioData.mockResolvedValue(null);
    mockSpeak.mockResolvedValue(undefined);
    mockStopPlayback.mockResolvedValue(undefined);
  });

  describe('initialization', () => {
    it('returns initial state correctly', () => {
      const { result } = renderHook(() => useWordTTS());

      expect(result.current.isLoading).toBe(false);
      expect(result.current.loadingWordIndex).toBe(-1);
      expect(result.current.error).toBeNull();
    });

    it('exposes playWord function', () => {
      const { result } = renderHook(() => useWordTTS());

      expect(typeof result.current.playWord).toBe('function');
    });

    it('exposes stop function', () => {
      const { result } = renderHook(() => useWordTTS());

      expect(typeof result.current.stop).toBe('function');
    });
  });

  describe('playWord - cache hit', () => {
    it('plays cached audio without synthesis', async () => {
      const cachedEntry = {
        cacheKey: 'hello|start||statement',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now(),
        durationMs: 250,
      };
      mockCacheGet.mockResolvedValue(cachedEntry);
      mockCacheGetAudioData.mockResolvedValue(new Uint8Array([1, 2, 3, 4]));

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      expect(mockCacheGet).toHaveBeenCalled();
      expect(mockCacheGetAudioData).toHaveBeenCalledWith(cachedEntry);
      expect(mockSpeak).not.toHaveBeenCalled();
      expect(mockPlaySound).toHaveBeenCalled();
    });

    it('does not show loading state for cache hits', async () => {
      const cachedEntry = {
        cacheKey: 'hello|start||statement',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now(),
        durationMs: 250,
      };
      mockCacheGet.mockResolvedValue(cachedEntry);
      mockCacheGetAudioData.mockResolvedValue(new Uint8Array([1, 2, 3, 4]));

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      // After cache hit playback, loading should be cleared
      expect(result.current.isLoading).toBe(false);
      expect(result.current.loadingWordIndex).toBe(-1);
    });
  });

  describe('playWord - cache miss', () => {
    it('synthesizes sentence when word not cached', async () => {
      mockCacheGet.mockResolvedValue(null);

      // Simulate immediate TTS callbacks in speak
      mockSpeak.mockImplementation(async (text: string, contextId: string) => {
        // Fire callbacks synchronously to complete synthesis
        ttsCallbacks.onTimestamps?.([
          { word: 'Hello', start: 0, end: 0.3 },
          { word: 'world', start: 0.35, end: 0.6 },
          { word: 'today.', start: 0.65, end: 1.0 },
        ], contextId);
        ttsCallbacks.onAudioChunk?.('base64audiodata', contextId);
        ttsCallbacks.onDone?.(contextId);
      });

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      expect(mockSpeak).toHaveBeenCalledWith(mockContext.sentence, 'word-0');
    });

    it('caches extracted word audio after synthesis', async () => {
      mockCacheGet.mockResolvedValue(null);

      mockSpeak.mockImplementation(async (text: string, contextId: string) => {
        ttsCallbacks.onTimestamps?.([
          { word: 'Hello', start: 0, end: 0.3 },
          { word: 'world', start: 0.35, end: 0.6 },
        ], contextId);
        ttsCallbacks.onAudioChunk?.('base64audiodata', contextId);
        ttsCallbacks.onDone?.(contextId);
      });

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      expect(mockCacheSet).toHaveBeenCalled();
    });

    it('plays extracted audio after synthesis', async () => {
      mockCacheGet.mockResolvedValue(null);

      mockSpeak.mockImplementation(async (text: string, contextId: string) => {
        ttsCallbacks.onTimestamps?.([
          { word: 'Hello', start: 0, end: 0.3 },
        ], contextId);
        ttsCallbacks.onAudioChunk?.('base64audiodata', contextId);
        ttsCallbacks.onDone?.(contextId);
      });

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      // Audio should be played after extraction
      expect(mockPlaySound).toHaveBeenCalled();
    });

    it('sets loading state during synthesis', async () => {
      mockCacheGet.mockResolvedValue(null);

      const { result } = renderHook(() => useWordTTS());

      // Start playWord - loading should be set immediately
      act(() => {
        result.current.playWord('Hello', 0, mockContext);
      });

      // Should be loading since synthesis hasn't completed
      expect(result.current.loadingWordIndex).toBe(0);
      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('stop', () => {
    it('calls stopPlayback on underlying TTS', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.stop();
      });

      expect(mockStopPlayback).toHaveBeenCalled();
    });

    it('clears loading state after stop', async () => {
      mockCacheGet.mockResolvedValue(null);
      const { result } = renderHook(() => useWordTTS());

      // Start playWord but don't await it
      let playPromise: Promise<void> | undefined;
      act(() => {
        playPromise = result.current.playWord('Hello', 0, mockContext);
      });

      expect(result.current.isLoading).toBe(true);

      // Stop - should clear loading (and reject the pending promise)
      await act(async () => {
        await result.current.stop();
        // Catch the expected rejection from playWord
        try {
          await playPromise;
        } catch {
          // Expected - playWord was cancelled
        }
      });

      expect(result.current.loadingWordIndex).toBe(-1);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('error handling', () => {
    it('sets error state on synthesis failure', async () => {
      mockCacheGet.mockResolvedValue(null);
      mockSpeak.mockRejectedValue(new Error('Synthesis failed'));

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        try {
          await result.current.playWord('Hello', 0, mockContext);
        } catch {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe('Synthesis failed');
      expect(result.current.isLoading).toBe(false);
    });

    it('clears error on successful playback', async () => {
      // First: create an error state
      mockCacheGet.mockResolvedValue(null);
      mockSpeak.mockRejectedValueOnce(new Error('First error'));

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        try {
          await result.current.playWord('Hello', 0, mockContext);
        } catch {
          // Expected
        }
      });

      expect(result.current.error).toBe('First error');

      // Now: successful playback from cache
      const cachedEntry = {
        cacheKey: 'hello|start||statement',
        audioPath: 'file://cache/tts-words/hello.pcm',
        cachedAt: Date.now(),
        durationMs: 250,
      };
      mockCacheGet.mockResolvedValue(cachedEntry);
      mockCacheGetAudioData.mockResolvedValue(new Uint8Array([1, 2, 3, 4]));

      await act(async () => {
        await result.current.playWord('Hello', 0, mockContext);
      });

      expect(result.current.error).toBeNull();
    });
  });
});
