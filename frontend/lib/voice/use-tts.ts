/**
 * Hook for streaming text-to-speech via Cartesia.
 *
 * Connects to the backend WebSocket at /voice/tts and synthesizes
 * text to speech, streaming audio chunks back for playback.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import Audio from '@/modules/audio';
import { authStorage } from '@/lib/auth-storage';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://dev.exoselfsystems.com';

// Convert HTTP URL to WebSocket URL
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export type TTSStatus = 'idle' | 'connecting' | 'ready' | 'speaking' | 'error';

export interface UseTTSOptions {
  /** Voice ID to use (optional, uses server default if not provided) */
  voiceId?: string;
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
  /** Synthesize text to speech */
  speak: (text: string, contextId?: string) => Promise<void>;
  /** Stop playback */
  stopPlayback: () => Promise<void>;
  /** Whether currently speaking */
  isSpeaking: boolean;
  /** Last error message */
  error: string | null;
}

export function useTTS(options: UseTTSOptions = {}): UseTTSResult {
  const {
    voiceId,
    onAudioChunk,
    onTimestamps,
    onDone,
    onError,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<TTSStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

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
          break;

        case 'audio':
          // Enqueue audio for playback
          Audio.enqueueAudio(data.data);
          updateStatus('speaking');
          onAudioChunk?.(data.data, data.context_id);
          break;

        case 'timestamps':
          onTimestamps?.(data.words, data.context_id);
          break;

        case 'done':
          console.log('[TTS] Synthesis complete for context:', data.context_id);
          updateStatus('ready');
          onDone?.(data.context_id);
          break;

        case 'error':
          console.error('[TTS] Server error:', data.message);
          setError(data.message);
          onError?.(data.message);
          updateStatus('error');
          break;

        default:
          console.log('[TTS] Unknown message type:', data.type);
      }
    } catch (e) {
      console.error('[TTS] Failed to parse message:', e);
    }
  }, [onAudioChunk, onTimestamps, onDone, onError, updateStatus]);

  // Connect to TTS service
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[TTS] Already connected');
      return;
    }

    try {
      setError(null);
      updateStatus('connecting');

      // Get auth token for WebSocket connection
      const token = await authStorage.getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

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

      ws.onerror = (e) => {
        console.error('[TTS] WebSocket error:', e);
        setError('Connection error');
        onError?.('Connection error');
        updateStatus('error');
      };

      ws.onclose = () => {
        console.log('[TTS] WebSocket closed');
        updateStatus('idle');
      };

    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Failed to connect to TTS';
      console.error('[TTS] Connect error:', errorMsg);
      setError(errorMsg);
      onError?.(errorMsg);
      updateStatus('error');
    }
  }, [handleMessage, updateStatus, onError]);

  // Disconnect from TTS service
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
        wsRef.current.close();
      } catch (e) {
        console.error('[TTS] Error closing WebSocket:', e);
      }
      wsRef.current = null;
    }
    updateStatus('idle');
  }, [updateStatus]);

  // Synthesize text to speech
  const speak = useCallback(async (text: string, contextId?: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error('[TTS] Not connected');
      setError('Not connected to TTS service');
      return;
    }

    const trimmedText = text.trim();
    if (!trimmedText) {
      console.warn('[TTS] Empty text, skipping');
      return;
    }

    console.log('[TTS] Synthesizing:', trimmedText.substring(0, 50) + '...');

    wsRef.current.send(JSON.stringify({
      type: 'synthesize',
      text: trimmedText,
      voice_id: voiceId,
      context_id: contextId,
    }));
  }, [voiceId]);

  // Stop playback
  const stopPlayback = useCallback(async () => {
    try {
      await Audio.stopPlayback();
      if (status === 'speaking') {
        updateStatus('ready');
      }
    } catch (e) {
      console.error('[TTS] Error stopping playback:', e);
    }
  }, [status, updateStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    connect,
    disconnect,
    speak,
    stopPlayback,
    isSpeaking: status === 'speaking',
    error,
  };
}
