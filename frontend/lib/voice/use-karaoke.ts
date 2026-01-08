/**
 * Hook for karaoke-style word highlighting during TTS playback.
 *
 * Tracks word timestamps from TTS and provides the current word index
 * based on elapsed playback time.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface UseKaraokeOptions {
  /** Update interval in ms (default: 50ms for smooth highlighting) */
  updateIntervalMs?: number;
}

export interface UseKaraokeResult {
  /** Current word index being spoken (-1 if not playing) */
  currentWordIndex: number;
  /** All word timestamps for current utterance */
  timestamps: WordTimestamp[];
  /** Start tracking with new timestamps (resets timer) */
  startTracking: (timestamps: WordTimestamp[]) => void;
  /** Add more timestamps to current tracking (for streaming) */
  addTimestamps: (timestamps: WordTimestamp[]) => void;
  /** Stop tracking and reset */
  stopTracking: () => void;
  /** Whether currently tracking */
  isTracking: boolean;
}

export function useKaraoke(options: UseKaraokeOptions = {}): UseKaraokeResult {
  const { updateIntervalMs = 50 } = options;

  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const [timestamps, setTimestamps] = useState<WordTimestamp[]>([]);
  const [isTracking, setIsTracking] = useState(false);

  const startTimeRef = useRef<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timestampsRef = useRef<WordTimestamp[]>([]);

  // Keep ref in sync for interval callback
  useEffect(() => {
    timestampsRef.current = timestamps;
  }, [timestamps]);

  const updateCurrentWord = useCallback(() => {
    const elapsed = (Date.now() - startTimeRef.current) / 1000; // Convert to seconds
    const ts = timestampsRef.current;

    // Find the word that should be highlighted
    let newIndex = -1;
    for (let i = 0; i < ts.length; i++) {
      if (elapsed >= ts[i].start && elapsed < ts[i].end) {
        newIndex = i;
        break;
      }
      // If we're past this word but before the next, show this word
      if (elapsed >= ts[i].end && (i === ts.length - 1 || elapsed < ts[i + 1].start)) {
        newIndex = i;
        break;
      }
    }

    setCurrentWordIndex(newIndex);

    // Stop tracking if we've passed all words
    if (ts.length > 0 && elapsed > ts[ts.length - 1].end + 0.5) {
      stopTracking();
    }
  }, []);

  const startTracking = useCallback((newTimestamps: WordTimestamp[]) => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    setTimestamps(newTimestamps);
    timestampsRef.current = newTimestamps;
    startTimeRef.current = Date.now();
    setCurrentWordIndex(0);
    setIsTracking(true);

    // Start update interval
    intervalRef.current = setInterval(updateCurrentWord, updateIntervalMs);
  }, [updateCurrentWord, updateIntervalMs]);

  // Add timestamps to existing tracking (for streaming TTS)
  const addTimestamps = useCallback((newTimestamps: WordTimestamp[]) => {
    if (!isTracking) {
      // If not tracking yet, start tracking
      startTracking(newTimestamps);
      return;
    }
    // Append new timestamps
    const updated = [...timestampsRef.current, ...newTimestamps];
    setTimestamps(updated);
    timestampsRef.current = updated;
  }, [isTracking, startTracking]);

  const stopTracking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsTracking(false);
    setCurrentWordIndex(-1);
    setTimestamps([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    currentWordIndex,
    timestamps,
    startTracking,
    addTimestamps,
    stopTracking,
    isTracking,
  };
}
