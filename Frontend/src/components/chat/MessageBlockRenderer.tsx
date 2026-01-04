/**
 * Message Block Renderer
 * 
 * Renders structured MessageBlock[] into clean, elegant UI
 * 
 * Principles:
 * - Clean, readable, smooth, elegant, professional
 * - No layout jumping
 * - Stable rendering
 * - Supports highlights
 */

import { memo } from "react";
import { motion } from "framer-motion";
import { MessageBlock, MessageBlocks } from "@/types/messageBlocks";
import { CodeBlock } from "./CodeBlock";
import { cn } from "@/lib/utils";
import { Highlight } from "@/types/chat";
import { detectSemanticHighlights, applySemanticHighlights } from "@/lib/semanticHighlight";

interface MessageBlockRendererProps {
  blocks: MessageBlocks;
  highlights?: Highlight[];
  isStreaming?: boolean;
  className?: string;
  customCodeRenderer?: (content: string, language: string) => React.ReactNode;
}

/**
 * Render a single text block with optional highlights
 * Applies semantic highlighting for semantic labels (Important:, ⚠️ Warning:, etc.)
 * User-created highlights are handled separately via the highlights prop
 */
const renderTextBlock = (
  content: string,
  highlights?: Highlight[],
  blockIndex?: number
): React.ReactNode => {
  // Detect semantic labels for automatic highlighting
  const semanticHighlights = detectSemanticHighlights(content);

  // Apply semantic highlights if found
  if (semanticHighlights.length > 0) {
    return <span>{applySemanticHighlights(content, semanticHighlights)}</span>;
  }

  // Fall back to user-created highlights if no semantic labels
  if (!highlights || highlights.length === 0) {
    return <span>{content}</span>;
  }

  // Sort highlights by start position
  const sortedHighlights = [...highlights].sort((a, b) => {
    if (a.startOffset !== b.startOffset) {
      return a.startOffset - b.startOffset;
    }
    return (b.endOffset - b.startOffset) - (a.endOffset - a.startOffset);
  });

  // Build highlight tree for nested highlights
  interface HighlightNode {
    start: number;
    end: number;
    color: string;
    id: string;
    children: HighlightNode[];
  }

  const buildTree = (highlights: Highlight[]): HighlightNode[] => {
    const roots: HighlightNode[] = [];
    const stack: HighlightNode[] = [];

    for (const h of highlights) {
      const node: HighlightNode = {
        start: h.startOffset,
        end: h.endOffset,
        color: h.color,
        id: h.id,
        children: [],
      };

      while (stack.length > 0 && stack[stack.length - 1].end <= node.start) {
        stack.pop();
      }

      if (stack.length === 0) {
        roots.push(node);
      } else {
        stack[stack.length - 1].children.push(node);
      }

      stack.push(node);
    }

    return roots;
  };

  const getDisplayColor = (color: string): string => {
    if (color.startsWith("#")) {
      return color;
    }

    const colorMap: Record<string, string> = {
      yellow: "#FFD93D",
      green: "#3ED174",
      blue: "#4B9CFF",
      pink: "#FBCFE8",
      orange: "#FED7AA",
      purple: "#C36BFF",
      teal: "#99F6E4",
      lime: "#D9F99D",
      rose: "#FECDD3",
      red: "#FF4B4B",
      cyan: "#A5F3FC",
      amber: "#FDE68A",
      mint: "#A7F3D0",
    };

    return colorMap[color.toLowerCase()] || "#FFD93D";
  };

  const tree = buildTree(sortedHighlights);

  const renderNode = (node: HighlightNode, textContent: string): React.ReactNode => {
    const nodeText = textContent.slice(node.start, node.end);
    const bgColor = getDisplayColor(node.color);

    if (node.children.length === 0) {
      return (
        <motion.span
          key={`${node.id}-${node.start}`}
          initial={{ backgroundColor: "rgba(0,0,0,0)" }}
          animate={{ backgroundColor: bgColor }}
          transition={{ duration: 0.4 }}
          style={{
            backgroundColor: bgColor,
            color: "#1a1a1a", // Slightly softer black
            borderBottom: "2px solid rgba(0,0,0,0.1)",
          }}
          className="rounded-[4px] px-1 py-[1px] mx-[1px] font-medium shadow-sm"
        >
          {nodeText}
        </motion.span>
      );
    }

    const parts: React.ReactNode[] = [];
    let cursor = node.start;

    for (const child of node.children) {
      if (cursor < child.start) {
        parts.push(textContent.slice(cursor, child.start));
      }
      parts.push(renderNode(child, textContent));
      cursor = child.end;
    }

    if (cursor < node.end) {
      parts.push(textContent.slice(cursor, node.end));
    }

    return (
      <motion.span
        key={`${node.id}-${node.start}`}
        initial={{ backgroundColor: "rgba(0,0,0,0)" }}
        animate={{ backgroundColor: bgColor }}
        transition={{ duration: 0.4 }}
        style={{
          backgroundColor: bgColor,
          color: "#1a1a1a",
          borderBottom: "2px solid rgba(0,0,0,0.1)",
        }}
        className="rounded-[4px] px-1 py-[1px] mx-[1px] font-medium shadow-sm"
      >
        {parts}
      </motion.span>
    );
  };

  const parts: React.ReactNode[] = [];
  let cursor = 0;

  for (const root of tree) {
    if (cursor < root.start) {
      parts.push(content.slice(cursor, root.start));
    }
    parts.push(renderNode(root, content));
    cursor = root.end;
  }

  if (cursor < content.length) {
    parts.push(content.slice(cursor));
  }

  return <span>{parts.length > 0 ? parts : content}</span>;
};

/**
 * Render a single block
 */
const renderBlock = (
  block: MessageBlock,
  index: number,
  highlights?: Highlight[],
  isStreaming?: boolean,
  customCodeRenderer?: (content: string, language: string) => React.ReactNode
): React.ReactNode => {
  switch (block.type) {
    case "text":
      return (
        <motion.p
          key={`text-${index}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: index * 0.02 }}
          className="mb-2 sm:mb-3 leading-6 sm:leading-7 text-[14px] sm:text-[15px] text-foreground"
        >
          {renderTextBlock(block.content, highlights, index)}
        </motion.p>
      );

    case "divider":
      return (
        <motion.div
          key={`divider-${index}`}
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ duration: 0.3, delay: index * 0.02 }}
        >
          <hr className="message-divider" />
        </motion.div>
      );

    case "heading":
      const HeadingTag = `h${block.level}` as keyof JSX.IntrinsicElements;
      const headingClasses = {
        1: "text-xl sm:text-2xl font-bold mb-2 sm:mb-3 mt-4 sm:mt-6",
        2: "text-lg sm:text-xl font-bold mb-2 sm:mb-3 mt-3 sm:mt-5",
        3: "text-base sm:text-lg font-semibold mb-1.5 sm:mb-2 mt-3 sm:mt-4",
      };

      return (
        <motion.div
          key={`heading-${index}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: index * 0.02 }}
        >
          <HeadingTag className={cn("text-foreground", headingClasses[block.level])}>
            {block.content}
          </HeadingTag>
        </motion.div>
      );

    case "code":
      if (customCodeRenderer) {
        return (
          <motion.div
            key={`code-${index}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.02 }}
            className="my-3 sm:my-4"
          >
            {customCodeRenderer(block.content, block.language)}
          </motion.div>
        );
      }
      return (
        <motion.div
          key={`code-${index}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.02 }}
          className="my-3 sm:my-4"
        >
          <CodeBlock language={block.language}>{block.content}</CodeBlock>
        </motion.div>
      );

    case "list":
      return (
        <motion.ul
          key={`list-${index}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: index * 0.02 }}
          className="list-disc list-outside ml-4 sm:ml-5 mb-2 sm:mb-3 space-y-1 sm:space-y-1.5"
        >
          {block.items.map((item, itemIndex) => (
            <li
              key={`item-${index}-${itemIndex}`}
              className="leading-6 sm:leading-7 pl-0.5 sm:pl-1 text-[14px] sm:text-[15px] text-foreground"
            >
              {renderTextBlock(item, highlights, index)}
            </li>
          ))}
        </motion.ul>
      );

    case "image":
      return (
        <motion.div
          key={`image-${index}`}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: index * 0.02 }}
          className="my-3 sm:my-4 rounded-lg overflow-hidden border border-border"
        >
          <img
            src={block.src}
            alt={block.alt || "Image"}
            className="w-full h-auto"
            loading="lazy"
          />
        </motion.div>
      );

    default:
      return null;
  }
};

/**
 * Main Message Block Renderer Component
 */
export const MessageBlockRenderer = memo(({
  blocks,
  highlights,
  isStreaming = false,
  className = "",
  customCodeRenderer,
}: MessageBlockRendererProps) => {
  if (!blocks || blocks.length === 0) {
    return null;
  }

  return (
    <div className={cn("message-blocks", className)}>
      {(() => {
        let currentGlobalOffset = 0;
        return blocks.map((block, index) => {
          // Calculate block length safely based on block type
          // This must match how innerText/selection calculates length
          let blockLength = 0;

          if (block.type === 'text' || block.type === 'code' || block.type === 'heading') {
            blockLength = block.content ? block.content.length : 0;
          } else if (block.type === 'list' && block.items) {
            // Count length of all items joined by newlines (approximation of innerText)
            blockLength = block.items.reduce((acc, item) => acc + (item ? item.length : 0), 0);
            // Add newlines between items if multiple
            if (block.items.length > 1) {
              blockLength += (block.items.length - 1);
            }
          }
          // Images and dividers contribute 0 to text length (usually)

          // Filter and adjust highlights for this block
          const blockHighlights = (highlights || [])
            .filter(h => {
              // Check overlap
              return h.startOffset < (currentGlobalOffset + blockLength) && h.endOffset > currentGlobalOffset;
            })
            .map(h => ({
              ...h,
              // Convert to local coordinates
              startOffset: Math.max(0, h.startOffset - currentGlobalOffset),
              endOffset: Math.min(blockLength, h.endOffset - currentGlobalOffset)
            }));

          const renderedBlock = renderBlock(block, index, blockHighlights, isStreaming, customCodeRenderer);

          // Update offset for next block
          currentGlobalOffset += blockLength;
          // Add implicit newline length if blocks are separated (browser dependent behavior)
          // Usually separate blocks (divs/ps) behave like they have a newline in innerText
          if (blockLength > 0 && index < blocks.length - 1) {
            currentGlobalOffset += 1; // Approximate boundary newline
          }

          return renderedBlock;
        });
      })()}

      {/* Streaming cursor */}
      {isStreaming && (
        <motion.span
          initial={{ opacity: 1 }}
          animate={{ opacity: [1, 0.2, 1] }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="inline-block w-1 sm:w-1.5 h-4 sm:h-5 ml-0.5 sm:ml-1 bg-primary/80 align-middle rounded-sm"
        />
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  // Memo comparison - only re-render when blocks actually change
  return (
    JSON.stringify(prevProps.blocks) === JSON.stringify(nextProps.blocks) &&
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.highlights?.length === nextProps.highlights?.length
  );
});

MessageBlockRenderer.displayName = "MessageBlockRenderer";

