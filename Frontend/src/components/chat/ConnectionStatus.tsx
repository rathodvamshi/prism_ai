import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { healthAPI } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
  className?: string;
}

/**
 * Connection Status Component
 * Monitors backend connectivity and displays status
 */
export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ className }) => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const [lastCheck, setLastCheck] = useState<Date>(new Date());

  const checkConnection = async () => {
    setStatus('checking');
    try {
      const response = await healthAPI.check();
      setStatus(response.status === 200 ? 'connected' : 'disconnected');
      setLastCheck(new Date());
    } catch (error) {
      setStatus('disconnected');
      setLastCheck(new Date());
    }
  };

  useEffect(() => {
    // Initial check
    checkConnection();

    // Check every 30 seconds
    const interval = setInterval(checkConnection, 30000);

    return () => clearInterval(interval);
  }, []);

  if (status === 'connected') {
    return null; // Don't show anything when connected
  }

  return (
    <div
      className={cn(
        'fixed bottom-4 left-4 z-50 flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg',
        status === 'disconnected' && 'bg-destructive text-destructive-foreground',
        status === 'checking' && 'bg-muted text-muted-foreground',
        className
      )}
    >
      {status === 'checking' && <Loader2 className="h-4 w-4 animate-spin" />}
      {status === 'disconnected' && <WifiOff className="h-4 w-4" />}
      
      <span className="text-sm font-medium">
        {status === 'checking' && 'Checking connection...'}
        {status === 'disconnected' && 'Backend disconnected'}
      </span>

      {status === 'disconnected' && (
        <button
          onClick={checkConnection}
          className="text-xs underline hover:no-underline"
        >
          Retry
        </button>
      )}
    </div>
  );
};

/**
 * Inline Connection Indicator (for header/status bar)
 */
export const ConnectionIndicator: React.FC = () => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');

  const checkConnection = async () => {
    try {
      const response = await healthAPI.check();
      setStatus(response.status === 200 ? 'connected' : 'disconnected');
    } catch {
      setStatus('disconnected');
    }
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'h-2 w-2 rounded-full',
          status === 'connected' && 'bg-green-500',
          status === 'disconnected' && 'bg-red-500',
          status === 'checking' && 'bg-yellow-500 animate-pulse'
        )}
      />
      <span className="text-xs text-muted-foreground">
        {status === 'connected' && 'Connected'}
        {status === 'disconnected' && 'Offline'}
        {status === 'checking' && 'Connecting...'}
      </span>
    </div>
  );
};
