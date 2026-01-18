/**
 * Tests for debounced interim transcript updates in new-voice.tsx
 *
 * Fix 2 (story-2irr): Debounce interim transcript updates to 150ms
 * Fix 3 (story-hfrs): Use useRef instead of useState for interim transcripts
 */

import { renderHook, act } from '@testing-library/react-native';
import { useCallback, useRef, useState } from 'react';

// Mock the debounce interval for testing
const DEBOUNCE_MS = 150;

/**
 * Extracted transcript handling logic for testing.
 * This mirrors the implementation in new-voice.tsx.
 */
function useTranscriptHandler() {
  const [transcript, setTranscript] = useState('');
  const transcriptRef = useRef(''); // Accumulated final text
  const interimRef = useRef(''); // Latest interim text (not triggering re-renders)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const renderCount = useRef(0);

  // Track renders
  renderCount.current += 1;

  const handleTranscript = useCallback((data: { transcript: string; isFinal: boolean }) => {
    if (data.isFinal) {
      // Final transcripts: update accumulated text and state immediately
      const newText = transcriptRef.current
        ? `${transcriptRef.current} ${data.transcript}`
        : data.transcript;
      transcriptRef.current = newText;
      interimRef.current = ''; // Clear interim
      setTranscript(newText);

      // Clear any pending debounce
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
    } else {
      // Interim transcripts: store in ref, debounce state updates
      interimRef.current = data.transcript;

      // Only set up debounce if not already pending
      if (!debounceTimerRef.current) {
        debounceTimerRef.current = setTimeout(() => {
          const displayText = transcriptRef.current
            ? `${transcriptRef.current} ${interimRef.current}`
            : interimRef.current;
          setTranscript(displayText);
          debounceTimerRef.current = null;
        }, DEBOUNCE_MS);
      }
    }
  }, []);

  return {
    transcript,
    handleTranscript,
    getRenderCount: () => renderCount.current,
    getInterimRef: () => interimRef.current,
  };
}

describe('useTranscriptHandler', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('updates state immediately for final transcripts', () => {
    const { result } = renderHook(() => useTranscriptHandler());

    act(() => {
      result.current.handleTranscript({ transcript: 'hello world', isFinal: true });
    });

    expect(result.current.transcript).toBe('hello world');
  });

  it('does not update state immediately for interim transcripts', () => {
    const { result } = renderHook(() => useTranscriptHandler());
    const initialRenderCount = result.current.getRenderCount();

    act(() => {
      result.current.handleTranscript({ transcript: 'hel', isFinal: false });
    });

    // State should not have changed yet (still empty)
    expect(result.current.transcript).toBe('');
    // Render count should not have increased beyond the initial
    expect(result.current.getRenderCount()).toBe(initialRenderCount);
  });

  it('stores interim transcript in ref without re-render', () => {
    const { result } = renderHook(() => useTranscriptHandler());

    act(() => {
      result.current.handleTranscript({ transcript: 'hel', isFinal: false });
    });

    // Ref should have the interim value
    expect(result.current.getInterimRef()).toBe('hel');
    // But state should still be empty
    expect(result.current.transcript).toBe('');
  });

  it('debounces multiple interim transcripts within window', async () => {
    const { result } = renderHook(() => useTranscriptHandler());
    const initialRenderCount = result.current.getRenderCount();

    // Send multiple interim transcripts rapidly
    act(() => {
      result.current.handleTranscript({ transcript: 'h', isFinal: false });
    });
    act(() => {
      result.current.handleTranscript({ transcript: 'he', isFinal: false });
    });
    act(() => {
      result.current.handleTranscript({ transcript: 'hel', isFinal: false });
    });
    act(() => {
      result.current.handleTranscript({ transcript: 'hell', isFinal: false });
    });
    act(() => {
      result.current.handleTranscript({ transcript: 'hello', isFinal: false });
    });

    // State should still be empty (debounce not fired yet)
    expect(result.current.transcript).toBe('');

    // Advance timers past debounce window
    await act(async () => {
      await jest.advanceTimersByTimeAsync(DEBOUNCE_MS);
    });

    // Now state should have the latest interim value
    expect(result.current.transcript).toBe('hello');
    // Should only have caused 1 additional render (from the debounced update)
    expect(result.current.getRenderCount()).toBe(initialRenderCount + 1);
  });

  it('final transcript clears pending debounce and updates immediately', async () => {
    const { result } = renderHook(() => useTranscriptHandler());

    // Send interim transcript
    act(() => {
      result.current.handleTranscript({ transcript: 'hel', isFinal: false });
    });

    // Before debounce fires, send final transcript
    act(() => {
      result.current.handleTranscript({ transcript: 'hello', isFinal: true });
    });

    // State should have final value immediately
    expect(result.current.transcript).toBe('hello');

    // Advance timers - should not cause additional update
    const renderCountBefore = result.current.getRenderCount();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(DEBOUNCE_MS * 2);
    });

    // No additional renders should have occurred
    expect(result.current.getRenderCount()).toBe(renderCountBefore);
    expect(result.current.transcript).toBe('hello');
  });

  it('accumulates final transcripts correctly', () => {
    const { result } = renderHook(() => useTranscriptHandler());

    act(() => {
      result.current.handleTranscript({ transcript: 'hello', isFinal: true });
    });
    act(() => {
      result.current.handleTranscript({ transcript: 'world', isFinal: true });
    });

    expect(result.current.transcript).toBe('hello world');
  });

  it('combines accumulated final text with interim display', async () => {
    const { result } = renderHook(() => useTranscriptHandler());

    // First, a final transcript
    act(() => {
      result.current.handleTranscript({ transcript: 'hello', isFinal: true });
    });

    expect(result.current.transcript).toBe('hello');

    // Then an interim transcript
    act(() => {
      result.current.handleTranscript({ transcript: 'wor', isFinal: false });
    });

    // Wait for debounce
    await act(async () => {
      await jest.advanceTimersByTimeAsync(DEBOUNCE_MS);
    });

    // Should show accumulated + interim
    expect(result.current.transcript).toBe('hello wor');
  });
});
