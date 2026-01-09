/**
 * Hook for TTS with caching support.
 *
 * Wraps useTTS to add caching of audio and timestamps.
 * On cache hit, plays from cache without network request.
 */

import { useCallback, useRef, useState } from 'react';
import { ExpoPlayAudioStream } from '@mykin-ai/expo-audio-stream';
import { useTTS, UseTTSOptions, UseTTSResult, TTSStatus } from './use-tts';
import { TTSCache, TTSCacheEntry } from './tts-cache';
import { WordTimestamp } from './use-karaoke';
import { createWavFromPcm, base64ToUint8Array, uint8ArrayToBase64 } from './wav-utils';

// Audio format constants for Cartesia TTS
const TTS_SAMPLE_RATE = 24000;
const TTS_BIT_DEPTH = 16;
const TTS_NUM_CHANNELS = 1;

export interface UseCachedTTSOptions extends Omit<UseTTSOptions, 'onAudioChunk' | 'onTimestamps' | 'onAudioStart'> {
  /** Called when audio starts playing (from cache or live) */
  onAudioStart?: (contextId: string) => void;
  /** Called when timestamps are available (from cache or live) */
  onTimestamps?: (words: WordTimestamp[], contextId: string) => void;
  /** Called when playback completes (from cache or live) */
  onDone?: (contextId: string) => void;
  /** Enable caching (default: true) */
  enableCache?: boolean;
}

export interface UseCachedTTSResult extends Omit<UseTTSResult, 'speak'> {
  /** Speak text (uses cache if available) */
  speak: (text: string, contextId?: string) => Promise<void>;
  /** Whether currently playing from cache */
  isPlayingFromCache: boolean;
  /** Clear the TTS cache */
  clearCache: () => Promise<void>;
}

export function useCachedTTS(options: UseCachedTTSOptions = {}): UseCachedTTSResult {
  const {
    onAudioStart,
    onTimestamps,
    onDone,
    onError,
    enableCache = true,
    ...ttsOptions
  } = options;

  const [isPlayingFromCache, setIsPlayingFromCache] = useState(false);

  // Refs for collecting audio during live TTS
  const audioChunksRef = useRef<string[]>([]);
  const timestampsRef = useRef<WordTimestamp[]>([]);
  const currentTextRef = useRef<string>('');
  const currentContextRef = useRef<string>('');
  const playbackStartRef = useRef<number>(0);
  // Track if playback was cancelled to prevent race condition
  const playbackCancelledRef = useRef(false);

  // Handle live audio chunk - collect for caching
  const handleAudioChunk = useCallback((data: string, contextId: string) => {
    if (enableCache) {
      audioChunksRef.current.push(data);
    }
  }, [enableCache]);

  // Handle live timestamps - collect and forward
  const handleTimestamps = useCallback((words: Array<{ word: string; start: number; end: number }>, contextId: string) => {
    const typedWords = words as WordTimestamp[];
    if (enableCache) {
      timestampsRef.current = typedWords;
    }
    onTimestamps?.(typedWords, contextId);
  }, [enableCache, onTimestamps]);

  // Handle live TTS completion - cache and forward
  const handleDone = useCallback(async (contextId: string) => {
    // Cache the audio if we have chunks
    if (enableCache && audioChunksRef.current.length > 0 && currentTextRef.current) {
      const durationMs = Date.now() - playbackStartRef.current;

      try {
        // Pass chunks array directly - TTSCache handles binary concatenation
        await TTSCache.set(
          currentTextRef.current,
          audioChunksRef.current,
          timestampsRef.current,
          durationMs
        );
      } catch (err) {
        console.warn('[CachedTTS] Failed to cache audio:', err);
      }
    }

    // Reset collection refs
    audioChunksRef.current = [];
    timestampsRef.current = [];
    currentTextRef.current = '';

    onDone?.(contextId);
  }, [enableCache, onDone]);

  // Wrap useTTS with our handlers
  const tts = useTTS({
    ...ttsOptions,
    onAudioStart,
    onAudioChunk: handleAudioChunk,
    onTimestamps: handleTimestamps,
    onDone: handleDone,
    onError,
  });

  // Play from cache using playWav (direct playback without streaming queue)
  const playFromCache = useCallback(async (entry: TTSCacheEntry, contextId: string) => {
    setIsPlayingFromCache(true);
    playbackCancelledRef.current = false;

    try {
      // Send timestamps immediately
      if (entry.timestamps.length > 0) {
        onTimestamps?.(entry.timestamps, contextId);
      }

      // Read cached PCM audio (returned as base64)
      const pcmBase64 = await TTSCache.readAudio(entry);

      // Check if cancelled while reading
      if (playbackCancelledRef.current) {
        return;
      }

      // Convert PCM to WAV format for playWav()
      // playWav() plays directly without the streaming queue, avoiding race conditions
      const pcmData = base64ToUint8Array(pcmBase64);
      const wavData = createWavFromPcm(pcmData, TTS_SAMPLE_RATE, TTS_BIT_DEPTH, TTS_NUM_CHANNELS);
      const wavBase64 = uint8ArrayToBase64(wavData);

      // Fire onAudioStart right before playing
      onAudioStart?.(contextId);

      // Play using playWav (direct playback, bypasses streaming queue)
      await ExpoPlayAudioStream.playWav(wavBase64);

      // Wait for approximate duration then signal done
      // Note: playWav doesn't have a completion callback,
      // so we estimate based on cached duration
      await new Promise(resolve => setTimeout(resolve, entry.durationMs + 100));

      // Only signal done if not cancelled during playback
      if (!playbackCancelledRef.current) {
        onDone?.(contextId);
      }
    } catch (err) {
      console.error('[CachedTTS] Playback error:', err);
      if (!playbackCancelledRef.current) {
        onError?.('Failed to play cached audio');
      }
    } finally {
      setIsPlayingFromCache(false);
    }
  }, [onAudioStart, onTimestamps, onDone, onError]);

  // Enhanced speak with cache lookup
  const speak = useCallback(async (text: string, contextId?: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const ctx = contextId || `tts-${Date.now()}`;

    // Stop any previous playback before starting new
    // This prevents "Failed to enqueue audio chunk" errors
    try {
      playbackCancelledRef.current = true;
      await tts.stopPlayback();
      // Give native audio player time to fully reset
      await new Promise(resolve => setTimeout(resolve, 50));
      playbackCancelledRef.current = false;
    } catch (err) {
      console.warn('[CachedTTS] Error stopping previous playback:', err);
    }

    // Check cache first
    if (enableCache) {
      try {
        const cached = await TTSCache.get(trimmed);
        if (cached) {
          console.log('[CachedTTS] Cache hit, playing from cache');
          await playFromCache(cached, ctx);
          return;
        }
      } catch (err) {
        console.warn('[CachedTTS] Cache lookup failed:', err);
      }
    }

    // Cache miss - do live TTS
    console.log('[CachedTTS] Cache miss, using live TTS');
    currentTextRef.current = trimmed;
    currentContextRef.current = ctx;
    audioChunksRef.current = [];
    timestampsRef.current = [];
    playbackStartRef.current = Date.now();

    await tts.speak(trimmed, ctx);
  }, [enableCache, playFromCache, tts]);

  // Clear cache utility
  const clearCache = useCallback(async () => {
    await TTSCache.clearAll();
  }, []);

  // Wrap stopPlayback to handle cancellation
  const stopPlayback = useCallback(async () => {
    playbackCancelledRef.current = true;
    setIsPlayingFromCache(false);
    await tts.stopPlayback();
  }, [tts]);

  return {
    ...tts,
    speak,
    stopPlayback,
    isPlayingFromCache,
    clearCache,
  };
}
