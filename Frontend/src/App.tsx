import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ProtectedRoute, PublicRoute } from "@/components/ProtectedRoute";
import { useAuthStore } from "@/stores/authStore";
import { useChatStore } from "@/stores/chatStore";
import { useProfileStore } from "@/stores/profileStore";
import { lazyLoad } from "@/lib/lazyLoad";

// ⚡ CRITICAL: Load immediately (blocking)
import Hero from "./pages/Hero";
import Auth from "./pages/Auth";

// ⚡ LAZY: Load on-demand (non-blocking)
const Chat = lazyLoad(() => import("./pages/Chat"));
const Profile = lazyLoad(() => import("./pages/Profile"));
const Settings = lazyLoad(() => import("./pages/Settings"));
const NotFound = lazyLoad(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicRoute><Hero /></PublicRoute>
  },
  {
    path: "/auth",
    element: <PublicRoute><Auth /></PublicRoute>
  },
  {
    path: "/chat",
    element: <ProtectedRoute><Chat /></ProtectedRoute>
  },
  {
    path: "/chat/:sessionId",
    element: <ProtectedRoute><Chat /></ProtectedRoute>
  },
  {
    path: "/settings",
    element: <ProtectedRoute><Settings /></ProtectedRoute>
  },
  {
    path: "/profile",
    element: <ProtectedRoute><Profile /></ProtectedRoute>
  },
  {
    path: "*",
    element: <NotFound />
  },
]);

const App = () => {
  const { checkAuth, authLoading, isAuthenticated } = useAuthStore();
  const { loadChatsFromBackend } = useChatStore();
  const { loadProfileFromBackend } = useProfileStore();

  // Initialize auth state on app startup
  useEffect(() => {
    if (authLoading) {
      checkAuth();
    }
  }, [checkAuth, authLoading]);

  // Load user data when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadChatsFromBackend();
      loadProfileFromBackend();
    }
  }, [isAuthenticated, loadChatsFromBackend, loadProfileFromBackend]);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <RouterProvider
          router={router}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        />
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
