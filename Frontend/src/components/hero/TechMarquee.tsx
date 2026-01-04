import React, { useEffect, useRef, useCallback, useState } from "react";

/**
 * 🔁 INFINITE HORIZONTAL QUEUE ANIMATION
 * Circular Queue / Doubly Linked List Concept
 *
 * Mental Model:
 * [React] → [Node] → [MongoDB] → [Redis] → [Flask] → [Neo4j] → [Pinecone]
 *    ↑                                                              ↓
 *    └──────────────── circular connection ─────────────────────────┘
 *
 * When an icon fully exits the viewport:
 * 1. Remove it from the front
 * 2. Append it to the end
 * 3. Maintain order
 * 4. Continue animation seamlessly
 *
 * This is true infinite flow, not fake looping.
 */

type IconProps = { className?: string };

// ─────────────────────────────────────────────────────────────────────────────
// COLORFUL SVG ICONS (Enterprise-grade, gradient fills)
// ─────────────────────────────────────────────────────────────────────────────

const ReactIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="React" role="img">
    <defs>
      <radialGradient id="reactGrad" cx="50%" cy="50%" r="60%">
        <stop offset="0%" stopColor="#9EE8FF" />
        <stop offset="100%" stopColor="#61DAFB" />
      </radialGradient>
    </defs>
    <circle cx="128" cy="128" r="22" fill="url(#reactGrad)" />
    <g fill="none" stroke="#61DAFB" strokeWidth="12">
      <ellipse cx="128" cy="128" rx="84" ry="34" />
      <ellipse cx="128" cy="128" rx="84" ry="34" transform="rotate(60 128 128)" />
      <ellipse cx="128" cy="128" rx="84" ry="34" transform="rotate(120 128 128)" />
    </g>
  </svg>
);

const NodeIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="Node.js" role="img">
    <defs>
      <linearGradient id="nodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#78C257" />
        <stop offset="100%" stopColor="#3C873A" />
      </linearGradient>
    </defs>
    <path d="M128 24l96 56v96l-96 56-96-56V80z" fill="url(#nodeGrad)" />
    <path d="M128 24l96 56v96l-96 56-96-56V80z" fill="none" stroke="#2D6A2E" strokeWidth="10" />
  </svg>
);

const MongoIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="MongoDB" role="img">
    <defs>
      <linearGradient id="mongoGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#7FCB68" />
        <stop offset="100%" stopColor="#47A248" />
      </linearGradient>
    </defs>
    <path d="M128 28s24 44 24 84-24 84-24 84-24-44-24-84 24-84 24-84z" fill="url(#mongoGrad)" />
    <path d="M128 28s24 44 24 84-24 84-24 84-24-44-24-84 24-84 24-84z" fill="none" stroke="#2E6F3E" strokeWidth="8" />
  </svg>
);

const RedisIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="Redis" role="img">
    <defs>
      <linearGradient id="redisGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#FF6B6B" />
        <stop offset="100%" stopColor="#D82C20" />
      </linearGradient>
    </defs>
    <rect x="40" y="60" width="176" height="40" rx="8" fill="url(#redisGrad)" />
    <rect x="48" y="108" width="160" height="40" rx="8" fill="url(#redisGrad)" />
    <rect x="56" y="156" width="144" height="40" rx="8" fill="url(#redisGrad)" />
  </svg>
);

const FlaskIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="Flask" role="img">
    <defs>
      <linearGradient id="flaskGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#9DECF9" />
        <stop offset="100%" stopColor="#3BC7D4" />
      </linearGradient>
    </defs>
    <path d="M88 24h80l-40 64-40-64zm40 64c24 40 56 88 56 112 0 24-20 32-56 32s-56-8-56-32c0-24 32-72 56-112z" fill="url(#flaskGrad)" />
    <path d="M88 24h80l-40 64-40-64zm40 64c24 40 56 88 56 112 0 24-20 32-56 32s-56-8-56-32c0-24 32-72 56-112z" fill="none" stroke="#2A7E86" strokeWidth="8" />
  </svg>
);

const Neo4jIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="Neo4j" role="img">
    <defs>
      <linearGradient id="neoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#83D3F2" />
        <stop offset="100%" stopColor="#008CC1" />
      </linearGradient>
    </defs>
    <circle cx="96" cy="96" r="28" fill="url(#neoGrad)" />
    <circle cx="168" cy="60" r="20" fill="url(#neoGrad)" />
    <circle cx="176" cy="168" r="32" fill="url(#neoGrad)" />
    <line x1="110" y1="110" x2="160" y2="72" stroke="#008CC1" strokeWidth="8" />
    <line x1="110" y1="110" x2="160" y2="168" stroke="#008CC1" strokeWidth="8" />
  </svg>
);

const PineconeIcon: React.FC<IconProps> = ({ className }) => (
  <svg viewBox="0 0 256 256" className={className} aria-label="Pinecone" role="img">
    <defs>
      <linearGradient id="pineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#D3A6FF" />
        <stop offset="100%" stopColor="#8B5CF6" />
      </linearGradient>
    </defs>
    <path d="M128 24l48 48-48 48-48-48 48-48zm0 96l48 48-48 64-48-64 48-48z" fill="url(#pineGrad)" />
    <path d="M128 24l48 48-48 48-48-48 48-48zm0 96l48 48-48 64-48-64 48-48z" fill="none" stroke="#6D28D9" strokeWidth="8" />
  </svg>
);

// ─────────────────────────────────────────────────────────────────────────────
// ICON DATA (Circular Queue Nodes)
// ─────────────────────────────────────────────────────────────────────────────

interface IconItem {
  name: string;
  Icon: React.FC<IconProps>;
}

const iconItems: IconItem[] = [
  { name: "React", Icon: ReactIcon },
  { name: "Node.js", Icon: NodeIcon },
  { name: "MongoDB", Icon: MongoIcon },
  { name: "Redis", Icon: RedisIcon },
  { name: "Flask", Icon: FlaskIcon },
  { name: "Neo4j", Icon: Neo4jIcon },
  { name: "Pinecone", Icon: PineconeIcon },
];

// Duplicate icons to ensure seamless circular flow
// When one exits left, another is already visible on right
const queueItems: IconItem[] = [...iconItems, ...iconItems];

// ─────────────────────────────────────────────────────────────────────────────
// CIRCULAR QUEUE MARQUEE COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

interface TechMarqueeProps {
  variant?: "background" | "inline";
}

export const TechMarquee: React.FC<TechMarqueeProps> = ({ variant = "inline" }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const posRef = useRef(0);
  const rafRef = useRef<number>();
  const lastTimeRef = useRef<number>(0);
  const isPausedRef = useRef(false);
  const hoveredRef = useRef<HTMLElement | null>(null);
  
  // Tooltip state for click-to-learn
  const [tooltip, setTooltip] = useState<{ name: string; x: number; y: number } | null>(null);
  
  // User pause control
  const [userPaused, setUserPaused] = useState(false);

  // Speed: px per second (responsive - slower on mobile)
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 640;
  const SPEED = isMobile ? 35 : 50;

  // ───────────────────────────────────────────────────────────────────────────
  // QUEUE ROTATION LOGIC (Circular Doubly Linked List)
  // When the first icon fully exits the viewport (left edge):
  // 1. Remove it from the start
  // 2. Append it to the end
  // 3. Reset translate position by that icon's width + gap
  // 4. Continue movement seamlessly — no jump, no reset
  // ───────────────────────────────────────────────────────────────────────────
  const rotateQueue = useCallback(() => {
    const track = trackRef.current;
    if (!track) return;

    const first = track.firstElementChild as HTMLElement | null;
    if (!first) return;

    const gap = parseFloat(getComputedStyle(track).gap) || 0;
    const threshold = first.offsetWidth + gap;

    if (posRef.current >= threshold) {
      // Remove from front, append to end (circular queue rotation)
      track.appendChild(first);
      // Adjust position to prevent visual jump
      posRef.current -= threshold;
      track.style.transform = `translate3d(${-posRef.current}px, 0, 0)`;
    }
  }, []);

  // ───────────────────────────────────────────────────────────────────────────
  // CENTER DETECTION - Auto blink when icon reaches middle
  // ───────────────────────────────────────────────────────────────────────────
  const detectCenter = useCallback(() => {
    const container = containerRef.current;
    const track = trackRef.current;
    if (!container || !track) return;

    const containerRect = container.getBoundingClientRect();
    const centerX = containerRect.left + containerRect.width / 2;

    const icons = track.querySelectorAll('.queue-icon');
    icons.forEach((icon) => {
      const iconRect = icon.getBoundingClientRect();
      const iconCenterX = iconRect.left + iconRect.width / 2;
      const distance = Math.abs(centerX - iconCenterX);

      // If icon is within 40px of center, add blink class
      if (distance < 40) {
        if (!icon.classList.contains('is-center')) {
          icon.classList.add('is-center');
        }
      } else {
        icon.classList.remove('is-center');
      }
    });
  }, []);

  // ───────────────────────────────────────────────────────────────────────────
  // ANIMATION LOOP (requestAnimationFrame for precise control)
  // ───────────────────────────────────────────────────────────────────────────
  const animate = useCallback(
    (now: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = now;
      const dt = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;

      const track = trackRef.current;
      if (!track) {
        rafRef.current = requestAnimationFrame(animate);
        return;
      }

      // Only move if not paused
      if (!isPausedRef.current) {
        posRef.current += SPEED * dt;
        track.style.transform = `translate3d(${-posRef.current}px, 0, 0)`;
        rotateQueue();
      }

      // Detect center icon for auto blink
      detectCenter();

      rafRef.current = requestAnimationFrame(animate);
    },
    [rotateQueue, detectCenter]
  );

  // ───────────────────────────────────────────────────────────────────────────
  // HOVER HANDLERS
  // On hover: pause entire animation, scale hovered icon (1.15–1.25)
  // On hover out: resume from same position, smooth continuation
  // ───────────────────────────────────────────────────────────────────────────
  const handleMouseEnter = useCallback((e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(".queue-icon") as HTMLElement | null;
    if (target) {
      isPausedRef.current = true;
      hoveredRef.current = target;
      target.classList.add("is-hovered");
    }
  }, []);

  const handleMouseLeave = useCallback((e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(".queue-icon") as HTMLElement | null;
    if (target) {
      target.classList.remove("is-hovered");
    }
    // Resume animation from same position
    isPausedRef.current = userPaused;
    hoveredRef.current = null;
  }, [userPaused]);

  // Click handler for tooltip
  const handleClick = useCallback((e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(".queue-icon") as HTMLElement | null;
    if (target) {
      const label = target.querySelector('.queue-icon-label')?.textContent || '';
      const rect = target.getBoundingClientRect();
      setTooltip({ name: label, x: rect.left + rect.width / 2, y: rect.top - 10 });
      // Auto-hide after 2s
      setTimeout(() => setTooltip(null), 2000);
    }
  }, []);

  // Toggle pause
  const togglePause = useCallback(() => {
    setUserPaused(prev => {
      isPausedRef.current = !prev;
      return !prev;
    });
  }, []);

  // ───────────────────────────────────────────────────────────────────────────
  // LIFECYCLE
  // ───────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Respect prefers-reduced-motion
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    // Start animation loop
    rafRef.current = requestAnimationFrame(animate);

    // Pause on tab blur, resume on focus (performance)
    const onBlur = () => {
      isPausedRef.current = true;
    };
    const onFocus = () => {
      if (!hoveredRef.current) {
        isPausedRef.current = false;
      }
      lastTimeRef.current = 0; // Reset delta to avoid jump
    };

    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);

    // Hover event delegation
    container.addEventListener("mouseenter", handleMouseEnter, true);
    container.addEventListener("mouseleave", handleMouseLeave, true);
    container.addEventListener("click", handleClick, true);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      container.removeEventListener("mouseenter", handleMouseEnter, true);
      container.removeEventListener("mouseleave", handleMouseLeave, true);
      container.removeEventListener("click", handleClick, true);
    };
  }, [animate, handleMouseEnter, handleMouseLeave, handleClick]);

  // ───────────────────────────────────────────────────────────────────────────
  // RENDER
  // ───────────────────────────────────────────────────────────────────────────
  const isBackground = variant === "background";

  return (
    <div
      ref={containerRef}
      className={
        "queue-marquee overflow-hidden flex items-center justify-center " +
        (isBackground
          ? "pointer-events-auto absolute inset-0 z-0"
          : "relative w-full z-10 py-4 sm:py-6 md:py-8")
      }
      aria-hidden="true"
    >
      {/* Track: moving container (flex row, centered) */}
      <div
        ref={trackRef}
        className="queue-track flex items-center gap-6 sm:gap-10 md:gap-12 lg:gap-16 will-change-transform px-2 sm:px-4"
        style={{ transform: "translate3d(0, 0, 0)" }}
      >
        {queueItems.map(({ name, Icon }, i) => (
          <div
            key={`${name}-${i}`}
            className="queue-icon group flex flex-col items-center cursor-pointer"
            style={{ animationDelay: `${(i % 7) * 0.15}s` }}
          >
            <div className="queue-icon-svg w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 transition-all duration-200 ease-out">
              <Icon className="w-full h-full" />
            </div>
            <span className="queue-icon-label mt-1 sm:mt-2 text-[9px] sm:text-[10px] md:text-xs font-medium text-foreground/50 whitespace-nowrap transition-all duration-200">
              {name}
            </span>
          </div>
        ))}
      </div>

      {/* Pause/Play control button */}
      <button
        onClick={togglePause}
        className="absolute bottom-0 sm:bottom-1 right-2 sm:right-4 z-30 p-1 sm:p-1.5 rounded-full bg-transparent border-none text-foreground/40 hover:text-foreground/60 transition-all duration-200"
        aria-label={userPaused ? "Play animation" : "Pause animation"}
      >
        {userPaused ? (
          <svg className="w-2.5 h-2.5 sm:w-3 sm:h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        ) : (
          <svg className="w-2.5 h-2.5 sm:w-3 sm:h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
        )}
      </button>

      {/* Tooltip on click */}
      {tooltip && (
        <div
          className="fixed z-50 px-2 sm:px-3 py-1 sm:py-1.5 bg-foreground text-background text-[10px] sm:text-xs font-medium rounded-md sm:rounded-lg shadow-lg pointer-events-none animate-fade-in"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: 'translate(-50%, -100%)'
          }}
        >
          {tooltip.name}
          <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-foreground" />
        </div>
      )}
    </div>
  );
};

export default TechMarquee;
