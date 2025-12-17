import { useEffect, useRef } from 'react';

/**
 * ⚡ Performance Monitoring Hook
 * 
 * Tracks:
 * - Component mount time
 * - Render time
 * - Re-render count
 * - Memory usage (if available)
 */

interface PerformanceMetrics {
  componentName: string;
  mountTime: number;
  renderTime: number;
  reRenderCount: number;
}

export function usePerformanceMonitor(componentName: string, enabled: boolean = false) {
  const renderCount = useRef(0);
  const mountTime = useRef(0);
  const lastRenderTime = useRef(0);

  useEffect(() => {
    if (!enabled) return;

    renderCount.current += 1;
    const now = performance.now();

    if (renderCount.current === 1) {
      // First render (mount)
      mountTime.current = now;
      console.log(`⚡ [${componentName}] Mounted in ${now.toFixed(2)}ms`);
    } else {
      // Re-render
      const renderTime = now - lastRenderTime.current;
      console.log(`🔄 [${componentName}] Re-render #${renderCount.current} took ${renderTime.toFixed(2)}ms`);
    }

    lastRenderTime.current = now;

    return () => {
      if (renderCount.current === 1) {
        const totalTime = performance.now() - mountTime.current;
        console.log(`❌ [${componentName}] Unmounted after ${totalTime.toFixed(2)}ms (${renderCount.current} renders)`);
      }
    };
  });

  return {
    renderCount: renderCount.current,
    mountTime: mountTime.current
  };
}

/**
 * ⚡ Lazy Component Loader Tracker
 * 
 * Tracks when lazy components start/finish loading
 */
export function useChunkLoadTracker(componentName: string) {
  useEffect(() => {
    const startTime = performance.now();
    console.log(`📦 [${componentName}] Starting chunk load...`);

    return () => {
      const loadTime = performance.now() - startTime;
      console.log(`✅ [${componentName}] Chunk loaded in ${loadTime.toFixed(2)}ms`);
    };
  }, [componentName]);
}

/**
 * ⚡ Initial Page Load Tracker
 * 
 * Measures critical performance metrics
 */
export function usePageLoadMetrics() {
  useEffect(() => {
    // Wait for page to fully load
    if (document.readyState === 'complete') {
      logMetrics();
    } else {
      window.addEventListener('load', logMetrics);
      return () => window.removeEventListener('load', logMetrics);
    }

    function logMetrics() {
      if ('performance' in window) {
        const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        
        if (perfData) {
          const metrics = {
            'DNS Lookup': (perfData.domainLookupEnd - perfData.domainLookupStart).toFixed(2),
            'TCP Connection': (perfData.connectEnd - perfData.connectStart).toFixed(2),
            'Request Time': (perfData.responseStart - perfData.requestStart).toFixed(2),
            'Response Time': (perfData.responseEnd - perfData.responseStart).toFixed(2),
            'DOM Processing': (perfData.domComplete - (perfData as any).domLoading).toFixed(2),
            'DOM Interactive': (perfData.domInteractive - (perfData as any).domLoading).toFixed(2),
            'DOM Content Loaded': (perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart).toFixed(2),
            'Load Event': (perfData.loadEventEnd - perfData.loadEventStart).toFixed(2),
            'Total Load Time': (perfData.loadEventEnd - perfData.fetchStart).toFixed(2)
          };

          console.group('📊 Page Load Metrics');
          Object.entries(metrics).forEach(([key, value]) => {
            console.log(`${key}: ${value}ms`);
          });
          console.groupEnd();

          // Check for paint metrics
          const paintMetrics = performance.getEntriesByType('paint');
          if (paintMetrics.length > 0) {
            console.group('🎨 Paint Metrics');
            paintMetrics.forEach((entry) => {
              console.log(`${entry.name}: ${entry.startTime.toFixed(2)}ms`);
            });
            console.groupEnd();
          }
        }
      }
    }
  }, []);
}

/**
 * ⚡ Network Monitoring
 * 
 * Tracks API call performance
 */
export function useNetworkMonitor() {
  useEffect(() => {
    if (!('PerformanceObserver' in window)) return;

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'resource') {
          const resourceEntry = entry as PerformanceResourceTiming;
          
          // Only log API calls
          if (resourceEntry.name.includes('/api/') || resourceEntry.name.includes('/chat/')) {
            const duration = resourceEntry.duration.toFixed(2);
            const size = resourceEntry.transferSize || 0;
            const sizeKB = (size / 1024).toFixed(2);
            
            console.log(`🌐 API: ${resourceEntry.name.split('/').pop()} - ${duration}ms (${sizeKB}KB)`);
          }
        }
      }
    });

    observer.observe({ entryTypes: ['resource'] });

    return () => observer.disconnect();
  }, []);
}

/**
 * ⚡ Memory Monitor
 * 
 * Tracks memory usage (Chrome only)
 */
export function useMemoryMonitor(intervalMs: number = 5000) {
  useEffect(() => {
    // @ts-ignore - Chrome-specific API
    if (!('memory' in performance)) {
      console.warn('Memory monitoring not available in this browser');
      return;
    }

    const interval = setInterval(() => {
      // @ts-ignore
      const memory = performance.memory;
      const usedMB = (memory.usedJSHeapSize / 1048576).toFixed(2);
      const limitMB = (memory.jsHeapSizeLimit / 1048576).toFixed(2);
      const percent = ((memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100).toFixed(1);

      console.log(`💾 Memory: ${usedMB}MB / ${limitMB}MB (${percent}%)`);
    }, intervalMs);

    return () => clearInterval(interval);
  }, [intervalMs]);
}

/**
 * ⚡ Component Size Tracker
 * 
 * Measures component bundle size impact
 */
export function logComponentSize(componentName: string, beforeSize: number) {
  if ('performance' in window) {
    const entries = performance.getEntriesByType('resource');
    const totalSize = entries.reduce((sum, entry: any) => {
      return sum + (entry.transferSize || 0);
    }, 0);

    const addedSize = totalSize - beforeSize;
    const addedKB = (addedSize / 1024).toFixed(2);

    console.log(`📦 [${componentName}] Added ${addedKB}KB to bundle`);
  }
}
