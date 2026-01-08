/**
 * Hook for streaming speech-to-text via Deepgram.
 *
 * Connects to the backend WebSocket at /voice/stt and streams audio
 * from the device microphone, receiving transcripts in real-time.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import Audio from '@/modules/audio';
import { authStorage } from '@/lib/auth-storage';
import { WS_BASE_URL } from '@/lib/api';

export type STTStatus = 'idle' | 'connecting' | 'listening' | 'error';

export interface STTTranscript {
  transcript: string;
  confidence: number;
  isFinal: boolean;
  speechFinal: boolean;
}

export interface UseSTTOptions {
  /** Called when a transcript (partial or final) is received */
  onTranscript?: (transcript: STTTranscript) => void;
  /** Called when speech is detected */
  onSpeechStarted?: () => void;
  /** Called when an utterance ends (silence detected) */
  onUtteranceEnd?: () => void;
  /** Called on error */
  onError?: (error: string) => void;
  /** Called when connection status changes */
  onStatusChange?: (status: STTStatus) => void;
  /** Called after silence persists for silenceTimeoutMs after utterance end */
  onSilenceTimeout?: () => void;
  /** Duration of silence (ms) after utterance end before firing onSilenceTimeout. 0 to disable. */
  silenceTimeoutMs?: number;
}

export interface UseSTTResult {
  /** Current connection status */
  status: STTStatus;
  /** Start listening for speech */
  startListening: () => Promise<void>;
  /** Stop listening */
  stopListening: () => Promise<void>;
  /** Whether currently listening */
  isListening: boolean;
  /** Last error message */
  error: string | null;
}

export function useSTT(options: UseSTTOptions = {}): UseSTTResult {
  const {
    onTranscript,
    onSpeechStarted,
    onUtteranceEnd,
    onError,
    onStatusChange,
    onSilenceTimeout,
    silenceTimeoutMs = 0,
  } = options;

  const [status, setStatus] = useState<STTStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioSubscriptionRef = useRef<{ remove: () => void } | null>(null);
  const isListeningRef = useRef(false);
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear silence timeout
  const clearSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
  }, []);

  // We need a ref to stopListening to avoid circular dependency
  const stopListeningRef = useRef<() => Promise<void>>(() => Promise.resolve());

  // Start silence timeout
  const startSilenceTimeout = useCallback(() => {
    clearSilenceTimeout();
    if (silenceTimeoutMs > 0 && onSilenceTimeout) {
      silenceTimeoutRef.current = setTimeout(async () => {
        // Stop listening before firing callback
        await stopListeningRef.current();
        onSilenceTimeout();
      }, silenceTimeoutMs);
    }
  }, [silenceTimeoutMs, onSilenceTimeout, clearSilenceTimeout]);

  // Update status and notify
  const updateStatus = useCallback((newStatus: STTStatus) => {
    setStatus(newStatus);
    onStatusChange?.(newStatus);
  }, [onStatusChange]);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'connected':
          console.log('[STT] Connected to STT service');
          updateStatus('listening');
          break;

        case 'transcript':
          onTranscript?.({
            transcript: data.transcript,
            confidence: data.confidence,
            isFinal: data.is_final,
            speechFinal: data.speech_final,
          });
          break;

        case 'speech_started':
          clearSilenceTimeout();
          onSpeechStarted?.();
          break;

        case 'utterance_end':
          onUtteranceEnd?.();
          startSilenceTimeout();
          break;

        case 'error':
          console.error('[STT] Server error:', data.message);
          setError(data.message);
          onError?.(data.message);
          updateStatus('error');
          break;

        default:
          console.log('[STT] Unknown message type:', data.type);
      }
    } catch (e) {
      console.error('[STT] Failed to parse message:', e);
    }
  }, [onTranscript, onSpeechStarted, onUtteranceEnd, onError, updateStatus, clearSilenceTimeout, startSilenceTimeout]);

  // Send audio data to WebSocket
  const sendAudio = useCallback((base64Audio: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'audio',
        data: base64Audio,
      }));
    }
  }, []);

  // Start listening
  const startListening = useCallback(async () => {
    if (isListeningRef.current) {
      console.log('[STT] Already listening');
      return;
    }

    try {
      setError(null);
      updateStatus('connecting');

      // Check microphone permissions
      const hasPermission = await Audio.getPermissions();
      if (!hasPermission) {
        throw new Error('Microphone permission denied');
      }

      // Get auth token for WebSocket connection
      const token = await authStorage.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Connect to backend WebSocket (auth sent via first message for security)
      const wsUrl = `${WS_BASE_URL}/voice/stt`;
      console.log('[STT] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log('[STT] WebSocket connected, sending auth');

        // Send authentication as first message (more secure than query param)
        ws.send(JSON.stringify({ type: 'auth', token }));

        // Start recording audio
        await Audio.startRecording();
        isListeningRef.current = true;

        // Subscribe to audio input events
        audioSubscriptionRef.current = Audio.addListener(
          'onAudioInput',
          (event: { base64EncodedAudio: string }) => {
            sendAudio(event.base64EncodedAudio);
          }
        ) as { remove: () => void };
      };

      ws.onmessage = handleMessage;

      ws.onerror = (e) => {
        console.error('[STT] WebSocket error:', e);
        setError('Connection error');
        onError?.('Connection error');
        updateStatus('error');
      };

      ws.onclose = () => {
        console.log('[STT] WebSocket closed');
        if (isListeningRef.current) {
          // Unexpected close
          updateStatus('idle');
        }
      };

    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Failed to start STT';
      console.error('[STT] Start error:', errorMsg);
      setError(errorMsg);
      onError?.(errorMsg);
      updateStatus('error');
    }
  }, [handleMessage, sendAudio, updateStatus, onError]);

  // Stop listening
  const stopListening = useCallback(async () => {
    if (!isListeningRef.current) {
      console.log('[STT] Not listening');
      return;
    }

    console.log('[STT] Stopping...');
    isListeningRef.current = false;

    // Clear any pending silence timeout
    clearSilenceTimeout();

    // Stop audio recording
    try {
      await Audio.stopRecording();
    } catch (e) {
      console.error('[STT] Error stopping recording:', e);
    }

    // Remove audio subscription
    if (audioSubscriptionRef.current) {
      audioSubscriptionRef.current.remove();
      audioSubscriptionRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
        wsRef.current.close();
      } catch (e) {
        console.error('[STT] Error closing WebSocket:', e);
      }
      wsRef.current = null;
    }

    updateStatus('idle');
    console.log('[STT] Stopped');
  }, [updateStatus, clearSilenceTimeout]);

  // Keep ref updated for silence timeout callback and cleanup
  stopListeningRef.current = stopListening;

  // Cleanup on unmount only (empty deps = runs once)
  useEffect(() => {
    return () => {
      if (isListeningRef.current) {
        stopListeningRef.current();
      }
    };
  }, []);

  return {
    status,
    startListening,
    stopListening,
    isListening: status === 'listening',
    error,
  };
}
