/**
 * React hook for Hume EVI chat integration
 *
 * Uses React Native's built-in WebSocket (not the Hume JS SDK which requires Node.js).
 * Audio handling is done via the native AudioModule.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';

import AudioModule from '../../modules/audio';
import { api } from '../api';
import type {
  ChatMessage,
  ConnectionStatus,
  ToolCall,
  UseEviChatOptions,
  UseEviChatReturn,
} from './types';

// Hume EVI WebSocket endpoint
const EVI_WEBSOCKET_URL = 'wss://api.hume.ai/v0/evi/chat';

// Audio format constants matching native module
const SAMPLE_RATE = 48000;
const CHANNELS = 1;

/**
 * EVI WebSocket message types (incoming)
 */
interface EviMessage {
  type: string;
  // audio_output
  data?: string;
  // user_message, assistant_message
  message?: { content?: string };
  // tool_call
  tool_call_id?: string;
  name?: string;
  parameters?: string;
  // error
  error?: string;
  code?: string;
}

/**
 * Hook for managing Hume EVI voice chat sessions
 */
export function useEviChat(options: UseEviChatOptions): UseEviChatReturn {
  const { configId, onToolCall, sessionSettings } = options;

  // Connection state
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isMuted, setIsMuted] = useState(false);

  // Refs for WebSocket, cleanup, and state guards
  const socketRef = useRef<WebSocket | null>(null);
  const audioListenerRef = useRef<{ remove: () => void } | null>(null);
  const isConnectingRef = useRef(false);
  const isMountedRef = useRef(true);

  /**
   * Add a message to the chat history
   */
  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const message: ChatMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, message]);
  }, []);

  /**
   * Send a message through the WebSocket
   */
  const sendMessage = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type, ...payload }));
    }
  }, []);

  /**
   * Handle incoming EVI messages
   */
  const handleMessage = useCallback(
    (message: EviMessage) => {
      switch (message.type) {
        case 'audio_output':
          // Queue audio for playback via native module
          if (message.data) {
            AudioModule.enqueueAudio(message.data).catch((err) => {
              console.error('Failed to enqueue audio:', err);
            });
          }
          break;

        case 'user_message':
          if (message.message?.content) {
            addMessage('user', message.message.content);
          }
          break;

        case 'assistant_message':
          if (message.message?.content) {
            addMessage('assistant', message.message.content);
          }
          break;

        case 'user_interruption':
          // User interrupted - stop playback
          AudioModule.stopPlayback().catch((err) => {
            console.error('Failed to stop playback:', err);
          });
          break;

        case 'tool_call':
          // Handle tool call if handler provided
          if (onToolCall && message.tool_call_id && message.name) {
            let parameters: Record<string, unknown> = {};
            if (message.parameters) {
              try {
                parameters = JSON.parse(message.parameters);
              } catch (e) {
                console.error('Failed to parse tool call parameters:', e);
              }
            }
            const toolCall: ToolCall = {
              toolCallId: message.tool_call_id,
              name: message.name,
              parameters,
            };

            onToolCall(toolCall)
              .then((result) => {
                // Send tool response back to EVI
                sendMessage('tool_response', {
                  tool_call_id: toolCall.toolCallId,
                  content: result,
                });
              })
              .catch((err) => {
                console.error('Tool call failed:', err);
                sendMessage('tool_response', {
                  tool_call_id: toolCall.toolCallId,
                  content: JSON.stringify({ error: err.message }),
                });
              });
          }
          break;

        case 'error':
          console.error('EVI error:', message);
          setError(new Error(message.error || 'Unknown EVI error'));
          break;
      }
    },
    [addMessage, onToolCall, sendMessage]
  );

  /**
   * Handle audio input from native module
   */
  const handleAudioInput = useCallback((event: { base64EncodedAudio: string }) => {
    sendMessage('audio_input', { data: event.base64EncodedAudio });
  }, [sendMessage]);

  /**
   * Connect to Hume EVI
   */
  const connect = useCallback(async () => {
    // Guard against rapid successive calls
    if (isConnectingRef.current || socketRef.current) {
      return;
    }
    isConnectingRef.current = true;

    setStatus('connecting');
    setError(null);
    setMessages([]);

    try {
      // Check platform - EVI only supported on iOS and web for now
      if (Platform.OS !== 'ios' && Platform.OS !== 'web') {
        throw new Error('EVI is only supported on iOS and web');
      }

      // Get microphone permissions
      const hasPermission = await AudioModule.getPermissions();
      if (!hasPermission) {
        throw new Error('Microphone permission denied');
      }

      // Fetch access token from backend
      const tokenResponse = await api.getHumeToken();

      // Build WebSocket URL with config ID and access token
      // Note: Token in query param is the documented Hume approach for WebSocket auth
      // (WebSocket API doesn't support custom headers in browsers/React Native)
      // See: https://dev.hume.ai/docs/introduction/api-key
      const wsUrl = `${EVI_WEBSOCKET_URL}?config_id=${encodeURIComponent(configId)}&access_token=${encodeURIComponent(tokenResponse.access_token)}`;

      // Create WebSocket connection
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = async () => {
        if (!isMountedRef.current) {
          socket.close();
          return;
        }

        console.log('EVI WebSocket connected');

        // Convert tools to Hume format (parameters must be stringified JSON)
        const humeTools = sessionSettings?.tools?.map((tool) => ({
          type: tool.type,
          name: tool.name,
          description: tool.description,
          parameters: JSON.stringify(tool.parameters),
          fallback_content: tool.fallbackContent,
        }));

        // Send session settings with audio encoding info
        sendMessage('session_settings', {
          audio: {
            encoding: 'linear16',
            sample_rate: SAMPLE_RATE,
            channels: CHANNELS,
          },
          ...(sessionSettings?.systemPrompt && {
            system_prompt: sessionSettings.systemPrompt,
          }),
          ...(humeTools && {
            tools: humeTools,
          }),
        });

        // Start recording audio
        await AudioModule.startRecording();

        isConnectingRef.current = false;
        if (isMountedRef.current) {
          setStatus('connected');
        }
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as EviMessage;
          handleMessage(message);
        } catch (e) {
          console.error('Failed to parse EVI message:', e);
        }
      };

      socket.onerror = (event) => {
        console.error('EVI WebSocket error:', event);
        isConnectingRef.current = false;
        if (isMountedRef.current) {
          setError(new Error('WebSocket connection error'));
          setStatus('error');
        }
      };

      socket.onclose = () => {
        console.log('EVI WebSocket closed');
        isConnectingRef.current = false;
        socketRef.current = null;
        if (isMountedRef.current) {
          setStatus('disconnected');
        }
        AudioModule.stopRecording().catch(console.error);
      };

      // Set up audio input listener
      const subscription = AudioModule.addListener('onAudioInput', handleAudioInput);
      audioListenerRef.current = subscription;
    } catch (err) {
      console.error('Failed to connect to EVI:', err);
      isConnectingRef.current = false;
      if (isMountedRef.current) {
        setError(err instanceof Error ? err : new Error(String(err)));
        setStatus('error');
      }
    }
  }, [configId, handleMessage, handleAudioInput, sendMessage, sessionSettings]);

  /**
   * Disconnect from Hume EVI
   */
  const disconnect = useCallback(() => {
    // Reset connection guard
    isConnectingRef.current = false;

    // Stop recording
    AudioModule.stopRecording().catch(console.error);
    AudioModule.stopPlayback().catch(console.error);

    // Remove audio listener
    if (audioListenerRef.current) {
      audioListenerRef.current.remove();
      audioListenerRef.current = null;
    }

    // Close WebSocket
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    if (isMountedRef.current) {
      setStatus('disconnected');
      setError(null);
    }
  }, []);

  /**
   * Mute microphone
   */
  const mute = useCallback(async () => {
    await AudioModule.mute();
    setIsMuted(true);
  }, []);

  /**
   * Unmute microphone
   */
  const unmute = useCallback(async () => {
    await AudioModule.unmute();
    setIsMuted(false);
  }, []);

  /**
   * Send tool response (for external tool call handling)
   */
  const sendToolResponse = useCallback((toolCallId: string, content: string) => {
    sendMessage('tool_response', {
      tool_call_id: toolCallId,
      content,
    });
  }, [sendMessage]);

  // Track mount state and cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    error,
    messages,
    connect,
    disconnect,
    mute,
    unmute,
    isMuted,
    sendToolResponse,
  };
}
