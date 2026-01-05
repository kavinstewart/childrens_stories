// API client for the children's stories backend

import { authStorage } from './auth-storage';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://dev.exoselfsystems.com';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type GenerationType = 'simple' | 'standard' | 'illustrated';

export interface StoryOutline {
  title: string;
  protagonist_goal: string;
  stakes: string;
  characters: string;
  setting: string;
  emotional_arc: string;
  plot_summary: string;
  moral: string;
  spread_count: number;  // Number of spreads (typically 12)
}

/**
 * A spread is a double-page unit in a picture book.
 * Standard picture books have 12 spreads for story content.
 */
export interface StorySpread {
  spread_number: number;
  text: string;
  word_count: number;
  was_revised: boolean;
  page_turn_note?: string;  // What makes reader want to turn the page
  illustration_prompt?: string;
  illustration_url?: string;
  illustration_updated_at?: string;  // For cache busting after regeneration
  composed_prompt?: string;  // Full prompt sent to image model (for dev editing)
}

export interface StoryProgress {
  stage: 'outline' | 'spreads' | 'character_refs' | 'illustrations' | 'failed';
  stage_detail: string;
  percentage: number;
  characters_total?: number;
  characters_completed?: number;
  spreads_total?: number;
  spreads_completed?: number;
  warnings?: string[];
  updated_at?: string;
}

export interface Story {
  id: string;
  status: JobStatus;
  goal: string;
  target_age_range: string;
  generation_type: GenerationType;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  title?: string;
  word_count?: number;
  spread_count?: number;  // Number of spreads (typically 12)
  attempts?: number;
  outline?: StoryOutline;
  spreads?: StorySpread[];
  is_illustrated: boolean;
  error_message?: string;
  progress?: StoryProgress;
  isCached?: boolean;  // Runtime flag: true when story is loaded from cache
}

export interface StoryListResponse {
  stories: Story[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateStoryRequest {
  goal: string;
}

export interface CreateStoryResponse {
  id: string;
  status: JobStatus;
  message: string;
}

export interface StoryRecommendation {
  id: string;
  title?: string;
  goal: string;
  cover_url?: string;
  is_illustrated: boolean;
}

export interface RecommendationsResponse {
  recommendations: StoryRecommendation[];
}

export interface RegenerateSpreadResponse {
  job_id: string;
  story_id: string;
  spread_number: number;
  status: JobStatus;
  message: string;
}

export interface LoginRequest {
  pin: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Get auth token if available
  const token = await authStorage.getToken();
  const authHeaders: Record<string, string> = {};
  if (token) {
    authHeaders['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(response.status, errorText || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// API functions
export const api = {
  // List all stories with pagination
  listStories: async (params?: {
    limit?: number;
    offset?: number;
    status?: JobStatus;
  }): Promise<StoryListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.status) searchParams.set('status', params.status);

    const query = searchParams.toString();
    return fetchApi(`/stories/${query ? `?${query}` : ''}`);
  },

  // Get a single story by ID
  getStory: async (id: string): Promise<Story> => {
    return fetchApi(`/stories/${id}`);
  },

  // Create a new story generation job
  createStory: async (request: CreateStoryRequest): Promise<CreateStoryResponse> => {
    return fetchApi('/stories/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Delete a story
  deleteStory: async (id: string): Promise<void> => {
    return fetchApi(`/stories/${id}`, {
      method: 'DELETE',
    });
  },

  // Get spread image URL (a spread = two facing pages)
  // Optional updatedAt param for cache busting after regeneration
  getSpreadImageUrl: (storyId: string, spreadNumber: number, updatedAt?: string): string => {
    const baseUrl = `${API_BASE_URL}/stories/${storyId}/spreads/${spreadNumber}/image`;
    if (updatedAt) {
      const timestamp = new Date(updatedAt).getTime();
      return `${baseUrl}?v=${timestamp}`;
    }
    return baseUrl;
  },

  // Get character reference image URL
  getCharacterImageUrl: (storyId: string, characterName: string): string => {
    return `${API_BASE_URL}/stories/${storyId}/characters/${encodeURIComponent(characterName)}/image`;
  },

  // Get story recommendations
  getRecommendations: async (storyId: string, limit: number = 4): Promise<RecommendationsResponse> => {
    return fetchApi(`/stories/${storyId}/recommendations?limit=${limit}`);
  },

  // Regenerate a spread illustration
  // Optional prompt parameter allows overriding the default composed prompt
  regenerateSpread: async (storyId: string, spreadNumber: number, prompt?: string): Promise<RegenerateSpreadResponse> => {
    return fetchApi(`/stories/${storyId}/spreads/${spreadNumber}/regenerate`, {
      method: 'POST',
      body: JSON.stringify(prompt ? { prompt } : {}),
    });
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    return fetchApi('/health');
  },

  // Authentication
  login: async (request: LoginRequest): Promise<LoginResponse> => {
    return fetchApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Send frontend logs to backend
  sendLogs: async (entries: Array<{
    level: string;
    message: string;
    timestamp: string;
    context?: Record<string, unknown>;
  }>): Promise<void> => {
    return fetchApi('/logs/ingest', {
      method: 'POST',
      body: JSON.stringify({ entries }),
    });
  },
};
