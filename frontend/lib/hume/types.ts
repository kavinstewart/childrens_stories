/**
 * Types for Hume EVI integration
 */

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ToolCall {
  toolCallId: string;
  name: string;
  parameters: Record<string, unknown>;
}

export interface ToolParameters {
  type: 'object';
  required?: string[];
  properties: Record<
    string,
    {
      type: string;
      description: string;
      enum?: string[];
    }
  >;
}

export interface ToolDefinition {
  type: 'function';
  name: string;
  description: string;
  parameters: ToolParameters;
  fallbackContent?: string;
}

export interface SessionSettings {
  systemPrompt?: string;
  tools?: ToolDefinition[];
}

export interface UseEviChatOptions {
  configId: string;
  onToolCall?: (toolCall: ToolCall) => Promise<string>;
  sessionSettings?: SessionSettings;
}

export interface UseEviChatReturn {
  // Connection state
  status: ConnectionStatus;
  error: Error | null;

  // Chat data
  messages: ChatMessage[];

  // Controls
  connect: () => Promise<void>;
  disconnect: () => void;
  mute: () => Promise<void>;
  unmute: () => Promise<void>;
  isMuted: boolean;

  // Tool response
  sendToolResponse: (toolCallId: string, content: string) => void;
}
