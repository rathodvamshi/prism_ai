import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

// Shimmer effect for skeleton loaders
export const Shimmer = () => (
  <motion.div
    className="absolute inset-0 bg-gradient-to-r from-transparent via-muted-foreground/5 to-transparent"
    animate={{
      x: ["-100%", "100%"],
    }}
    transition={{
      duration: 1.5,
      repeat: Infinity,
      ease: "linear",
    }}
  />
);

// Chat item skeleton for sidebar
export const ChatItemSkeleton = () => (
  <div className="relative overflow-hidden rounded-lg p-3 bg-sidebar-accent/30">
    <Shimmer />
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-sidebar-accent/50" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-3/4 rounded bg-sidebar-accent/50" />
        <div className="h-3 w-1/2 rounded bg-sidebar-accent/40" />
      </div>
    </div>
  </div>
);

// Message skeleton for chat area
export const MessageSkeleton = ({ isUser = false }: { isUser?: boolean }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
    className={cn(
      "flex gap-3 py-4 px-6",
      isUser ? "justify-end" : "justify-start"
    )}
  >
    {!isUser && (
      <div className="relative overflow-hidden w-8 h-8 rounded-lg bg-muted/50 shrink-0">
        <Shimmer />
      </div>
    )}
    <div className={cn(
      "relative overflow-hidden max-w-[70%] rounded-2xl p-4",
      isUser ? "bg-secondary/80" : "bg-muted/30"
    )}>
      <Shimmer />
      <div className="space-y-2">
        <div className={cn(
          "h-4 rounded",
          isUser ? "bg-muted-foreground/20 w-40" : "bg-muted-foreground/15 w-56"
        )} />
        <div className={cn(
          "h-4 rounded",
          isUser ? "bg-muted-foreground/15 w-32" : "bg-muted-foreground/10 w-48"
        )} />
        {!isUser && <div className="h-4 w-40 rounded bg-muted-foreground/10" />}
      </div>
    </div>
    {isUser && (
      <div className="relative overflow-hidden w-8 h-8 rounded-lg bg-muted/50 shrink-0">
        <Shimmer />
      </div>
    )}
  </motion.div>
);

// Conversation loading skeleton (shows 3 messages)
export const ConversationLoadingSkeleton = () => (
  <div className="space-y-4">
    <MessageSkeleton isUser={true} />
    <MessageSkeleton isUser={false} />
    <MessageSkeleton isUser={true} />
    <MessageSkeleton isUser={false} />
  </div>
);

// Chat list loading skeleton for sidebar
export const ChatListSkeleton = () => (
  <div className="space-y-2 p-2">
    {[...Array(5)].map((_, i) => (
      <ChatItemSkeleton key={i} />
    ))}
  </div>
);

// Mini agent skeleton
export const MiniAgentSkeleton = () => (
  <div className="relative overflow-hidden rounded-lg p-4 bg-accent/20 border border-border/50">
    <Shimmer />
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-accent/40" />
        <div className="h-4 w-32 rounded bg-accent/40" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-accent/30" />
        <div className="h-3 w-4/5 rounded bg-accent/25" />
      </div>
    </div>
  </div>
);

// Task skeleton
export const TaskSkeleton = () => (
  <div className="relative overflow-hidden rounded-lg p-3 bg-sidebar-accent/20">
    <Shimmer />
    <div className="flex items-center gap-3">
      <div className="w-5 h-5 rounded bg-sidebar-accent/40" />
      <div className="flex-1">
        <div className="h-4 w-3/4 rounded bg-sidebar-accent/40" />
      </div>
    </div>
  </div>
);

// Generic loading spinner
export const LoadingSpinner = ({ size = "md" }: { size?: "sm" | "md" | "lg" }) => {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 border-2",
    lg: "w-8 h-8 border-3"
  };

  return (
    <motion.div
      className={cn(
        "rounded-full border-primary/30 border-t-primary",
        sizeClasses[size]
      )}
      animate={{ rotate: 360 }}
      transition={{
        duration: 0.8,
        repeat: Infinity,
        ease: "linear"
      }}
    />
  );
};

// Typing indicator (for AI thinking)
export const TypingIndicator = () => (
  <div className="flex gap-1 items-center">
    {[0, 1, 2].map((i) => (
      <motion.div
        key={i}
        className="w-2 h-2 rounded-full bg-foreground/40"
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.4, 0.8, 0.4],
        }}
        transition={{
          duration: 1,
          repeat: Infinity,
          delay: i * 0.2,
        }}
      />
    ))}
  </div>
);

// Full page loading state
export const FullPageLoader = ({ message = "Loading..." }: { message?: string }) => (
  <div className="fixed inset-0 flex items-center justify-center bg-background/95 backdrop-blur-sm z-50">
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center gap-4"
    >
      <LoadingSpinner size="lg" />
      <p className="text-muted-foreground text-sm">{message}</p>
    </motion.div>
  </div>
);
