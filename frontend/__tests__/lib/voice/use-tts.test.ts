/**
 * Tests for useTTS hook
 */

// Mock expo-audio-stream
jest.mock('@mykin-ai/expo-audio-stream', () => ({
  ExpoPlayAudioStream: {
    playSound: jest.fn(),
    stopSound: jest.fn().mockResolvedValue(undefined),
    setSoundConfig: jest.fn(),
  },
  EncodingTypes: {
    PCM_S16LE: 'pcm_s16le',
  },
}));

// Mock expo-audio-stream events
jest.mock('@mykin-ai/expo-audio-stream/build/events', () => ({
  subscribeToEvent: jest.fn(() => ({
    remove: jest.fn(),
  })),
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

  simulateError() {
    this.onerror?.({});
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

(global as any).WebSocket = MockWebSocket;

import { renderHook, act } from '@testing-library/react-native';
import { useTTS } from '../../../lib/voice/use-tts';
import { authStorage } from '@/lib/auth-storage';

describe('useTTS', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockWsInstance = null;
    wsOpenCallback = null;
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('connect', () => {
    it('resolves when server sends connected message', async () => {
      const { result } = renderHook(() => useTTS());

      let connectPromise: Promise<void>;

      await act(async () => {
        connectPromise = result.current.connect();
        await Promise.resolve();
      });

      // Trigger WebSocket open
      act(() => {
        wsOpenCallback?.();
      });

      await act(async () => {
        await Promise.resolve();
      });

      // Simulate server connected response
      act(() => {
        mockWsInstance?.simulateMessage({ type: 'connected' });
      });

      await act(async () => {
        await connectPromise!;
      });

      expect(result.current.status).toBe('ready');
    });

    it('rejects on connection error', async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useTTS({ onError }));

      let connectPromise: Promise<void>;

      await act(async () => {
        connectPromise = result.current.connect();
        await Promise.resolve();
      });

      // Trigger WebSocket open
      act(() => {
        wsOpenCallback?.();
      });

      await act(async () => {
        await Promise.resolve();
      });

      // Simulate error
      act(() => {
        mockWsInstance?.simulateError();
      });

      await expect(connectPromise!).rejects.toThrow('Connection error');
      expect(result.current.status).toBe('error');
      expect(onError).toHaveBeenCalledWith('Connection error');
    });

    it('rejects on timeout', async () => {
      const onError = jest.fn();
      const { result } = renderHook(() => useTTS({ onError }));

      let connectPromise: Promise<void>;

      await act(async () => {
        connectPromise = result.current.connect();
        await Promise.resolve();
      });

      // Trigger WebSocket open but don't send connected message
      act(() => {
        wsOpenCallback?.();
      });

      // Advance past timeout
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      await expect(connectPromise!).rejects.toThrow('Connection timeout');
      expect(result.current.status).toBe('error');
      expect(onError).toHaveBeenCalledWith('Connection timeout');
    });

    it('rejects when not authenticated', async () => {
      (authStorage.getToken as jest.Mock).mockResolvedValueOnce(null);
      const onError = jest.fn();
      const { result } = renderHook(() => useTTS({ onError }));

      let connectError: unknown;
      await act(async () => {
        try {
          await result.current.connect();
        } catch (e) {
          connectError = e;
        }
        // Allow state updates to flush
        await Promise.resolve();
      });

      expect(connectError).toBeInstanceOf(Error);
      expect((connectError as Error).message).toBe('Not authenticated');
      expect(result.current.status).toBe('error');
      expect(onError).toHaveBeenCalledWith('Not authenticated');
    });
  });

  describe('speak', () => {
    it('auto-connects and sends synthesize message', async () => {
      const { result } = renderHook(() => useTTS());

      let speakPromise: Promise<void>;

      await act(async () => {
        speakPromise = result.current.speak('Hello world');
        await Promise.resolve();
      });

      // Trigger WebSocket open
      act(() => {
        wsOpenCallback?.();
      });

      await act(async () => {
        await Promise.resolve();
      });

      // Simulate server connected response
      act(() => {
        mockWsInstance?.simulateMessage({ type: 'connected' });
      });

      await act(async () => {
        await speakPromise!;
      });

      // Should have sent auth and synthesize messages
      expect(mockWsInstance?.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'auth', token: 'test-token' })
      );
      expect(mockWsInstance?.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"synthesize"')
      );
      expect(mockWsInstance?.send).toHaveBeenCalledWith(
        expect.stringContaining('"text":"Hello world"')
      );
    });

    it('skips empty text', async () => {
      const { result } = renderHook(() => useTTS());

      await act(async () => {
        await result.current.speak('   ');
      });

      // Should not have created a WebSocket
      expect(mockWsInstance).toBeNull();
    });
  });

  describe('disconnect', () => {
    it('closes the WebSocket and resets status', async () => {
      const { result } = renderHook(() => useTTS());

      // Connect first
      await act(async () => {
        result.current.connect();
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
      });

      expect(result.current.status).toBe('ready');

      // Disconnect
      act(() => {
        result.current.disconnect();
      });

      expect(mockWsInstance?.close).toHaveBeenCalled();
      expect(result.current.status).toBe('idle');
    });
  });
});
