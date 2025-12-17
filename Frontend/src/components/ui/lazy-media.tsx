import React, { useState, useEffect } from 'react';
import { Loader2, ImageOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  fallback?: React.ReactNode;
  aspectRatio?: string;
  className?: string;
}

/**
 * ⚡ LazyImage - High-Performance Image Loading
 * 
 * Features:
 * - Native lazy loading (browser-level)
 * - Loading state with skeleton
 * - Error fallback
 * - Fade-in animation on load
 * - Proper aspect ratio preservation
 */
export const LazyImage: React.FC<LazyImageProps> = ({
  src,
  alt,
  fallback,
  aspectRatio = '16/9',
  className,
  ...props
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
  }, [src]);

  const handleLoad = () => {
    setLoading(false);
  };

  const handleError = () => {
    setLoading(false);
    setError(true);
  };

  return (
    <div 
      className={cn("relative overflow-hidden bg-muted", className)}
      style={{ aspectRatio }}
    >
      {/* Loading State */}
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-muted-foreground">
          {fallback || (
            <>
              <ImageOff className="w-8 h-8" />
              <p className="text-xs">Failed to load image</p>
            </>
          )}
        </div>
      )}

      {/* Image */}
      {!error && (
        <img
          src={src}
          alt={alt}
          loading="lazy" // Native lazy loading
          decoding="async" // Async decoding for performance
          onLoad={handleLoad}
          onError={handleError}
          className={cn(
            "w-full h-full object-cover transition-opacity duration-300",
            loading ? "opacity-0" : "opacity-100"
          )}
          {...props}
        />
      )}
    </div>
  );
};

interface LazyAvatarProps {
  src?: string | null;
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

/**
 * ⚡ LazyAvatar - Optimized Avatar Component
 * 
 * Features:
 * - Lazy loading with fallback
 * - Initials fallback
 * - Multiple sizes
 */
export const LazyAvatar: React.FC<LazyAvatarProps> = ({
  src,
  name,
  size = 'md',
  className
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-lg'
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  useEffect(() => {
    if (src) {
      setLoading(true);
      setError(false);
    } else {
      setLoading(false);
      setError(true);
    }
  }, [src]);

  if (!src || error) {
    // Fallback to initials
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-full bg-primary/10 text-primary font-semibold',
          sizeClasses[size],
          className
        )}
      >
        {getInitials(name)}
      </div>
    );
  }

  return (
    <div className={cn('relative rounded-full overflow-hidden', sizeClasses[size], className)}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
      )}
      <img
        src={src}
        alt={name}
        loading="lazy"
        decoding="async"
        onLoad={() => setLoading(false)}
        onError={() => {
          setLoading(false);
          setError(true);
        }}
        className={cn(
          'w-full h-full object-cover transition-opacity duration-300',
          loading ? 'opacity-0' : 'opacity-100'
        )}
      />
    </div>
  );
};

/**
 * ⚡ LazyIcon - Lazy-loaded SVG Icons
 * 
 * Use for large icon libraries or custom SVGs
 */
interface LazyIconProps {
  iconPath: string; // Path to SVG file
  className?: string;
  size?: number;
}

export const LazyIcon: React.FC<LazyIconProps> = ({
  iconPath,
  className,
  size = 24
}) => {
  const [Icon, setIcon] = useState<React.FC | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import(/* @vite-ignore */ iconPath)
      .then((module) => {
        setIcon(() => module.default);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [iconPath]);

  if (loading) {
    return (
      <div
        className={cn('animate-pulse bg-muted rounded', className)}
        style={{ width: size, height: size }}
      />
    );
  }

  if (!Icon) return null;

  const IconComponent = Icon as any;
  return <IconComponent className={className} />;
};
