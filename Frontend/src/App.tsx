import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ProtectedRoute, PublicRoute } from "@/components/ProtectedRoute";
import Hero from "./pages/Hero";
import Auth from "./pages/Auth";
import Chat from "./pages/Chat";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

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

const App = () => (
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

export default App;
