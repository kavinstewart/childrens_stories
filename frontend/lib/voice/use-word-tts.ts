/**
 * Hook for word-level TTS playback with isolated word synthesis.
 *
 * Enables tap-to-speak functionality where users can tap individual words
 * to hear them spoken. Uses isolated word synthesis for better quality.
 *
 * Features:
 * - Isolated word synthesis (not extracted from sentences)
 * - Homograph disambiguation using LLM
 * - Emotion mapping based on sentence type
 * - Word-level caching
 */

import { useCallback, useRef, useState } from 'react';
import { ExpoPlayAudioStream, EncodingTypes } from '@mykin-ai/expo-audio-stream';
import { useTTS } from './use-tts';
import { WordTTSCache, buildCacheKey } from './word-tts-cache';
import { createWavFromPcm, uint8ArrayToBase64, base64ToUint8Array } from './wav-utils';
import { isHomograph, getHomographEntry, formatPhonemes } from './homographs';
import { WordContext } from '@/components/TappableText';

// Cartesia TTS format constants
const TTS_SAMPLE_RATE = 24000;
const TTS_BIT_DEPTH = 16;

/** Map sentence type to Cartesia emotion tag */
type Emotion = 'neutral' | 'curious' | 'excited';

function getEmotionForSentenceType(sentenceType: WordContext['sentenceType']): Emotion {
  switch (sentenceType) {
    case 'question':
      return 'curious';
    case 'exclamation':
      return 'excited';
    default:
      return 'neutral';
  }
}

/** Build text to synthesize, with optional phoneme hint */
function buildSynthesisText(word: string, phonemes: string | null, emotion: Emotion): string {
  let text = word;

  // Apply phoneme hint for homographs
  if (phonemes) {
    text = formatPhonemes(phonemes);
  }

  // Wrap with emotion tag if not neutral
  if (emotion !== 'neutral') {
    text = `<emotion name="${emotion}">${text}</emotion>`;
  }

  return text;
}

interface PendingSynthesis {
  contextId: string;
  wordIndex: number;
  audioChunks: Uint8Array[];
  resolve: () => void;
  reject: (error: Error) => void;
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

  // Track pending synthesis
  const pendingSynthesisRef = useRef<PendingSynthesis | null>(null);
  // Track if we've played audio (to avoid stopSound before init)
  const hasPlayedAudioRef = useRef(false);

  // Handle incoming audio chunks
  const handleAudioChunk = useCallback((data: string, contextId: string) => {
    const pending = pendingSynthesisRef.current;
    if (pending && pending.contextId === contextId) {
      const audioBytes = base64ToUint8Array(data);
      pending.audioChunks.push(audioBytes);
    }
  }, []);

  // Handle synthesis completion
  const handleDone = useCallback((contextId: string) => {
    const pending = pendingSynthesisRef.current;
    if (!pending || pending.contextId !== contextId) {
      return;
    }

    try {
      // Combine all audio chunks
      const totalLength = pending.audioChunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const fullAudio = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of pending.audioChunks) {
        fullAudio.set(chunk, offset);
        offset += chunk.length;
      }

      if (fullAudio.length > 0) {
        // Create WAV and play
        const wavAudio = createWavFromPcm(fullAudio, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, 1);
        const base64Audio = uint8ArrayToBase64(wavAudio);
        ExpoPlayAudioStream.playSound(base64Audio, `word-${pending.wordIndex}`, EncodingTypes.PCM_S16LE);
        hasPlayedAudioRef.current = true;
      }

      pending.resolve();
    } catch (err) {
      pending.reject(err instanceof Error ? err : new Error(String(err)));
    } finally {
      pendingSynthesisRef.current = null;
      setLoadingWordIndex(-1);
    }
  }, []);

  // Initialize TTS with callbacks (suppress auto-playback, we handle it)
  const { speak, stopPlayback } = useTTS({
    suppressPlayback: true,
    onAudioChunk: handleAudioChunk,
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

  // Stop playback
  const stop = useCallback(async () => {
    await stopPlayback();
    setLoadingWordIndex(-1);
    if (pendingSynthesisRef.current) {
      pendingSynthesisRef.current.reject(new Error('Playback stopped'));
      pendingSynthesisRef.current = null;
    }
  }, [stopPlayback]);

  // Play a word
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
      const emotion = getEmotionForSentenceType(context.sentenceType);

      // Check cache first
      const cacheKey = {
        word: word.toLowerCase(),
        position: context.position,
        punctuation: context.punctuation,
        sentenceType: context.sentenceType,
      };

      const cachedEntry = await WordTTSCache.get(cacheKey);
      if (cachedEntry) {
        const audioData = await WordTTSCache.getAudioData(cachedEntry);
        if (audioData && audioData.length > 0) {
          // Play cached audio
          const wavAudio = createWavFromPcm(audioData, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, 1);
          const base64Audio = uint8ArrayToBase64(wavAudio);
          ExpoPlayAudioStream.playSound(base64Audio, `word-cached-${wordIndex}`, EncodingTypes.PCM_S16LE);
          hasPlayedAudioRef.current = true;
          setLoadingWordIndex(-1);
          return;
        }
      }

      // Determine phonemes for homographs
      let phonemes: string | null = null;
      if (isHomograph(word)) {
        const entry = getHomographEntry(word);
        if (entry) {
          // For now, use first pronunciation (index 0)
          // TODO: Implement LLM disambiguation
          phonemes = entry.pronunciations[0];
        }
      }

      // Build synthesis text
      const synthesisText = buildSynthesisText(word, phonemes, emotion);
      const contextId = `word-${wordIndex}-${Date.now()}`;

      return new Promise<void>((resolve, reject) => {
        pendingSynthesisRef.current = {
          contextId,
          wordIndex,
          audioChunks: [],
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

        // Synthesize the word
        speak(synthesisText, contextId).catch((err) => {
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
