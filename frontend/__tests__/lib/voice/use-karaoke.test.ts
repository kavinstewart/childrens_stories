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
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

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
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

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
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

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

  describe('addTimestamps (streaming)', () => {
    it('starts tracking if not already tracking', () => {
      const { result } = renderHook(() => useKaraoke());

      expect(result.current.isTracking).toBe(false);

      act(() => {
        result.current.addTimestamps([mockTimestamps[0]]);
      });

      expect(result.current.isTracking).toBe(true);
      expect(result.current.timestamps).toEqual([mockTimestamps[0]]);
      expect(result.current.currentWordIndex).toBe(0);
    });

    it('accumulates timestamps without resetting timer', () => {
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

      // First batch - just first word
      act(() => {
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
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

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
      const { result } = renderHook(() => useKaraoke({ updateIntervalMs: 50 }));

      // This is what happens in production - multiple words arrive before React re-renders
      // All calls use the same function reference, so state-based checks would fail
      act(() => {
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
});
