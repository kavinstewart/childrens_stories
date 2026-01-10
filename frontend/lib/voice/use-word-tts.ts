/**
 * Hook for word-level TTS playback.
 *
 * STUB: Sentence-based extraction has been removed.
 * This will be reimplemented with isolated word synthesis and homograph disambiguation.
 * See bead story-lu4r for implementation plan.
 */

import { useCallback, useState } from 'react';
import { WordContext } from '@/components/TappableText';

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

  const playWord = useCallback(async (
    word: string,
    wordIndex: number,
    _context: WordContext
  ): Promise<void> => {
    console.log(`[WordTTS] playWord called: "${word}" index=${wordIndex} - NOT IMPLEMENTED`);
    setError('Word TTS not yet implemented');
  }, []);

  const stop = useCallback(async () => {
    console.log('[WordTTS] stop() called - NOT IMPLEMENTED');
    setLoadingWordIndex(-1);
  }, []);

  return {
    playWord,
    stop,
    isLoading: loadingWordIndex !== -1,
    loadingWordIndex,
    error,
  };
}
