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
});
