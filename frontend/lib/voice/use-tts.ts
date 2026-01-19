/**
 * Hook for streaming text-to-speech via Cartesia.
 *
 * Connects to the backend WebSocket at /voice/tts and synthesizes
 * text to speech, streaming audio chunks back for playback.
 *
 * Uses @mykin-ai/expo-audio-stream for reliable audio streaming playback.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ExpoPlayAudioStream, EncodingTypes } from '@mykin-ai/expo-audio-stream';
import { subscribeToEvent } from '@mykin-ai/expo-audio-stream/build/events';
import { authStorage } from '@/lib/auth-storage';
import { WS_BASE_URL } from '@/lib/api';

// Sample rate from Cartesia TTS (24kHz PCM S16LE)
const TTS_SAMPLE_RATE = 24000;

/** Map error codes to user-friendly messages */
function getUserFriendlyError(code: string | undefined, fallbackMessage: string): string {
  switch (code) {
    case 'auth_required':
      return 'Please log in again to use voice features';
    case 'tts_not_configured':
      return 'Voice service is not available';
    case 'tts_credits_exhausted':
      return 'Voice service credits exhausted';
    case 'tts_auth_failed':
      return 'Voice service authentication failed';
    case 'tts_rate_limited':
      return 'Too many requests, please wait a moment';
    case 'tts_connection_failed':
      return 'Could not connect to voice service';
    default:
      return fallbackMessage || 'Voice service error';
  }
}

/** Map WebSocket close codes to user-friendly messages */
function getCloseCodeMessage(code: number): string | null {
  switch (code) {
    case 1000:
      return null; // Normal close, no error
    case 1001:
      return 'Server is restarting';
    case 1006:
      return 'Connection lost unexpectedly';
    case 1008:
      return 'Please log in again'; // Policy violation (auth)
    case 1011:
      return 'Voice service encountered an error';
    case 1013:
      return 'Server is busy, please try again';
    default:
      return code >= 4000 ? 'Voice service error' : null;
  }
}

export type TTSStatus = 'idle' | 'connecting' | 'ready' | 'speaking' | 'error';

export interface UseTTSOptions {
  /** Voice ID to use (optional, uses server default if not provided) */
  voiceId?: string;
  /** Suppress automatic audio playback - only fire callbacks (for collecting audio) */
  suppressPlayback?: boolean;
  /** Called when first audio chunk arrives (for sync timing) */
  onAudioStart?: (contextId: string) => void;
  /** Called when audio chunk is received */
  onAudioChunk?: (data: string, contextId: string) => void;
  /** Called when word timestamps are received */
  onTimestamps?: (words: Array<{ word: string; start: number; end: number }>, contextId: string) => void;
  /** Called when synthesis is done for a context */
  onDone?: (contextId: string) => void;
  /** Called on error */
  onError?: (error: string) => void;
  /** Called when connection status changes */
  onStatusChange?: (status: TTSStatus) => void;
}

export interface UseTTSResult {
  /** Current connection status */
  status: TTSStatus;
  /** Connect to TTS service */
  connect: () => Promise<void>;
  /** Disconnect from TTS service */
  disconnect: () => void;
  /** Synthesize text to speech (auto-connects if needed) */
  speak: (text: string, contextId?: string) => Promise<void>;
  /** Stop playback and disconnect */
  stop: () => Promise<void>;
  /** Stop playback only (keeps connection) */
  stopPlayback: () => Promise<void>;
  /** Whether currently speaking */
  isSpeaking: boolean;
  /** Last error message */
  error: string | null;
}

export function useTTS(options: UseTTSOptions = {}): UseTTSResult {
  const {
    voiceId,
    suppressPlayback = false,
    onAudioStart,
    onAudioChunk,
    onTimestamps,
    onDone,
    onError,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<TTSStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  // Ref to resolve/reject the connection promise
  const connectResolversRef = useRef<{
    resolve: () => void;
    reject: (error: Error) => void;
  } | null>(null);
  // Track contexts that have fired onAudioStart
  const audioStartedContextsRef = useRef<Set<string>>(new Set());
  // Track contexts waiting for SoundStarted event (queue to handle multiple)
  const pendingAudioStartRef = useRef<string[]>([]);
  // Keep onAudioStart callback in ref for event listener
  const onAudioStartRef = useRef(onAudioStart);
  onAudioStartRef.current = onAudioStart;
  // Track if playSound has ever been called (to avoid calling stopSound before init)
  const hasPlayedAudioRef = useRef(false);
  // Track last error received (to show meaningful message on close)
  const lastErrorRef = useRef<{ code?: string; message: string } | null>(null);

  // Update status and notify
  const updateStatus = useCallback((newStatus: TTSStatus) => {
    setStatus(newStatus);
    onStatusChange?.(newStatus);
  }, [onStatusChange]);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'connected':
          console.log('[TTS] Connected to TTS service');
          updateStatus('ready');
          // Resolve the connection promise if waiting
          if (connectResolversRef.current) {
            connectResolversRef.current.resolve();
            connectResolversRef.current = null;
          }
          break;

        case 'audio':
          // Enqueue audio for playback using expo-audio-stream
          if (data.data) {
            // Only play audio if not suppressed (suppressPlayback used for collecting audio without playing)
            if (!suppressPlayback) {
              const turnId = data.context_id || 'tts-default';
              ExpoPlayAudioStream.playSound(data.data, turnId, EncodingTypes.PCM_S16LE);
              hasPlayedAudioRef.current = true;
              updateStatus('speaking');
              // Queue this context for SoundStarted event (if not already started)
              // onAudioStart will fire when native player actually starts
              if (!audioStartedContextsRef.current.has(turnId)) {
                // Only add if not already in queue
                if (!pendingAudioStartRef.current.includes(turnId)) {
                  pendingAudioStartRef.current.push(turnId);
                }
              }
            }
            onAudioChunk?.(data.data, data.context_id);
          }
          break;

        case 'timestamps':
          // Debug: Log first word to verify format is {word, start, end}
          if (data.words?.length > 0) {
            const first = data.words[0];
            console.log('[TTS] Timestamp format check:', {
              hasWord: 'word' in first,
              hasStart: 'start' in first,
              hasEnd: 'end' in first,
              sample: first,
            });
          }
          onTimestamps?.(data.words, data.context_id);
          break;

        case 'done':
          console.log('[TTS] Synthesis complete for context:', data.context_id);
          updateStatus('ready');
          onDone?.(data.context_id);
          break;

        case 'error':
          console.error('[TTS] Server error:', data.code || 'unknown', '-', data.message);
          // Store error for use in close handler
          lastErrorRef.current = { code: data.code, message: data.message };
          // Map error codes to user-friendly messages
          const userMessage = getUserFriendlyError(data.code, data.message);
          setError(userMessage);
          onError?.(userMessage);
          updateStatus('error');
          // Reject the connection promise if waiting
          if (connectResolversRef.current) {
            connectResolversRef.current.reject(new Error(userMessage));
            connectResolversRef.current = null;
          }
          break;

        default:
          console.log('[TTS] Unknown message type:', data.type);
      }
    } catch (e) {
      console.error('[TTS] Failed to parse message:', e);
    }
  }, [suppressPlayback, onAudioChunk, onTimestamps, onDone, onError, updateStatus]);

  // Connect to TTS service - returns Promise that resolves when connected
  const connect = useCallback(async (): Promise<void> => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[TTS] Already connected');
      return;
    }

    // Get auth token first (before creating promise)
    const token = await authStorage.getToken();
    if (!token) {
      const errorMsg = 'Not authenticated';
      setError(errorMsg);
      onError?.(errorMsg);
      updateStatus('error');
      throw new Error(errorMsg);
    }

    setError(null);
    updateStatus('connecting');

    // Create a promise that resolves when we receive 'connected' from server
    return new Promise((resolve, reject) => {
      const CONNECTION_TIMEOUT = 5000;

      // Set up timeout
      const timeoutId = setTimeout(() => {
        connectResolversRef.current = null;
        const errorMsg = 'Connection timeout';
        setError(errorMsg);
        onError?.(errorMsg);
        updateStatus('error');
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        reject(new Error(errorMsg));
      }, CONNECTION_TIMEOUT);

      // Store resolvers so handleMessage can resolve/reject
      connectResolversRef.current = {
        resolve: () => {
          clearTimeout(timeoutId);
          resolve();
        },
        reject: (error: Error) => {
          clearTimeout(timeoutId);
          reject(error);
        },
      };

      // Connect to backend WebSocket
      const wsUrl = `${WS_BASE_URL}/voice/tts`;
      console.log('[TTS] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[TTS] WebSocket connected, sending auth');
        // Send authentication as first message
        ws.send(JSON.stringify({ type: 'auth', token }));
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        clearTimeout(timeoutId);
        // Use last error from server if available, otherwise infer from state
        const lastError = lastErrorRef.current;
        const errorMsg = lastError
          ? getUserFriendlyError(lastError.code, lastError.message)
          : 'Could not connect to voice service';
        console.error('[TTS] WebSocket error - ' + errorMsg);
        setError(errorMsg);
        onError?.(errorMsg);
        updateStatus('error');
        if (connectResolversRef.current) {
          connectResolversRef.current = null;
          reject(new Error(errorMsg));
        }
      };

      ws.onclose = (event) => {
        console.log('[TTS] WebSocket closed, code:', event.code, 'reason:', event.reason);
        // Clear last error ref for next connection
        const lastError = lastErrorRef.current;
        lastErrorRef.current = null;

        updateStatus('idle');
        // If we're still waiting for connection, reject with meaningful error
        if (connectResolversRef.current) {
          clearTimeout(timeoutId);
          // Determine error message: use server error, close code, or generic
          let errorMsg: string;
          if (lastError) {
            errorMsg = getUserFriendlyError(lastError.code, lastError.message);
          } else {
            errorMsg = getCloseCodeMessage(event.code) || 'Connection closed';
          }
          console.error('[TTS] Connection failed:', errorMsg);
          setError(errorMsg);
          onError?.(errorMsg);
          connectResolversRef.current = null;
          reject(new Error(errorMsg));
        }
      };
    });
  }, [handleMessage, updateStatus, onError]);

  // Disconnect from TTS service
  const disconnect = useCallback(() => {
    console.log('[TTS] disconnect() called, wsRef exists:', !!wsRef.current);
    if (wsRef.current) {
      try {
        console.log('[TTS] Sending stop message and closing WebSocket');
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
        wsRef.current.close();
      } catch (e) {
        console.error('[TTS] Error closing WebSocket:', e);
      }
      wsRef.current = null;
    }
    updateStatus('idle');
  }, [updateStatus]);

  // Synthesize text to speech (auto-connects if needed)
  const speak = useCallback(async (text: string, contextId?: string) => {
    const trimmedText = text.trim();
    if (!trimmedText) {
      console.warn('[TTS] Empty text, skipping');
      return;
    }

    // Auto-connect if not connected
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.log('[TTS] Not connected, connecting first...');
      try {
        await connect();
      } catch (e) {
        // Error already handled by connect()
        console.error('[TTS] Failed to connect:', e);
        return;
      }
    }

    // Double-check connection is ready
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error('[TTS] Connection not ready after connect');
      setError('Failed to connect to TTS service');
      return;
    }

    console.log('[TTS] Synthesizing:', trimmedText.substring(0, 50) + '...');

    wsRef.current.send(JSON.stringify({
      type: 'synthesize',
      text: trimmedText,
      voice_id: voiceId,
      context_id: contextId,
    }));
  }, [voiceId, connect]);

  // Stop playback
  const stopPlayback = useCallback(async () => {
    console.log('[TTS] stopPlayback() called, hasPlayedAudio:', hasPlayedAudioRef.current);
    // Only call stopSound if we've actually played audio (prevents native crash on first call)
    if (!hasPlayedAudioRef.current) {
      console.log('[TTS] stopPlayback() skipped - no audio played yet');
      return;
    }
    try {
      await ExpoPlayAudioStream.stopSound();
      // Clear tracking state so next playback can fire onAudioStart
      audioStartedContextsRef.current.clear();
      pendingAudioStartRef.current = [];
      hasPlayedAudioRef.current = false;
      if (status === 'speaking') {
        updateStatus('ready');
      }
      console.log('[TTS] stopPlayback() completed');
    } catch (e) {
      console.error('[TTS] Error stopping playback:', e);
    }
  }, [status, updateStatus]);

  // Keep ref updated for cleanup
  const disconnectRef = useRef(disconnect);
  disconnectRef.current = disconnect;

  // Configure audio player sample rate on mount
  useEffect(() => {
    // Configure for 24kHz Cartesia audio (cast to bypass restrictive TS type)
    ExpoPlayAudioStream.setSoundConfig({
      sampleRate: TTS_SAMPLE_RATE as 16000 | 44100 | 48000,
    });
  }, []);

  // Subscribe to SoundStarted event - fires when native audio player actually starts
  // This gives accurate sync timing instead of guessing buffer latency
  // Note: SoundStarted event has no context ID, so we use FIFO queue to match.
  // This works correctly when playing one audio stream at a time (normal usage).
  // Edge case: if multiple streams play concurrently and finish out of order,
  // the wrong context could be matched. This is acceptable for our use case.
  useEffect(() => {
    const subscription = subscribeToEvent('SoundStarted', async () => {
      // Process next pending context from queue (FIFO order)
      const pendingContext = pendingAudioStartRef.current.shift();
      if (pendingContext && !audioStartedContextsRef.current.has(pendingContext)) {
        console.log('[TTS] SoundStarted event - audio actually playing for:', pendingContext);
        audioStartedContextsRef.current.add(pendingContext);
        onAudioStartRef.current?.(pendingContext);
      }
    });

    return () => {
      subscription.remove();
    };
  }, []);

  // Cleanup on unmount only (empty deps = runs once)
  useEffect(() => {
    return () => {
      disconnectRef.current();
    };
  }, []);

  // Stop everything (alias for common use)
  const stop = useCallback(async () => {
    await stopPlayback();
    disconnect();
  }, [stopPlayback, disconnect]);

  return {
    status,
    connect,
    disconnect,
    speak,
    stop,
    stopPlayback,
    isSpeaking: status === 'speaking',
    error,
  };
}
