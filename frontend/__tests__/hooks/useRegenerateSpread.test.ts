/**
 * Unit tests for useRegenerateSpread React Query mutation hook
 */
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useRegenerateSpread, storyKeys } from '../../features/stories/hooks';
import { api, Story, StorySpread } from '../../lib/api';

// Mock the api module
jest.mock('../../lib/api', () => ({
  api: {
    regenerateSpread: jest.fn(),
    getStory: jest.fn(),
  },
}));

// Mock the StoryCacheManager
const mockInvalidateStory = jest.fn().mockResolvedValue(undefined);
jest.mock('../../lib/story-cache', () => ({
  StoryCacheManager: {
    invalidateStory: (...args: unknown[]) => mockInvalidateStory(...args),
  },
}));

const mockedApi = api as jest.Mocked<typeof api>;

// Helper to create a test story
function createMockStory(overrides: Partial<Story> = {}): Story {
  return {
    id: 'test-story-id',
    status: 'completed',
    goal: 'Test story',
    target_age_range: '4-7',
    generation_type: 'illustrated',
    is_illustrated: true,
    spreads: [
      { spread_number: 1, text: 'Spread 1', word_count: 30, was_revised: false },
      { spread_number: 2, text: 'Spread 2', word_count: 35, was_revised: false },
      { spread_number: 3, text: 'Spread 3', word_count: 40, was_revised: false },
    ] as StorySpread[],
    ...overrides,
  };
}

// Helper to create wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return {
    queryClient,
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: queryClient }, children),
  };
}

describe('useRegenerateSpread', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('mutation call', () => {
    it('calls api.regenerateSpread with correct params', async () => {
      const { queryClient, wrapper } = createWrapper();
      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 3,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 3,
        });
      });

      expect(mockedApi.regenerateSpread).toHaveBeenCalledWith(
        'test-story-id',
        3,
        undefined
      );
    });

    it('passes custom prompt to api when provided', async () => {
      const { queryClient, wrapper } = createWrapper();
      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 3,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 3,
          prompt: 'Custom illustration prompt',
        });
      });

      expect(mockedApi.regenerateSpread).toHaveBeenCalledWith(
        'test-story-id',
        3,
        'Custom illustration prompt'
      );
    });

    it('returns job_id on success', async () => {
      const { wrapper } = createWrapper();
      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-xyz',
        story_id: 'test-story-id',
        spread_number: 3,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      let response;
      await act(async () => {
        response = await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 3,
        });
      });

      expect(response).toEqual({
        job_id: 'job-xyz',
        story_id: 'test-story-id',
        spread_number: 3,
        status: 'pending',
        message: 'Regeneration started',
      });
    });
  });

  describe('optimistic updates', () => {
    it('marks spread as regenerating before API returns', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      // Pre-populate cache with story data
      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      // Make API slow so we can check intermediate state
      let resolveApi: (value: any) => void;
      mockedApi.regenerateSpread.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveApi = resolve;
          })
      );

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      // Start mutation but don't await
      act(() => {
        result.current.mutate({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      // Check optimistic update immediately
      await waitFor(() => {
        const cachedStory = queryClient.getQueryData<Story>(
          storyKeys.detail('test-story-id')
        );
        const spread = cachedStory?.spreads?.find((s) => s.spread_number === 2);
        expect((spread as any)?._regenerating).toBe(true);
      });

      // Resolve the API call
      await act(async () => {
        resolveApi!({
          job_id: 'job-123',
          story_id: 'test-story-id',
          spread_number: 2,
          status: 'pending',
          message: 'Regeneration started',
        });
      });
    });

    it('only marks the target spread as regenerating', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 2,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        result.current.mutate({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      // Wait for mutation to start
      await waitFor(() => {
        const cachedStory = queryClient.getQueryData<Story>(
          storyKeys.detail('test-story-id')
        );
        // Spread 1 should NOT be regenerating
        const spread1 = cachedStory?.spreads?.find((s) => s.spread_number === 1);
        expect((spread1 as any)?._regenerating).toBeUndefined();
        // Spread 3 should NOT be regenerating
        const spread3 = cachedStory?.spreads?.find((s) => s.spread_number === 3);
        expect((spread3 as any)?._regenerating).toBeUndefined();
      });
    });

    it('cancels inflight queries to prevent race conditions', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      const cancelQueriesSpy = jest.spyOn(queryClient, 'cancelQueries');

      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 2,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      expect(cancelQueriesSpy).toHaveBeenCalledWith({
        queryKey: storyKeys.detail('test-story-id'),
      });
    });
  });

  describe('success handling', () => {
    beforeEach(() => {
      mockInvalidateStory.mockClear();
    });

    it('invalidates story cache on success', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      const invalidateQueriesSpy = jest.spyOn(queryClient, 'invalidateQueries');

      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 2,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: storyKeys.detail('test-story-id'),
      });
    });

    it('invalidates offline story cache on success', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      mockedApi.regenerateSpread.mockResolvedValue({
        job_id: 'job-123',
        story_id: 'test-story-id',
        spread_number: 2,
        status: 'pending',
        message: 'Regeneration started',
      });

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      // Should invalidate the offline cache so fresh network data is used
      expect(mockInvalidateStory).toHaveBeenCalledWith('test-story-id');
    });
  });

  describe('error handling', () => {
    it('restores previous state on error', async () => {
      const { queryClient, wrapper } = createWrapper();
      const mockStory = createMockStory();

      queryClient.setQueryData(storyKeys.detail('test-story-id'), mockStory);

      mockedApi.regenerateSpread.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        try {
          await result.current.mutateAsync({
            storyId: 'test-story-id',
            spreadNumber: 2,
          });
        } catch {
          // Expected error
        }
      });

      // Cache should be restored to original state
      const cachedStory = queryClient.getQueryData<Story>(
        storyKeys.detail('test-story-id')
      );
      const spread = cachedStory?.spreads?.find((s) => s.spread_number === 2);
      expect((spread as any)?._regenerating).toBeUndefined();
    });

    it('sets isError to true on failure', async () => {
      const { wrapper } = createWrapper();

      mockedApi.regenerateSpread.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      await act(async () => {
        try {
          await result.current.mutateAsync({
            storyId: 'test-story-id',
            spreadNumber: 2,
          });
        } catch {
          // Expected error
        }
      });

      // Wait for error state to propagate
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });
      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe('loading states', () => {
    it('isPending is true while mutation is in progress', async () => {
      const { wrapper } = createWrapper();

      let resolveApi: (value: any) => void;
      mockedApi.regenerateSpread.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveApi = resolve;
          })
      );

      const { result } = renderHook(() => useRegenerateSpread(), { wrapper });

      expect(result.current.isPending).toBe(false);

      act(() => {
        result.current.mutate({
          storyId: 'test-story-id',
          spreadNumber: 2,
        });
      });

      await waitFor(() => {
        expect(result.current.isPending).toBe(true);
      });

      await act(async () => {
        resolveApi!({
          job_id: 'job-123',
          story_id: 'test-story-id',
          spread_number: 2,
          status: 'pending',
          message: 'Regeneration started',
        });
      });

      await waitFor(() => {
        expect(result.current.isPending).toBe(false);
      });
    });
  });
});
