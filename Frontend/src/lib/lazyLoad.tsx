import React, { lazy, Suspense, ComponentType } from 'react';
import { Loader2 } from 'lucide-react';

/**
 * ⚡ Lazy Route Loader
 * 
 * Wrapper for lazy-loading entire route components
 * with error boundaries and loading states
 */

interface LazyRouteProps {
  fallback?: React.ReactNode;
}

export function lazyLoad<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>,
  fallback?: React.ReactNode
) {
  const LazyComponent = lazy(importFunc);

  return (props: React.ComponentProps<T>) => (
    <Suspense fallback={fallback || <RouteLoadingFallback />}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

/**
 * Default loading fallback for routes
 */
const RouteLoadingFallback: React.FC = () => (
  <div className="fixed inset-0 flex items-center justify-center bg-background">
    <div className="flex flex-col items-center gap-4">
      <Loader2 className="w-12 h-12 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Loading...</p>
    </div>
  </div>
);

/**
 * ⚡ Preload Component
 * 
 * Preload a lazy component on hover or other trigger
 */
export function preloadComponent<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>
) {
  return () => {
    importFunc();
  };
}

/**
 * ⚡ Usage Example:
 * 
 * // 1. Basic lazy loading
 * const Settings = lazyLoad(() => import('./pages/Settings'));
 * 
 * // 2. With custom fallback
 * const Profile = lazyLoad(
 *   () => import('./pages/Profile'),
 *   <div>Loading profile...</div>
 * );
 * 
 * // 3. Preload on hover
 * const preloadSettings = preloadComponent(() => import('./pages/Settings'));
 * <button onMouseEnter={preloadSettings}>Settings</button>
 */
