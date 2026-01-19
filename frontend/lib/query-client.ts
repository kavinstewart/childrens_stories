import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data stays fresh for 60 seconds before refetching
      staleTime: 60_000,
    },
  },
});
