import { memo } from "react";
import { motion } from "framer-motion";

/**
 * 🧠 Thinking Indicator - ChatGPT-Style
 * 
 * Professional thinking animation with:
 * - Smooth pulsing dots
 * - Gradient shimmer effect
 * - Subtle bounce animation
 */
export const ThinkingDots = memo(() => (
  <div className="flex items-center gap-2 py-3 px-1">
    {/* Animated dots container */}
    <div className="flex items-center gap-1.5">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full bg-gradient-to-br from-primary to-primary/60"
          initial={{ opacity: 0.3, scale: 0.7 }}
          animate={{
            opacity: [0.3, 1, 0.3],
            scale: [0.7, 1.1, 0.7],
            y: [0, -4, 0],
          }}
          transition={{
            duration: 1.4,
            repeat: Infinity,
            delay: i * 0.2,
            ease: [0.4, 0, 0.2, 1], // Custom easing for smoother feel
          }}
        />
      ))}
    </div>
    
    {/* Thinking text with shimmer */}
    <motion.div
      className="relative overflow-hidden"
      initial={{ opacity: 0, x: -5 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2 }}
    >
      <span className="text-sm text-muted-foreground font-medium">
        Thinking
      </span>
      {/* Shimmer overlay */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/10 to-transparent"
        animate={{ x: ["-100%", "200%"] }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      />
    </motion.div>
  </div>
));

ThinkingDots.displayName = "ThinkingDots";
