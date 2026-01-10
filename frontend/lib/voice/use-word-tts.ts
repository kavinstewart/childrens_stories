/**
 * Hook for word-level TTS playback with caching.
 *
 * Enables tap-to-speak functionality where users can tap individual words
 * to hear them spoken. Uses context-aware caching for natural prosody.
 *
 * Strategy:
 * 1. Check word cache using context key (word|position|punctuation|sentenceType)
 * 2. On cache hit: play cached audio directly
 * 3. On cache miss: synthesize full sentence, extract word audio, cache it
 */

import { useCallback, useRef, useState } from 'react';
import { ExpoPlayAudioStream, EncodingTypes } from '@mykin-ai/expo-audio-stream';
import { useTTS } from './use-tts';
import { WordTTSCache, buildCacheKey } from './word-tts-cache';
import { extractAudioSlice, uint8ArrayToBase64, base64ToUint8Array, createWavFromPcm } from './wav-utils';
import { WordContext } from '@/components/TappableText';

// Cartesia TTS format constants
const TTS_SAMPLE_RATE = 24000;
const TTS_BIT_DEPTH = 16;

interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

interface PendingSynthesis {
  contextId: string;
  wordIndex: number;
  targetWordIndex: number; // Index within sentence
  context: WordContext;
  audioChunks: Uint8Array[];
  timestamps: WordTimestamp[];
  resolve: () => void;
  reject: (error: Error) => void;
}

interface SentenceCache {
  sentence: string;
  audioData: Uint8Array;
  timestamps: WordTimestamp[];
  cachedAt: number;
}

export interface UseWordTTSResult {
  /** Play a word's TTS audio */
  playWord: (word: string, wordIndex: number, context: WordContext) => Promise<void>;
  /** Stop current playback */
  stop: () => Promise<void>;
  /** Whether synthesis is in progress */
  isLoading: boolean;
  /** Index of word currently loading (-1 if none) */
  loadingWordIndex: number;
  /** Last error message */
  error: string | null;
}

export function useWordTTS(): UseWordTTSResult {
  const [loadingWordIndex, setLoadingWordIndex] = useState<number>(-1);
  const [error, setError] = useState<string | null>(null);

  // Track pending synthesis requests
  const pendingSynthesisRef = useRef<PendingSynthesis | null>(null);

  // Keep recent sentence audio in memory for quick subsequent word taps
  const sentenceCacheRef = useRef<SentenceCache | null>(null);
  const SENTENCE_CACHE_TTL = 30000; // 30 seconds

  // Handle incoming audio chunks
  const handleAudioChunk = useCallback((data: string, contextId: string) => {
    const pending = pendingSynthesisRef.current;
    if (pending && pending.contextId === contextId) {
      const audioBytes = base64ToUint8Array(data);
      pending.audioChunks.push(audioBytes);
      console.log(`[WordTTS] Audio chunk received: ${audioBytes.length} bytes, total chunks: ${pending.audioChunks.length}`);
    }
  }, []);

  // Handle incoming timestamps
  const handleTimestamps = useCallback((words: WordTimestamp[], contextId: string) => {
    const pending = pendingSynthesisRef.current;
    if (pending && pending.contextId === contextId) {
      // Accumulate timestamps
      pending.timestamps.push(...words);
      console.log(`[WordTTS] Timestamps received: ${words.length} words, total: ${pending.timestamps.length}, target index: ${pending.targetWordIndex}`);
    }
  }, []);

  // Handle synthesis completion
  const handleDone = useCallback((contextId: string) => {
    const pending = pendingSynthesisRef.current;
    if (!pending || pending.contextId !== contextId) return;

    try {
      // Combine all audio chunks
      const totalLength = pending.audioChunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const fullAudio = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of pending.audioChunks) {
        fullAudio.set(chunk, offset);
        offset += chunk.length;
      }

      // Cache sentence audio in memory
      sentenceCacheRef.current = {
        sentence: pending.context.sentence,
        audioData: fullAudio,
        timestamps: pending.timestamps,
        cachedAt: Date.now(),
      };

      // Extract and play the target word's audio
      const targetTimestamp = pending.timestamps[pending.targetWordIndex];
      if (targetTimestamp) {
        const wordAudio = extractAudioSlice(
          fullAudio,
          targetTimestamp.start,
          targetTimestamp.end,
          TTS_SAMPLE_RATE,
          TTS_BIT_DEPTH
        );

        if (wordAudio.length > 0) {
          // Play the extracted audio
          const wavAudio = createWavFromPcm(wordAudio, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, 1);
          const base64Audio = uint8ArrayToBase64(wavAudio);
          ExpoPlayAudioStream.playSound(base64Audio, `word-play-${pending.wordIndex}`, EncodingTypes.PCM_S16LE);

          // Calculate duration from timestamps
          const durationMs = (targetTimestamp.end - targetTimestamp.start) * 1000;

          // Cache the word audio for future use
          WordTTSCache.set(
            {
              word: pending.context.sentence.split(/\s+/)[pending.targetWordIndex] || '',
              position: pending.context.position,
              punctuation: pending.context.punctuation,
              sentenceType: pending.context.sentenceType,
            },
            wordAudio,
            durationMs
          );
        }
      }

      pending.resolve();
    } catch (err) {
      pending.reject(err instanceof Error ? err : new Error(String(err)));
    } finally {
      pendingSynthesisRef.current = null;
      setLoadingWordIndex(-1);
    }
  }, []);

  // Initialize useTTS with callbacks
  // suppressPlayback=true: we collect audio chunks without auto-playing, then play only the extracted word
  const { speak, stopPlayback, disconnect } = useTTS({
    suppressPlayback: true,
    onAudioChunk: handleAudioChunk,
    onTimestamps: handleTimestamps,
    onDone: handleDone,
    onError: (errMsg) => {
      setError(errMsg);
      setLoadingWordIndex(-1);
      if (pendingSynthesisRef.current) {
        pendingSynthesisRef.current.reject(new Error(errMsg));
        pendingSynthesisRef.current = null;
      }
    },
  });

  // Stop playback and clean up
  const stop = useCallback(async () => {
    await stopPlayback();
    setLoadingWordIndex(-1);
    if (pendingSynthesisRef.current) {
      pendingSynthesisRef.current.reject(new Error('Playback stopped'));
      pendingSynthesisRef.current = null;
    }
  }, [stopPlayback]);

  // Play a word's audio
  const playWord = useCallback(async (
    word: string,
    wordIndex: number,
    context: WordContext
  ): Promise<void> => {
    // Cancel any pending synthesis
    if (pendingSynthesisRef.current) {
      await stopPlayback();
      pendingSynthesisRef.current.reject(new Error('Cancelled'));
      pendingSynthesisRef.current = null;
    }

    setLoadingWordIndex(wordIndex);
    setError(null);

    try {
      // Build cache key for this word in context
      const cacheKey = {
        word,
        position: context.position,
        punctuation: context.punctuation,
        sentenceType: context.sentenceType,
      };

      // Check word cache first
      const cachedEntry = await WordTTSCache.get(cacheKey);
      if (cachedEntry) {
        const audioData = await WordTTSCache.getAudioData(cachedEntry);
        if (audioData && audioData.length > 0) {
          // Play cached audio
          const wavAudio = createWavFromPcm(audioData, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, 1);
          const base64Audio = uint8ArrayToBase64(wavAudio);
          ExpoPlayAudioStream.playSound(base64Audio, `word-cached-${wordIndex}`, EncodingTypes.PCM_S16LE);
          setLoadingWordIndex(-1);
          return;
        }
      }

      // Check in-memory sentence cache
      const sentenceCache = sentenceCacheRef.current;
      if (
        sentenceCache &&
        sentenceCache.sentence === context.sentence &&
        Date.now() - sentenceCache.cachedAt < SENTENCE_CACHE_TTL
      ) {
        // Extract word from cached sentence audio
        const targetTimestamp = sentenceCache.timestamps[context.sentenceWordIndex];
        if (targetTimestamp) {
          const wordAudio = extractAudioSlice(
            sentenceCache.audioData,
            targetTimestamp.start,
            targetTimestamp.end,
            TTS_SAMPLE_RATE,
            TTS_BIT_DEPTH
          );

          if (wordAudio.length > 0) {
            const wavAudio = createWavFromPcm(wordAudio, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, 1);
            const base64Audio = uint8ArrayToBase64(wavAudio);
            ExpoPlayAudioStream.playSound(base64Audio, `word-memory-${wordIndex}`, EncodingTypes.PCM_S16LE);

            // Cache the word audio for future use
            const durationMs = (targetTimestamp.end - targetTimestamp.start) * 1000;
            await WordTTSCache.set(cacheKey, wordAudio, durationMs);

            setLoadingWordIndex(-1);
            return;
          }
        }
      }

      // Cache miss - need to synthesize sentence
      const contextId = `word-${wordIndex}`;

      return new Promise<void>((resolve, reject) => {
        pendingSynthesisRef.current = {
          contextId,
          wordIndex,
          targetWordIndex: context.sentenceWordIndex,
          context,
          audioChunks: [],
          timestamps: [],
          resolve: () => {
            setLoadingWordIndex(-1);
            resolve();
          },
          reject: (err) => {
            setError(err.message);
            setLoadingWordIndex(-1);
            reject(err);
          },
        };

        // Start synthesis of the full sentence
        speak(context.sentence, contextId).catch((err) => {
          setError(err.message);
          setLoadingWordIndex(-1);
          pendingSynthesisRef.current = null;
          reject(err);
        });
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      setError(errorMsg);
      setLoadingWordIndex(-1);
      throw err;
    }
  }, [speak, stopPlayback]);

  return {
    playWord,
    stop,
    isLoading: loadingWordIndex !== -1,
    loadingWordIndex,
    error,
  };
}
