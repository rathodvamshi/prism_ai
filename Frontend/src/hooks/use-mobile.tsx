import * as React from "react";

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.innerWidth < MOBILE_BREAKPOINT;
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const onChange = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    if (mql.addEventListener) {
      mql.addEventListener("change", onChange);
    } else {
      // Safari fallback
      // @ts-ignore
      mql.addListener(onChange);
    }
    // Sync once on mount in case of SSR hydration
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    return () => {
      if (mql.removeEventListener) {
        mql.removeEventListener("change", onChange);
      } else {
        // @ts-ignore
        mql.removeListener(onChange);
      }
    };
  }, []);

  return isMobile;
}
