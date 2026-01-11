/**
 * Tests for useWordTTS hook with isolated word synthesis
 */

import { renderHook, act, waitFor } from '@testing-library/react-native';
import { WordContext } from '../../../components/TappableText';

// Mock implementations
const mockSpeak = jest.fn<Promise<void>, [string, string]>(() => Promise.resolve());
const mockStopPlayback = jest.fn<Promise<void>, []>(() => Promise.resolve());

// Must mock before importing the hook
jest.mock('../../../lib/voice/use-tts', () => ({
  useTTS: () => ({
    speak: mockSpeak,
    stopPlayback: mockStopPlayback,
    disconnect: jest.fn(),
    status: 'idle',
    error: null,
  }),
}));

jest.mock('@mykin-ai/expo-audio-stream', () => ({
  ExpoPlayAudioStream: {
    playSound: jest.fn(),
    stopSound: jest.fn(),
    setSoundConfig: jest.fn(),
  },
  EncodingTypes: {
    PCM_S16LE: 'pcm_s16le',
  },
}));

const mockCacheGet = jest.fn(() => Promise.resolve(null));
const mockCacheSet = jest.fn(() => Promise.resolve());
const mockCacheGetAudioData = jest.fn(() => Promise.resolve(null));

jest.mock('../../../lib/voice/word-tts-cache', () => ({
  WordTTSCache: {
    get: (...args: unknown[]) => mockCacheGet(...args),
    set: (...args: unknown[]) => mockCacheSet(...args),
    getAudioData: (...args: unknown[]) => mockCacheGetAudioData(...args),
  },
  buildCacheKey: jest.fn((key) => key.pronunciationIndex !== undefined ? `${key.word}|p${key.pronunciationIndex}` : key.word),
}));

jest.mock('../../../lib/voice/homographs', () => ({
  isHomograph: jest.fn((word: string) => {
    const homographs = ['read', 'lead', 'bow', 'wind'];
    return homographs.includes(word.toLowerCase());
  }),
  getHomographEntry: jest.fn((word: string) => {
    if (word.toLowerCase() === 'read') {
      return {
        pronunciations: ['ɹ|iː|d', 'ɹ|ɛ|d'],
        meanings: ['present tense', 'past tense'],
      };
    }
    return null;
  }),
  formatPhonemes: jest.fn((p: string) => `<<${p}>>`),
}));

const mockDisambiguateHomograph = jest.fn();
jest.mock('../../../lib/api', () => ({
  api: {
    disambiguateHomograph: (...args: unknown[]) => mockDisambiguateHomograph(...args),
  },
}));

// Import after mocks
import { useWordTTS } from '../../../lib/voice/use-word-tts';

describe('useWordTTS', () => {
  const createContext = (overrides: Partial<WordContext> = {}): WordContext => ({
    sentence: 'I read books every day.',
    sentenceWordIndex: 1,
    position: 'mid',
    punctuation: '',
    sentenceType: 'statement',
    ...overrides,
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockCacheGet.mockResolvedValue(null);
    mockCacheSet.mockResolvedValue(undefined);
    mockCacheGetAudioData.mockResolvedValue(null);
  });

  describe('initial state', () => {
    it('starts with no loading state', () => {
      const { result } = renderHook(() => useWordTTS());

      expect(result.current.isLoading).toBe(false);
      expect(result.current.loadingWordIndex).toBe(-1);
      expect(result.current.error).toBeNull();
    });

    it('exposes playWord and stop functions', () => {
      const { result } = renderHook(() => useWordTTS());

      expect(typeof result.current.playWord).toBe('function');
      expect(typeof result.current.stop).toBe('function');
    });
  });

  describe('playWord', () => {
    it('calls speak to synthesize the word', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        // Don't await the playWord - it won't resolve without onDone callback
        result.current.playWord('hello', 0, createContext());
        // Give it a tick to start
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockSpeak).toHaveBeenCalled();
    });

    it('sets loading state when called', async () => {
      const { result } = renderHook(() => useWordTTS());

      act(() => {
        result.current.playWord('hello', 0, createContext());
      });

      // Should be loading (we haven't resolved the promise)
      expect(result.current.loadingWordIndex).toBe(0);
    });
  });

  describe('stop', () => {
    it('calls stopPlayback', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.stop();
      });

      expect(mockStopPlayback).toHaveBeenCalled();
    });

    it('resets loading state', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        await result.current.stop();
      });

      expect(result.current.loadingWordIndex).toBe(-1);
    });
  });

  describe('emotion mapping', () => {
    it('synthesizes with speak for questions', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('what', 0, createContext({
          sentenceType: 'question',
        }));
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockSpeak).toHaveBeenCalled();
      // Check that the text includes emotion tag
      const callArg = mockSpeak.mock.calls[0]?.[0] as string;
      expect(callArg).toContain('curious');
    });

    it('synthesizes with speak for exclamations', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('wow', 0, createContext({
          sentenceType: 'exclamation',
        }));
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockSpeak).toHaveBeenCalled();
      const callArg = mockSpeak.mock.calls[0]?.[0] as string;
      expect(callArg).toContain('excited');
    });
  });

  describe('homograph handling', () => {
    beforeEach(() => {
      mockDisambiguateHomograph.mockReset();
      mockDisambiguateHomograph.mockResolvedValue({
        word: 'read',
        pronunciation_index: 0,
        phonemes: 'ɹ|iː|d',
        is_homograph: true,
      });
    });

    it('calls disambiguation API for homographs', async () => {
      const { result } = renderHook(() => useWordTTS());
      const context = createContext({ sentence: 'I read books every day.' });

      await act(async () => {
        result.current.playWord('read', 0, context);
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockDisambiguateHomograph).toHaveBeenCalledWith(
        'read',
        'I read books every day.',
        1
      );
    });

    it('uses phonemes from disambiguation response', async () => {
      mockDisambiguateHomograph.mockResolvedValue({
        word: 'read',
        pronunciation_index: 1,
        phonemes: 'ɹ|ɛ|d',
        is_homograph: true,
      });

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('read', 0, createContext());
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockSpeak).toHaveBeenCalled();
      const callArg = mockSpeak.mock.calls[0]?.[0] as string;
      // Should contain the phoneme markup with disambiguated phonemes
      expect(callArg).toContain('<<ɹ|ɛ|d>>');
    });

    it('falls back to first pronunciation if disambiguation fails', async () => {
      mockDisambiguateHomograph.mockRejectedValue(new Error('API error'));

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('read', 0, createContext());
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockSpeak).toHaveBeenCalled();
      const callArg = mockSpeak.mock.calls[0]?.[0] as string;
      // Should fall back to first pronunciation
      expect(callArg).toContain('<<ɹ|iː|d>>');
    });

    it('does not call disambiguation for non-homographs', async () => {
      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('hello', 0, createContext());
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      expect(mockDisambiguateHomograph).not.toHaveBeenCalled();
    });

    it('includes pronunciationIndex in cache key for homographs', async () => {
      mockDisambiguateHomograph.mockResolvedValue({
        word: 'read',
        pronunciation_index: 1,
        phonemes: 'ɹ|ɛ|d',
        is_homograph: true,
      });

      const { result } = renderHook(() => useWordTTS());

      await act(async () => {
        result.current.playWord('read', 0, createContext());
        await new Promise(resolve => setTimeout(resolve, 10));
      });

      // Verify cache.get was called with simplified key (word + pronunciationIndex only)
      expect(mockCacheGet).toHaveBeenCalledWith({
        word: 'read',
        pronunciationIndex: 1,
      });
    });
  });

});
