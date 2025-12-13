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

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, checkAuth } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (!isAuthenticated) {
    // Redirect to auth page with return url
    return <Navigate to={`/auth?mode=login&from=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
};

/**
 * Public Route Component
 * Redirects to chat if user is already authenticated
 */
export const PublicRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isAuthenticated) {
    // Redirect to chat if already logged in
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
};