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
  /** Called when no meaningful activity (utterance_end) occurs within noActivityTimeoutMs. Safety net for edge cases. */
  onNoActivityTimeout?: () => void;
  /** Duration (ms) before firing onNoActivityTimeout if no utterance_end received. 0 to disable. Default 15000. */
  noActivityTimeoutMs?: number;
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
    onNoActivityTimeout,
    noActivityTimeoutMs = 0,
  } = options;

  const [status, setStatus] = useState<STTStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioSubscriptionRef = useRef<{ remove: () => void } | null>(null);
  const isListeningRef = useRef(false);
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noActivityTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debug counters for logging
  const audioChunkCountRef = useRef(0);
  const totalAudioBytesRef = useRef(0);
  const sessionStartTimeRef = useRef<number>(0);

  // Clear silence timeout
  const clearSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      console.log('[STT] Clearing silence timeout');
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
      console.log(`[STT] Starting silence timeout (${silenceTimeoutMs}ms)`);
      silenceTimeoutRef.current = setTimeout(async () => {
        console.log('[STT] Silence timeout FIRED - stopping');
        // Stop listening before firing callback
        await stopListeningRef.current();
        onSilenceTimeout();
      }, silenceTimeoutMs);
    }
  }, [silenceTimeoutMs, onSilenceTimeout, clearSilenceTimeout]);

  // Clear no-activity timeout (safety net)
  const clearNoActivityTimeout = useCallback(() => {
    if (noActivityTimeoutRef.current) {
      console.log('[STT] Clearing no-activity timeout (utterance_end received)');
      clearTimeout(noActivityTimeoutRef.current);
      noActivityTimeoutRef.current = null;
    }
  }, []);

  // Start no-activity timeout (safety net for when utterance_end never arrives)
  const startNoActivityTimeout = useCallback(() => {
    clearNoActivityTimeout();
    if (noActivityTimeoutMs > 0 && onNoActivityTimeout) {
      console.log(`[STT] Starting no-activity timeout (${noActivityTimeoutMs}ms)`);
      noActivityTimeoutRef.current = setTimeout(async () => {
        const elapsed = Date.now() - sessionStartTimeRef.current;
        console.error(`[STT] No-activity timeout FIRED after ${elapsed}ms - no utterance_end received. Audio chunks sent: ${audioChunkCountRef.current}, total bytes: ${totalAudioBytesRef.current}`);
        // Stop listening before firing callback
        await stopListeningRef.current();
        onNoActivityTimeout();
      }, noActivityTimeoutMs);
    }
  }, [noActivityTimeoutMs, onNoActivityTimeout, clearNoActivityTimeout]);

  // Update status and notify
  const updateStatus = useCallback((newStatus: STTStatus) => {
    setStatus(newStatus);
    onStatusChange?.(newStatus);
  }, [onStatusChange]);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      const elapsed = Date.now() - sessionStartTimeRef.current;

      switch (data.type) {
        case 'connected':
          console.log(`[STT] Connected to STT service (session started ${elapsed}ms ago)`);
          updateStatus('listening');
          // Start safety net timeout for edge cases where utterance_end never arrives
          startNoActivityTimeout();
          break;

        case 'transcript':
          console.log(`[STT] Transcript received (${elapsed}ms): "${data.transcript.substring(0, 50)}${data.transcript.length > 50 ? '...' : ''}" final=${data.is_final} speechFinal=${data.speech_final} confidence=${data.confidence?.toFixed(2)}`);
          onTranscript?.({
            transcript: data.transcript,
            confidence: data.confidence,
            isFinal: data.is_final,
            speechFinal: data.speech_final,
          });
          break;

        case 'speech_started':
          console.log(`[STT] Speech started (${elapsed}ms)`);
          clearSilenceTimeout();
          onSpeechStarted?.();
          break;

        case 'utterance_end':
          console.log(`[STT] Utterance end (${elapsed}ms) - clearing no-activity timeout`);
          // Clear safety net - normal flow is working
          clearNoActivityTimeout();
          onUtteranceEnd?.();
          startSilenceTimeout();
          break;

        case 'error':
          console.error(`[STT] Server error (${elapsed}ms):`, data.message, data.code || '');
          setError(data.message);
          onError?.(data.message);
          updateStatus('error');
          break;

        default:
          console.log(`[STT] Unknown message type (${elapsed}ms):`, data.type, data);
      }
    } catch (e) {
      console.error('[STT] Failed to parse message:', e, 'raw:', event.data?.substring?.(0, 200));
    }
  }, [onTranscript, onSpeechStarted, onUtteranceEnd, onError, updateStatus, clearSilenceTimeout, startSilenceTimeout, startNoActivityTimeout, clearNoActivityTimeout]);

  // Send audio data to WebSocket
  const sendAudio = useCallback((base64Audio: string) => {
    const ws = wsRef.current;
    if (!ws) {
      console.warn('[STT] sendAudio called but WebSocket is null');
      return;
    }

    if (ws.readyState !== WebSocket.OPEN) {
      console.warn(`[STT] sendAudio called but WebSocket not open (readyState=${ws.readyState}: ${['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] || 'UNKNOWN'})`);
      return;
    }

    // Track audio stats
    audioChunkCountRef.current++;
    const chunkBytes = Math.floor(base64Audio.length * 0.75); // Approximate decoded size
    totalAudioBytesRef.current += chunkBytes;

    // Log periodically (every 50 chunks) to avoid log spam
    if (audioChunkCountRef.current % 50 === 1) {
      const elapsed = Date.now() - sessionStartTimeRef.current;
      console.log(`[STT] Audio chunk #${audioChunkCountRef.current} (${elapsed}ms): ~${chunkBytes} bytes, total ~${totalAudioBytesRef.current} bytes`);
    }

    ws.send(JSON.stringify({
      type: 'audio',
      data: base64Audio,
    }));
  }, []);

  // Start listening
  const startListening = useCallback(async () => {
    if (isListeningRef.current) {
      console.log('[STT] Already listening');
      return;
    }

    // Reset session counters
    audioChunkCountRef.current = 0;
    totalAudioBytesRef.current = 0;
    sessionStartTimeRef.current = Date.now();

    console.log('[STT] Starting new session...');

    try {
      setError(null);
      updateStatus('connecting');

      // Check microphone permissions
      console.log('[STT] Checking microphone permissions...');
      const hasPermission = await Audio.getPermissions();
      if (!hasPermission) {
        throw new Error('Microphone permission denied');
      }
      console.log('[STT] Microphone permission granted');

      // Get auth token for WebSocket connection
      const token = await authStorage.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      console.log('[STT] Auth token retrieved');

      // Connect to backend WebSocket (auth sent via first message for security)
      const wsUrl = `${WS_BASE_URL}/voice/stt`;
      console.log('[STT] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        const elapsed = Date.now() - sessionStartTimeRef.current;
        console.log(`[STT] WebSocket connected (${elapsed}ms), sending auth`);

        // Send authentication as first message (more secure than query param)
        ws.send(JSON.stringify({ type: 'auth', token }));

        // Start recording audio
        console.log('[STT] Starting audio recording...');
        try {
          await Audio.startRecording();
          console.log('[STT] Audio recording started successfully');
        } catch (recordErr) {
          console.error('[STT] Failed to start audio recording:', recordErr);
          throw recordErr;
        }
        isListeningRef.current = true;

        // Subscribe to audio input events
        console.log('[STT] Subscribing to audio input events...');
        audioSubscriptionRef.current = Audio.addListener(
          'onAudioInput',
          (event: { base64EncodedAudio: string }) => {
            sendAudio(event.base64EncodedAudio);
          }
        ) as { remove: () => void };
        console.log('[STT] Audio subscription active');
      };

      ws.onmessage = handleMessage;

      ws.onerror = (e) => {
        const elapsed = Date.now() - sessionStartTimeRef.current;
        // Extract useful info from the error event
        const errorInfo = {
          type: (e as Event).type,
          // WebSocket errors don't expose much detail for security reasons
        };
        console.error(`[STT] WebSocket error (${elapsed}ms):`, JSON.stringify(errorInfo), e);
        setError('Connection error');
        onError?.('Connection error');
        updateStatus('error');
      };

      ws.onclose = (e) => {
        const elapsed = Date.now() - sessionStartTimeRef.current;
        console.log(`[STT] WebSocket closed (${elapsed}ms) - code=${e.code} reason="${e.reason}" wasClean=${e.wasClean}. Audio chunks sent: ${audioChunkCountRef.current}, total bytes: ${totalAudioBytesRef.current}`);
        if (isListeningRef.current) {
          // Unexpected close
          console.warn('[STT] Unexpected close while still listening');
          updateStatus('idle');
        }
      };

    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Failed to start STT';
      const elapsed = Date.now() - sessionStartTimeRef.current;
      console.error(`[STT] Start error (${elapsed}ms):`, errorMsg, e);
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

    const elapsed = Date.now() - sessionStartTimeRef.current;
    console.log(`[STT] Stopping... (session duration: ${elapsed}ms, audio chunks: ${audioChunkCountRef.current}, total bytes: ${totalAudioBytesRef.current})`);
    isListeningRef.current = false;

    // Clear any pending timeouts
    console.log('[STT] Clearing timeouts...');
    clearSilenceTimeout();
    clearNoActivityTimeout();

    // Stop audio recording
    console.log('[STT] Stopping audio recording...');
    try {
      await Audio.stopRecording();
      console.log('[STT] Audio recording stopped');
    } catch (e) {
      console.error('[STT] Error stopping recording:', e);
    }

    // Remove audio subscription
    if (audioSubscriptionRef.current) {
      console.log('[STT] Removing audio subscription...');
      audioSubscriptionRef.current.remove();
      audioSubscriptionRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      const wsState = wsRef.current.readyState;
      console.log(`[STT] Closing WebSocket (readyState=${wsState}: ${['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][wsState] || 'UNKNOWN'})...`);
      try {
        if (wsState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'stop' }));
        }
        wsRef.current.close();
      } catch (e) {
        console.error('[STT] Error closing WebSocket:', e);
      }
      wsRef.current = null;
    }

    updateStatus('idle');
    console.log('[STT] Stopped');
  }, [updateStatus, clearSilenceTimeout, clearNoActivityTimeout]);

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
