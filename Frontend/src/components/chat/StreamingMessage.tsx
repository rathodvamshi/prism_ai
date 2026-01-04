import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { MessageBlockParser } from "@/lib/messageBlockParser";
import { MessageBlockRenderer } from "./MessageBlockRenderer";

interface StreamingMessageProps {
  content: string;
  isStreaming: boolean;
  isThinking: boolean;
  className?: string;
}

/**
 * GPT-Style Streaming Message Component
 * 
 * Key Principles:
 * 1. NO re-rendering on every chunk (stable component)
 * 2. Content passed directly from store (append-only)
 * 3. Layout stability (no flickering/jumping)
 * 4. Smooth cursor animation during streaming
 * 5. Clean thinking state with animated dots
 */
export const StreamingMessage = memo(({
  content,
  isStreaming,
  isThinking,
  className = "",
}: StreamingMessageProps) => {

  // Thinking State - Before first chunk
  if (isThinking) {
    return null;
  }

  // Parse content into structured blocks for streaming
  const { blocks, partialBlock } = useMemo(() => {
    if (!content) {
      return { blocks: [], partialBlock: undefined };
    }
    return MessageBlockParser.parseStreaming(content);
  }, [content]);

  // GPT-Style Content Rendering with structured blocks
  // Content comes pre-appended from store (no internal buffering)
  return (
    <div className={className}>
      <MessageBlockRenderer
        blocks={blocks}
        isStreaming={isStreaming}
      />

      {/* Render partial block if streaming */}
      {isStreaming && partialBlock && (
        <div className="mt-2">
          {partialBlock.type === "code" && (
            <div className="my-3 sm:my-4">
              <div className="bg-muted rounded-lg p-4 border border-border">
                <div className="text-xs text-muted-foreground mb-2 font-mono">
                  {partialBlock.language || "text"}
                </div>
                <pre className="text-sm font-mono overflow-x-auto">
                  <code>{partialBlock.content}</code>
                </pre>
              </div>
            </div>
          )}
          {partialBlock.type === "text" && (
            <p className="mb-2 sm:mb-3 leading-6 sm:leading-7 text-[14px] sm:text-[15px] text-foreground">
              {partialBlock.content}
            </p>
          )}
          {partialBlock.type === "heading" && (
            <h2 className="text-lg sm:text-xl font-bold mb-2 sm:mb-3 mt-3 sm:mt-5 text-foreground">
              {partialBlock.content}
            </h2>
          )}
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for memo - only re-render when actually needed
  // This prevents unnecessary re-renders during streaming
  return (
    prevProps.content === nextProps.content &&
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.isThinking === nextProps.isThinking
  );
});

StreamingMessage.displayName = "StreamingMessage";
