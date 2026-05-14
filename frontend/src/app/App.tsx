import { RouterProvider } from 'react-router';
import { Toaster } from 'sonner';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './store/auth';
import { router } from './routes';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s before data is considered stale
      gcTime: 5 * 60_000,      // 5min garbage collection (cache retention)
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Toaster position="top-center" richColors />
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
