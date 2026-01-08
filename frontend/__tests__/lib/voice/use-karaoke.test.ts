/**
 * Tests for useKaraoke hook
 */

import { renderHook, act } from '@testing-library/react-native';
import { useKaraoke, WordTimestamp } from '../../../lib/voice/use-karaoke';

describe('useKaraoke', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const mockTimestamps: WordTimestamp[] = [
    { word: 'Hello', start: 0.0, end: 0.3 },
    { word: 'world', start: 0.35, end: 0.7 },
    { word: 'how', start: 0.75, end: 0.9 },
    { word: 'are', start: 0.95, end: 1.1 },
    { word: 'you', start: 1.15, end: 1.4 },
  ];

  describe('initial state', () => {
    it('starts with no tracking', () => {
      const { result } = renderHook(() => useKaraoke());

      expect(result.current.isTracking).toBe(false);
      expect(result.current.currentWordIndex).toBe(-1);
      expect(result.current.timestamps).toEqual([]);
    });
  });

  describe('startTracking', () => {
    it('starts tracking with timestamps', () => {
      const { result } = renderHook(() => useKaraoke());

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      expect(result.current.isTracking).toBe(true);
      expect(result.current.timestamps).toEqual(mockTimestamps);
      expect(result.current.currentWordIndex).toBe(0);
    });

    it('updates current word index over time', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      expect(result.current.currentWordIndex).toBe(0);

      // Advance to second word (0.35s = 350ms)
      act(() => {
        jest.advanceTimersByTime(400);
      });

      expect(result.current.currentWordIndex).toBe(1);

      // Advance to third word (0.75s = 750ms)
      act(() => {
        jest.advanceTimersByTime(400);
      });

      expect(result.current.currentWordIndex).toBe(2);
    });

    it('handles gap between words', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      // Advance to gap between first and second word (0.32s)
      act(() => {
        jest.advanceTimersByTime(320);
      });

      // Should still show first word during the gap
      expect(result.current.currentWordIndex).toBe(0);
    });
  });

  describe('stopTracking', () => {
    it('stops tracking and resets state', () => {
      const { result } = renderHook(() => useKaraoke());

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      expect(result.current.isTracking).toBe(true);

      act(() => {
        result.current.stopTracking();
      });

      expect(result.current.isTracking).toBe(false);
      expect(result.current.currentWordIndex).toBe(-1);
      expect(result.current.timestamps).toEqual([]);
    });
  });

  describe('auto-stop', () => {
    it('auto-stops after all words are spoken', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      expect(result.current.isTracking).toBe(true);

      // Advance past all words (last word ends at 1.4s + 0.5s buffer)
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(result.current.isTracking).toBe(false);
    });
  });

  describe('restart tracking', () => {
    it('can restart with new timestamps', () => {
      const { result } = renderHook(() => useKaraoke());

      // Start first tracking
      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      // Advance a bit
      act(() => {
        jest.advanceTimersByTime(500);
      });

      // Restart with new timestamps
      const newTimestamps: WordTimestamp[] = [
        { word: 'New', start: 0.0, end: 0.2 },
        { word: 'text', start: 0.25, end: 0.5 },
      ];

      act(() => {
        result.current.startTracking(newTimestamps);
      });

      expect(result.current.timestamps).toEqual(newTimestamps);
      expect(result.current.currentWordIndex).toBe(0);
    });
  });

  describe('startTimer', () => {
    it('starts timer without timestamps', () => {
      const { result } = renderHook(() => useKaraoke());

      expect(result.current.isTracking).toBe(false);

      act(() => {
        result.current.startTimer();
      });

      expect(result.current.isTracking).toBe(true);
      expect(result.current.timestamps).toEqual([]);
      expect(result.current.currentWordIndex).toBe(0);
    });

    it('does nothing if already tracking', () => {
      const { result } = renderHook(() => useKaraoke());

      act(() => {
        result.current.startTracking(mockTimestamps);
      });

      const startTime = Date.now();

      act(() => {
        jest.advanceTimersByTime(100);
        result.current.startTimer(); // Should not reset
      });

      // Timer should not be reset (currentWordIndex should advance)
      expect(result.current.isTracking).toBe(true);
    });
  });

  describe('addTimestamps (streaming)', () => {
    it('accumulates timestamps without starting timer', () => {
      const { result } = renderHook(() => useKaraoke());

      // Add timestamps before starting timer
      act(() => {
        result.current.addTimestamps([mockTimestamps[0]]);
      });

      // Should have timestamps but not be tracking (timer not started)
      expect(result.current.timestamps).toEqual([mockTimestamps[0]]);
      expect(result.current.isTracking).toBe(false);
    });

    it('accumulates timestamps without resetting timer', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      // Start timer first (simulating onAudioStart)
      act(() => {
        result.current.startTimer();
        result.current.addTimestamps([mockTimestamps[0]]);
      });

      expect(result.current.timestamps.length).toBe(1);
      expect(result.current.currentWordIndex).toBe(0);

      // Advance 200ms into first word
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(result.current.currentWordIndex).toBe(0);

      // Add more timestamps - should NOT reset timer
      act(() => {
        result.current.addTimestamps([mockTimestamps[1], mockTimestamps[2]]);
      });

      expect(result.current.timestamps.length).toBe(3);
      // Should still be on first word since we're at 200ms
      expect(result.current.currentWordIndex).toBe(0);

      // Advance to second word (350ms from start)
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(result.current.currentWordIndex).toBe(1);
    });

    it('handles rapid streaming of single words', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      // Start timer first
      act(() => {
        result.current.startTimer();
      });

      // Simulate Cartesia streaming words one at a time
      act(() => {
        result.current.addTimestamps([{ word: 'Hello', start: 0.0, end: 0.3 }]);
      });

      expect(result.current.timestamps.length).toBe(1);

      act(() => {
        result.current.addTimestamps([{ word: 'world', start: 0.35, end: 0.7 }]);
      });

      expect(result.current.timestamps.length).toBe(2);

      act(() => {
        result.current.addTimestamps([{ word: 'how', start: 0.75, end: 0.9 }]);
      });

      expect(result.current.timestamps.length).toBe(3);

      // Advance to when "world" should be highlighted
      act(() => {
        jest.advanceTimersByTime(400);
      });

      expect(result.current.currentWordIndex).toBe(1);
    });

    it('handles multiple addTimestamps calls in same event loop tick (stale closure test)', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50, audioLatencyMs: 0 }));

      // Start timer and add timestamps in same tick (like production)
      act(() => {
        result.current.startTimer();
        result.current.addTimestamps([{ word: 'Hello', start: 0.0, end: 0.3 }]);
        result.current.addTimestamps([{ word: 'world', start: 0.35, end: 0.7 }]);
        result.current.addTimestamps([{ word: 'how', start: 0.75, end: 0.9 }]);
      });

      // All 3 words should be accumulated, not just the last one
      expect(result.current.timestamps.length).toBe(3);
      expect(result.current.timestamps[0].word).toBe('Hello');
      expect(result.current.timestamps[1].word).toBe('world');
      expect(result.current.timestamps[2].word).toBe('how');
      expect(result.current.isTracking).toBe(true);

      // Timer should have started from first word, so advancing should work correctly
      act(() => {
        jest.advanceTimersByTime(400);
      });

      expect(result.current.currentWordIndex).toBe(1); // "world"
    });
  });

  describe('audioLatencyMs', () => {
    it('delays word highlighting to compensate for audio buffer', () => {
      // Use 200ms latency offset
      const { result } = renderHook(() => useKaraoke({
        updateIntervalMs: 50,
        audioLatencyMs: 200
      }));

      act(() => {
        result.current.startTimer();
        result.current.addTimestamps([
          { word: 'Hello', start: 0.0, end: 0.3 },
          { word: 'world', start: 0.35, end: 0.7 },
        ]);
      });

      // At time 0, with 200ms latency offset, elapsed time is negative
      // so currentWordIndex should be 0 (initial value from startTimer)
      expect(result.current.currentWordIndex).toBe(0);

      // Advance 100ms - still within latency buffer, elapsed time is negative
      act(() => {
        jest.advanceTimersByTime(100);
      });
      // Timer starts word 0 immediately but elapsed calculation is offset
      expect(result.current.currentWordIndex).toBe(0);

      // Advance to 250ms total - now 50ms of "real" audio time (250-200=50ms)
      // First word (0.0-0.3s) should be highlighted
      act(() => {
        jest.advanceTimersByTime(150);
      });
      expect(result.current.currentWordIndex).toBe(0);

      // Advance to 550ms total - 350ms of "real" audio time (550-200=350ms)
      // Second word starts at 350ms, should now be word 1
      act(() => {
        jest.advanceTimersByTime(300);
      });
      expect(result.current.currentWordIndex).toBe(1);
    });

    it('uses default 150ms latency when not specified', () => {
      // Only specify updateIntervalMs, let audioLatencyMs use default of 150ms
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

      act(() => {
        result.current.startTimer();
        result.current.addTimestamps([
          { word: 'Test', start: 0.0, end: 0.2 },
        ]);
      });

      // At 100ms, with default 150ms latency, elapsed is -50ms (negative)
      // Word should be at index 0 (first word shown during latency window)
      act(() => {
        jest.advanceTimersByTime(100);
      });
      expect(result.current.currentWordIndex).toBe(0);

      // At 200ms, with 150ms latency, elapsed is 50ms
      // First word (0.0-0.2s = 0-200ms) should still be highlighted
      act(() => {
        jest.advanceTimersByTime(100);
      });
      expect(result.current.currentWordIndex).toBe(0);
    });
  });
});
