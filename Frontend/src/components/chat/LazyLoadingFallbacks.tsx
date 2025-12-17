import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * 🎯 Loading Fallbacks for Lazy-Loaded Components
 * - Shown while component bundle is being loaded
 * - Prevents layout shift with proper sizing
 * - Matches component dimensions
 */

export const PanelLoadingFallback: React.FC = () => (
  <div className="h-full w-full flex items-center justify-center bg-background/50 backdrop-blur-sm">
    <div className="flex flex-col items-center gap-2">
      <Loader2 className="w-6 h-6 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Loading...</p>
    </div>
  </div>
);

export const ModalLoadingFallback: React.FC = () => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
    <div className="flex flex-col items-center gap-3">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Loading...</p>
    </div>
  </div>
);

export const InlineLoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center p-4">
    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
  </div>
);

export const CommandPaletteLoadingFallback: React.FC = () => (
  <div className="fixed inset-0 z-50 flex items-center justify-center">
    <div className="w-full max-w-lg mx-4 bg-background rounded-lg border shadow-lg p-4 flex items-center justify-center">
      <Loader2 className="w-6 h-6 animate-spin text-primary" />
    </div>
  </div>
);
