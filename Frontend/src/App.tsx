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
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import Contact from "./pages/Contact";

// ⚡ LAZY: Load on-demand (non-blocking)
const Chat = lazyLoad(() => import("./pages/Chat"));
const Profile = lazyLoad(() => import("./pages/Profile"));
const NotFound = lazyLoad(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

// Guard for Admin Routes
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
    const { user, isAdmin, authLoading } = useAuthStore();
    
    // While loading, show nothing or spinner. 
    // Usually authStore.checkAuth() runs on mount if authLoading is true.
    if (authLoading) return <div className="h-screen w-full flex items-center justify-center bg-zinc-950 text-white">Loading Security Protocols...</div>;
    
    if (!user || !isAdmin) {
        return <Auth />; // Redirect to normal login or show 403
    }
    return <>{children}</>;
};

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
    path: "/contact",
    element: <PublicRoute><Contact /></PublicRoute>
  },
  {
    path: "/admin",
    element: <AdminRoute><AdminDashboard /></AdminRoute>
  },
  {
    path: "/admin/login",
    element: <AdminLogin /> 
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
    // Run once on mount
    checkAuth();
  }, [checkAuth]);

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
