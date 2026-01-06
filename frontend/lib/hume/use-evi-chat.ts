/**
 * React hook for Hume EVI chat integration
 *
 * Manages WebSocket connection to Hume EVI, handles audio streaming
 * via native module, and processes messages and tool calls.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Hume, HumeClient } from 'hume';
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

// Audio format constants matching native module
const SAMPLE_RATE = 48000;
const CHANNELS = 1;

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
  const socketRef = useRef<Hume.empathicVoice.chat.ChatSocket | null>(null);
  const audioListenerRef = useRef<{ remove: () => void } | null>(null);
  const isConnectingRef = useRef(false); // Guard against rapid connect calls
  const isMountedRef = useRef(true); // Track mount state for async operations

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
   * Handle incoming EVI messages
   */
  const handleMessage = useCallback(
    (message: Hume.empathicVoice.SubscribeEvent) => {
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
          if (onToolCall && message.toolCallId && message.name) {
            let parameters: Record<string, unknown> = {};
            if (message.parameters) {
              try {
                parameters = JSON.parse(message.parameters);
              } catch (e) {
                console.error('Failed to parse tool call parameters:', e);
              }
            }
            const toolCall: ToolCall = {
              toolCallId: message.toolCallId,
              name: message.name,
              parameters,
            };

            onToolCall(toolCall)
              .then((result) => {
                // Send tool response back to EVI
                socketRef.current?.sendToolResponseMessage({
                  toolCallId: toolCall.toolCallId,
                  content: result,
                });
              })
              .catch((err) => {
                console.error('Tool call failed:', err);
                socketRef.current?.sendToolResponseMessage({
                  toolCallId: toolCall.toolCallId,
                  content: JSON.stringify({ error: err.message }),
                });
              });
          }
          break;

        case 'error':
          console.error('EVI error:', message);
          setError(new Error(message.message || 'Unknown EVI error'));
          break;
      }
    },
    [addMessage, onToolCall]
  );

  /**
   * Handle audio input from native module
   * Note: Uses socketRef directly to avoid stale closure issues with status state
   */
  const handleAudioInput = useCallback((event: { base64EncodedAudio: string }) => {
    // Check socketRef directly - it's always current, unlike status which could be stale
    const socket = socketRef.current;
    if (socket) {
      socket.sendAudioInput({ data: event.base64EncodedAudio });
    }
  }, []);

  /**
   * Connect to Hume EVI
   */
  const connect = useCallback(async () => {
    // Use ref to guard against rapid successive calls (avoids stale closure issues)
    if (isConnectingRef.current || socketRef.current) {
      return;
    }
    isConnectingRef.current = true;

    setStatus('connecting');
    setError(null);
    setMessages([]);

    try {
      // Check platform - EVI only supported on iOS for now
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

      // Create Hume client with access token
      const client = new HumeClient({
        accessToken: tokenResponse.access_token,
      });

      // Connect to EVI chat
      const socket = client.empathicVoice.chat.connect({
        configId,
      });

      socketRef.current = socket;

      // Set up event handlers
      socket.on('open', async () => {
        // Check if component still mounted before updating state
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
          fallbackContent: tool.fallbackContent,
        }));

        // Send session settings with audio encoding info
        socket.sendSessionSettings({
          audio: {
            encoding: 'linear16',
            sampleRate: SAMPLE_RATE,
            channels: CHANNELS,
          },
          ...(sessionSettings?.systemPrompt && {
            systemPrompt: sessionSettings.systemPrompt,
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
      });

      socket.on('message', handleMessage);

      socket.on('error', (err) => {
        console.error('EVI WebSocket error:', err);
        isConnectingRef.current = false;
        if (isMountedRef.current) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setStatus('error');
        }
      });

      socket.on('close', () => {
        console.log('EVI WebSocket closed');
        isConnectingRef.current = false;
        socketRef.current = null;
        if (isMountedRef.current) {
          setStatus('disconnected');
        }
        AudioModule.stopRecording().catch(console.error);
      });

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
  }, [configId, handleMessage, handleAudioInput, sessionSettings]);

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
    if (socketRef.current) {
      socketRef.current.sendToolResponseMessage({
        toolCallId,
        content,
      });
    }
  }, []);

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
