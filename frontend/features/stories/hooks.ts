import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Story, CreateStoryRequest, JobStatus, RegenerateSpreadResponse } from '@/lib/api';

// Query keys
export const storyKeys = {
  all: ['stories'] as const,
  lists: () => [...storyKeys.all, 'list'] as const,
  list: (filters: { status?: JobStatus }) => [...storyKeys.lists(), filters] as const,
  details: () => [...storyKeys.all, 'detail'] as const,
  detail: (id: string) => [...storyKeys.details(), id] as const,
  recommendations: (id: string) => [...storyKeys.all, 'recommendations', id] as const,
};

// Hook to fetch all stories
export function useStories(status?: JobStatus) {
  return useQuery({
    queryKey: storyKeys.list({ status }),
    queryFn: () => api.listStories({ status, limit: 100 }),
    select: (data) => data.stories,
  });
}

// Hook to fetch a single story
export function useStory(id: string | undefined) {
  return useQuery({
    queryKey: storyKeys.detail(id!),
    queryFn: () => api.getStory(id!),
    enabled: !!id,
  });
}

// Hook to poll a story while it's generating
export function useStoryPolling(id: string | undefined) {
  return useQuery({
    queryKey: storyKeys.detail(id!),
    queryFn: () => api.getStory(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const story = query.state.data as Story | undefined;
      // Poll every 2 seconds while pending/running
      if (story?.status === 'pending' || story?.status === 'running') {
        return 2000;
      }
      // Stop polling when completed or failed
      return false;
    },
  });
}

// Hook to create a new story
export function useCreateStory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateStoryRequest) => api.createStory(request),
    onSuccess: () => {
      // Invalidate story lists to refetch
      queryClient.invalidateQueries({ queryKey: storyKeys.lists() });
    },
  });
}

// Hook to delete a story
export function useDeleteStory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteStory(id),
    onSuccess: (_, id) => {
      // Remove from cache and invalidate lists
      queryClient.removeQueries({ queryKey: storyKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: storyKeys.lists() });
    },
  });
}

// Hook to fetch story recommendations
export function useRecommendations(storyId: string | undefined, limit: number = 4) {
  return useQuery({
    queryKey: storyKeys.recommendations(storyId!),
    queryFn: () => api.getRecommendations(storyId!, limit),
    enabled: !!storyId,
    select: (data) => data.recommendations,
  });
}

// Hook to regenerate a spread illustration
export function useRegenerateSpread() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      storyId,
      spreadNumber,
      prompt,
    }: {
      storyId: string;
      spreadNumber: number;
      prompt?: string;
    }) => api.regenerateSpread(storyId, spreadNumber, prompt),

    // Optimistic update: mark spread as regenerating
    onMutate: async ({ storyId, spreadNumber }) => {
      // Cancel any outgoing queries to prevent race conditions
      await queryClient.cancelQueries({
        queryKey: storyKeys.detail(storyId),
      });

      // Snapshot previous value
      const previousStory = queryClient.getQueryData<Story>(
        storyKeys.detail(storyId)
      );

      // Optimistically update the story to mark spread as regenerating
      if (previousStory) {
        queryClient.setQueryData<Story>(storyKeys.detail(storyId), {
          ...previousStory,
          spreads: previousStory.spreads?.map((s) =>
            s.spread_number === spreadNumber
              ? { ...s, _regenerating: true } as typeof s & { _regenerating: boolean }
              : s
          ),
        });
      }

      return { previousStory, storyId };
    },

    // On success, invalidate to get fresh data with new timestamp
    onSuccess: (_, { storyId }) => {
      queryClient.invalidateQueries({
        queryKey: storyKeys.detail(storyId),
      });
    },

    // On error, restore previous state
    onError: (_, __, context) => {
      if (context?.previousStory) {
        queryClient.setQueryData(
          storyKeys.detail(context.storyId),
          context.previousStory
        );
      }
    },
  });
}
