/**
 * Protected Route Component
 * Redirects to auth page if user is not authenticated
 */

import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

// Loading component for auth check
const AuthLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, authLoading, checkAuth } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    if (authLoading) {
      checkAuth();
    }
  }, [checkAuth, authLoading]);

  // Show loader while checking authentication
  if (authLoading) {
    return <AuthLoader />;
  }

  // Redirect to auth page if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={`/auth?mode=login&from=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
};

/**
 * Public Route Component
 * Redirects to chat if user is already authenticated
 */
export const PublicRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, authLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    if (authLoading) {
      checkAuth();
    }
  }, [checkAuth, authLoading]);

  // Show loader while checking authentication
  if (authLoading) {
    return <AuthLoader />;
  }

  // Redirect to chat if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
};