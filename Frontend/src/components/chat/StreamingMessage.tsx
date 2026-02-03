import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { MessageBlockParser } from "@/lib/messageBlockParser";
import { MessageBlockRenderer } from "./MessageBlockRenderer";
import { ThinkingDots } from "./ThinkingDots";
import { filterMetadata } from "@/lib/streamUtils";

interface StreamingMessageProps {
  content: string;
  isStreaming: boolean;
  isThinking: boolean;
  className?: string;
}

/**
 * 🚀 GPT-Style Streaming Message Component
 * 
 * Architecture:
 * - Single renderer (MessageBlockRenderer) for BOTH streaming & completed states
 * - NO visual jump when streaming ends - identical rendering pipeline
 * - Cursor only shown during active streaming
 * 
 * Flow:
 * 1. Content → filterMetadata (remove internal markers)
 * 2. Filtered → MessageBlockParser.parseStreaming (structured blocks)
 * 3. Blocks → MessageBlockRenderer (consistent UI)
 * 4. Streaming? → Add blinking cursor
 */
export const StreamingMessage = memo(({
  content,
  isStreaming,
  isThinking,
  className = "",
}: StreamingMessageProps) => {
  // Parse content into blocks - same pipeline for streaming & completed
  const parsedContent = useMemo(() => {
    if (isThinking || !content) return null;
    const cleanContent = filterMetadata(content);
    const { blocks } = MessageBlockParser.parseStreaming(cleanContent);
    return blocks;
  }, [content, isThinking]);

  // Thinking state - show animated dots while waiting for first token
  if (isThinking || (isStreaming && !content)) {
    return <ThinkingDots />;
  }

  // Fallback for empty/unparseable content
  if (!parsedContent || parsedContent.length === 0) {
    return (
      <div className={`ai-message prose prose-sm dark:prose-invert max-w-none ${className}`}>
        <p className="text-foreground leading-relaxed">{filterMetadata(content)}</p>
      </div>
    );
  }

  // 🎯 UNIFIED RENDERING: Same renderer for streaming & completed
  return (
    <div className={`ai-message prose prose-sm dark:prose-invert max-w-none ${className}`}>
      <MessageBlockRenderer 
        blocks={parsedContent} 
        isStreaming={isStreaming}
      />
      {/* Blinking cursor - ChatGPT style */}
      {isStreaming && (
        <motion.span 
          className="inline-block w-[2.5px] h-[1.1em] ml-0.5 rounded-[1px] bg-primary/90"
          style={{ verticalAlign: 'text-bottom', marginBottom: '1px' }}
          initial={{ opacity: 1 }}
          animate={{ opacity: [1, 0.2, 1] }}
          transition={{ 
            duration: 0.8,
            repeat: Infinity,
            ease: [0.4, 0, 0.6, 1] // Smooth ease-in-out
          }}
        />
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Optimized memo comparison
  // During streaming: only re-render when content changes
  if (prevProps.isStreaming && nextProps.isStreaming) {
    return prevProps.content === nextProps.content;
  }
  // Otherwise: check all props
  return (
    prevProps.content === nextProps.content &&
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.isThinking === nextProps.isThinking
  );
});

StreamingMessage.displayName = "StreamingMessage";
