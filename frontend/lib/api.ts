// API client for the children's stories backend

// For Expo Go on device, use your Mac's IP address
// For simulator, localhost works
const API_BASE_URL = __DEV__
  ? 'http://192.168.86.39:8000'  // Your Mac's IP for device testing
  : 'http://localhost:8000';

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
}

// Backwards compatibility alias
export type StoryPage = StorySpread;

export interface QualityJudgment {
  overall_score: number;
  verdict: string;
  engagement_score: number;
  read_aloud_score: number;
  emotional_truth_score: number;
  coherence_score: number;
  chekhov_score: number;
  has_critical_failures: boolean;
  specific_problems: string;
}

export interface StoryProgress {
  stage: 'outline' | 'spreads' | 'quality' | 'character_refs' | 'illustrations' | 'failed';
  stage_detail: string;
  percentage: number;
  characters_total?: number;
  characters_completed?: number;
  spreads_total?: number;
  spreads_completed?: number;
  quality_attempt?: number;
  quality_attempts_max?: number;
  quality_score?: number;
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
  judgment?: QualityJudgment;
  is_illustrated: boolean;
  error_message?: string;
  progress?: StoryProgress;

  // Backwards compatibility (API returns both for now)
  page_count?: number;
  pages?: StoryPage[];
}

export interface StoryListResponse {
  stories: Story[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateStoryRequest {
  goal: string;
  target_age_range?: string;
  generation_type?: GenerationType;
  quality_threshold?: number;
  max_attempts?: number;
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

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
  getSpreadImageUrl: (storyId: string, spreadNumber: number): string => {
    return `${API_BASE_URL}/stories/${storyId}/spreads/${spreadNumber}/image`;
  },

  // Get page image URL (backwards compatibility - redirects to spread)
  getPageImageUrl: (storyId: string, pageNumber: number): string => {
    return `${API_BASE_URL}/stories/${storyId}/pages/${pageNumber}/image`;
  },

  // Get character reference image URL
  getCharacterImageUrl: (storyId: string, characterName: string): string => {
    return `${API_BASE_URL}/stories/${storyId}/characters/${encodeURIComponent(characterName)}/image`;
  },

  // Get story recommendations
  getRecommendations: async (storyId: string, limit: number = 4): Promise<RecommendationsResponse> => {
    return fetchApi(`/stories/${storyId}/recommendations?limit=${limit}`);
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    return fetchApi('/health');
  },
};
