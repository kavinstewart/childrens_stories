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
  /** Audio latency offset in ms to compensate for buffer delay (default: 0ms with SoundStarted event) */
  audioLatencyMs?: number;
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
  /** Start the timer (call when audio starts) - does not reset timestamps */
  startTimer: () => void;
  /** Stop tracking and reset */
  stopTracking: () => void;
  /** Whether currently tracking */
  isTracking: boolean;
}

export function useKaraoke(options: UseKaraokeOptions = {}): UseKaraokeResult {
  const { updateIntervalMs = 50, audioLatencyMs = 0 } = options;

  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const [timestamps, setTimestamps] = useState<WordTimestamp[]>([]);
  const [isTracking, setIsTracking] = useState(false);

  const startTimeRef = useRef<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timestampsRef = useRef<WordTimestamp[]>([]);
  const isTrackingRef = useRef(false); // Ref for synchronous checks

  // Keep ref in sync for interval callback
  useEffect(() => {
    timestampsRef.current = timestamps;
  }, [timestamps]);

  const updateCurrentWord = useCallback(() => {
    const elapsed = (Date.now() - startTimeRef.current) / 1000; // Convert to seconds
    const ts = timestampsRef.current;

    // If no timestamps yet, keep current index
    if (ts.length === 0) {
      return;
    }

    // If elapsed is negative (still in audio buffer latency window), show first word
    if (elapsed < 0) {
      setCurrentWordIndex(0);
      return;
    }

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
    if (elapsed > ts[ts.length - 1].end + 0.5) {
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
    // Add audioLatencyMs to start time to compensate for audio buffer delay
    // This makes the timer think playback started later, syncing with actual audio output
    startTimeRef.current = Date.now() + audioLatencyMs;
    setCurrentWordIndex(0);
    setIsTracking(true);
    isTrackingRef.current = true; // Set ref synchronously

    // Start update interval
    intervalRef.current = setInterval(updateCurrentWord, updateIntervalMs);
  }, [updateCurrentWord, updateIntervalMs, audioLatencyMs]);

  // Start timer only (called when audio starts, before timestamps arrive)
  const startTimer = useCallback(() => {
    if (isTrackingRef.current) return; // Already tracking

    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Add audioLatencyMs to start time to compensate for audio buffer delay
    // This makes the timer think playback started later, syncing with actual audio output
    startTimeRef.current = Date.now() + audioLatencyMs;
    setCurrentWordIndex(0);
    setIsTracking(true);
    isTrackingRef.current = true;

    // Start update interval
    intervalRef.current = setInterval(updateCurrentWord, updateIntervalMs);
  }, [updateCurrentWord, updateIntervalMs, audioLatencyMs]);

  // Add timestamps to current tracking (for streaming TTS)
  // Just appends timestamps, does NOT start timer
  const addTimestamps = useCallback((newTimestamps: WordTimestamp[]) => {
    // Append new timestamps (timer should already be started via startTimer)
    const updated = [...timestampsRef.current, ...newTimestamps];
    setTimestamps(updated);
    timestampsRef.current = updated;
  }, []);

  const stopTracking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsTracking(false);
    isTrackingRef.current = false; // Clear ref synchronously
    setCurrentWordIndex(-1);
    setTimestamps([]);
    timestampsRef.current = [];
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
    startTimer,
    stopTracking,
    isTracking,
  };
}
