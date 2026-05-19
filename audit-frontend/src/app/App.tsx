import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";
import { Toaster } from "sonner";
import { router } from "./routes";
import { AuthProvider } from "./store/audit-auth";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30000, gcTime: 300000, refetchOnWindowFocus: false } },
});

export function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster position="top-center" richColors />
      </AuthProvider>
    </QueryClientProvider>
  );
}
