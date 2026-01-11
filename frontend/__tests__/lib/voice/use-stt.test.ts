/**
 * Tests for useSTT hook silence timeout functionality
 *
 * Uses a simplified mock approach to test the silence timeout logic.
 */

// Mock Audio module BEFORE any imports
jest.mock('@/modules/audio', () => ({
  __esModule: true,
  default: {
    getPermissions: jest.fn().mockResolvedValue(true),
    startRecording: jest.fn().mockResolvedValue(undefined),
    stopRecording: jest.fn().mockResolvedValue(undefined),
    addListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
  },
}));

// Mock auth storage
jest.mock('@/lib/auth-storage', () => ({
  authStorage: {
    getToken: jest.fn().mockResolvedValue('test-token'),
  },
}));

// Mock WebSocket globally
let mockWsInstance: MockWebSocket | null = null;
let wsOpenCallback: (() => void) | null = null;

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readyState = MockWebSocket.OPEN;

  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;

  constructor(_url: string) {
    mockWsInstance = this;
    // Store callback for manual triggering
    Promise.resolve().then(() => {
      wsOpenCallback = () => this.onopen?.();
    });
  }

  send = jest.fn();
  close = jest.fn();

  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

(global as any).WebSocket = MockWebSocket;

import { renderHook, act } from '@testing-library/react-native';
import { useSTT } from '../../../lib/voice/use-stt';

describe('useSTT silence timeout', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockWsInstance = null;
    wsOpenCallback = null;
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('fires onSilenceTimeout after silence duration', async () => {
    const onSilenceTimeout = jest.fn();
    const onUtteranceEnd = jest.fn();

    const { result } = renderHook(() => useSTT({
      onUtteranceEnd,
      onSilenceTimeout,
      silenceTimeoutMs: 3000,
    }));

    // Start listening
    act(() => {
      result.current.startListening();
    });

    // Let promises resolve
    await act(async () => {
      await Promise.resolve();
    });

    // Trigger WebSocket open
    act(() => {
      wsOpenCallback?.();
    });

    await act(async () => {
      await Promise.resolve();
    });

    // Simulate connected
    act(() => {
      mockWsInstance?.simulateMessage({ type: 'connected' });
    });

    // Simulate utterance end
    act(() => {
      mockWsInstance?.simulateMessage({ type: 'utterance_end' });
    });

    expect(onUtteranceEnd).toHaveBeenCalled();
    expect(onSilenceTimeout).not.toHaveBeenCalled();

    // Advance time past timeout (use async version to flush microtasks from async callback)
    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
    });

    expect(onSilenceTimeout).toHaveBeenCalledTimes(1);
  });

  it('cancels timeout when speech restarts', async () => {
    const onSilenceTimeout = jest.fn();

    const { result } = renderHook(() => useSTT({
      onSilenceTimeout,
      silenceTimeoutMs: 3000,
    }));

    act(() => {
      result.current.startListening();
    });

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      wsOpenCallback?.();
    });

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      mockWsInstance?.simulateMessage({ type: 'connected' });
      mockWsInstance?.simulateMessage({ type: 'utterance_end' });
    });

    // Wait 1.5s
    await act(async () => {
      await jest.advanceTimersByTimeAsync(1500);
    });

    // Speech restarts - cancels timeout
    act(() => {
      mockWsInstance?.simulateMessage({ type: 'speech_started' });
    });

    // Wait past original timeout
    await act(async () => {
      await jest.advanceTimersByTimeAsync(2000);
    });

    expect(onSilenceTimeout).not.toHaveBeenCalled();
  });

  it('does not fire timeout when disabled (0ms)', async () => {
    const onSilenceTimeout = jest.fn();

    const { result } = renderHook(() => useSTT({
      onSilenceTimeout,
      silenceTimeoutMs: 0,
    }));

    act(() => {
      result.current.startListening();
    });

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      wsOpenCallback?.();
    });

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      mockWsInstance?.simulateMessage({ type: 'connected' });
      mockWsInstance?.simulateMessage({ type: 'utterance_end' });
    });

    await act(async () => {
      await jest.advanceTimersByTimeAsync(10000);
    });

    expect(onSilenceTimeout).not.toHaveBeenCalled();
  });
});
