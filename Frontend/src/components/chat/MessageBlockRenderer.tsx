/**
 * Message Block Renderer
 * 
 * Renders structured MessageBlock[] into clean, elegant UI
 */

import { memo, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { MessageBlock, MessageBlocks } from "@/types/messageBlocks";
import { CodeBlock } from "./CodeBlock";
import { MediaActionCard } from "./MediaActionCard";
import { SuggestionChips } from "./SuggestionChips";
import { cn } from "@/lib/utils";
import { Highlight } from "@/types/chat";
import { detectSemanticHighlights, applySemanticHighlights, stripMarkdown } from "@/lib/semanticHighlight";
import { Info, Lightbulb, AlertTriangle, CheckCircle2, Quote } from "lucide-react";

// 🚀 Performance: Cache color conversions
const colorCache = new Map<string, string>();

const getDisplayColor = (color: string): string => {
  // Check cache first
  const cached = colorCache.get(color);
  if (cached) return cached;

  let result: string;
  if (color.startsWith("#")) {
    result = color;
  } else {
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
    result = colorMap[color.toLowerCase()] || "#FFD93D";
  }

  // Cache the result
  colorCache.set(color, result);
  return result;
};

interface MessageBlockRendererProps {
  blocks: MessageBlocks;
  highlights?: Highlight[];
  isStreaming?: boolean;
  className?: string;
  customCodeRenderer?: (content: string, language: string) => React.ReactNode;
}

/**
 * Render a single text block with optional highlights
 * 
 * Performance optimizations:
 * - Early returns for empty content
 * - Efficient deduplication with Set
 * - Memoized color lookups
 * - Tree-based rendering for nested highlights
 */
const renderTextBlock = (
  content: string,
  highlights?: Highlight[],
  blockIndex?: number
): React.ReactNode => {
  // Early return for empty content
  if (!content) return null;

  // 🔧 USER HIGHLIGHTS TAKE PRIORITY
  // If there are user highlights, render those (they use rendered text positions)
  const renderedContent = stripMarkdown(content);

  // Early return for empty rendered content
  if (!renderedContent) return null;

  // If we have user highlights, apply them to rendered content
  if (highlights && highlights.length > 0) {
    // ✅ FAST DEDUPLICATION using Set for O(1) lookup
    const seenSignatures = new Set<string>();
    const uniqueHighlights: Highlight[] = [];

    for (const h of highlights) {
      if ((h as any)._broken) continue;
      const signature = `${h.startIndex}:${h.endIndex}:${h.text?.slice(0, 50)}`;
      if (!seenSignatures.has(signature)) {
        seenSignatures.add(signature);
        uniqueHighlights.push(h);
      }
    }

    // ✅ VALIDATION - Check that highlights actually fall within this content block
    const validHighlights = uniqueHighlights.filter(h => {
      if (h.startIndex === undefined || h.endIndex === undefined || !h.text) {
        if (import.meta.env.DEV) {
          console.warn('[MessageBlockRenderer] Invalid highlight - missing fields:', h);
        }
        return false;
      }

      // Check bounds
      if (h.startIndex < 0 || h.endIndex > renderedContent.length || h.startIndex >= h.endIndex) {
        if (import.meta.env.DEV) {
          console.warn('[MessageBlockRenderer] Highlight out of bounds:', {
            highlight: h.id,
            range: [h.startIndex, h.endIndex],
            contentLength: renderedContent.length
          });
        }
        return false;
      }

      // Verify text matches (optional - for debugging)
      const actualText = renderedContent.substring(h.startIndex, h.endIndex);
      if (actualText !== h.text) {
        if (import.meta.env.DEV) {
          console.warn('[MessageBlockRenderer] Text mismatch:', {
            expected: h.text.substring(0, 30),
            actual: actualText.substring(0, 30)
          });
        }
        // Still allow it - the highlight system may have drift correction
      }

      return true;
    });

    if (validHighlights.length > 0) {
      // Sort highlights by start index, then by length (longer first for proper nesting)
      const sortedHighlights = [...validHighlights].sort((a, b) => {
        if (a.startIndex !== b.startIndex) return a.startIndex - b.startIndex;
        return (b.endIndex - b.startIndex) - (a.endIndex - a.startIndex);
      });

      // Build highlight tree for nested highlights
      interface HighlightNode {
        start: number;
        end: number;
        color: string;
        id: string;
        children: HighlightNode[];
      }

      const buildTree = (hlights: Highlight[]): HighlightNode[] => {
        const roots: HighlightNode[] = [];
        const stack: HighlightNode[] = [];

        for (const h of hlights) {
          const node: HighlightNode = {
            start: h.startIndex,
            end: h.endIndex,
            color: h.color,
            id: h.id,
            children: [],
          };

          // Pop nodes that are completely before this one
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

      const tree = buildTree(sortedHighlights);

      const renderNode = (node: HighlightNode, textContent: string): React.ReactNode => {
        const nodeText = textContent.slice(node.start, node.end);
        const bgColor = getDisplayColor(node.color);

        if (node.children.length === 0) {
          return (
            <motion.span
              key={`hl-${node.id}-${node.start}`}
              initial={{ backgroundColor: "rgba(255,255,0,0.2)" }}
              animate={{ backgroundColor: bgColor }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              style={{
                backgroundColor: bgColor,
                color: "#000000",
                borderBottom: "2px solid rgba(0,0,0,0.15)",
                padding: "1px 3px",
                borderRadius: "3px",
                margin: "0 1px",
              }}
              className="font-medium shadow-sm"
            >
              {nodeText}
            </motion.span>
          );
        }

        const parts: React.ReactNode[] = [];
        let cursor = node.start;

        for (const child of node.children) {
          if (cursor < child.start) {
            parts.push(<span key={`text-${cursor}-${child.start}`}>{textContent.slice(cursor, child.start)}</span>);
          }
          parts.push(renderNode(child, textContent));
          cursor = child.end;
        }

        if (cursor < node.end) {
          parts.push(<span key={`text-${cursor}-${node.end}`}>{textContent.slice(cursor, node.end)}</span>);
        }

        return (
          <motion.span
            key={`hl-${node.id}-${node.start}`}
            initial={{ backgroundColor: "rgba(255,255,0,0.2)" }}
            animate={{ backgroundColor: bgColor }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            style={{
              backgroundColor: bgColor,
              color: "#000000",
              borderBottom: "2px solid rgba(0,0,0,0.15)",
              padding: "1px 3px",
              borderRadius: "3px",
              margin: "0 1px",
            }}
            className="font-medium shadow-sm"
          >
            {parts}
          </motion.span>
        );
      };

      // Build parts array using RENDERED content
      const parts: React.ReactNode[] = [];
      let cursor = 0;

      for (const root of tree) {
        if (cursor < root.start) {
          parts.push(renderedContent.slice(cursor, root.start));
        }
        parts.push(renderNode(root, renderedContent));
        cursor = root.end;
      }

      if (cursor < renderedContent.length) {
        parts.push(renderedContent.slice(cursor));
      }

      return <span>{parts.length > 0 ? parts : renderedContent}</span>;
    }
  }

  // No user highlights - fall back to semantic highlighting (bold, code, etc.)
  const semanticHighlights = detectSemanticHighlights(content);
  if (semanticHighlights.length > 0) {
    return <span>{applySemanticHighlights(content, semanticHighlights)}</span>;
  }

  // Plain text, no highlights of any kind
  return <span>{content}</span>;
};

/**
 * Render a single block
 */
const renderBlock = (
  block: MessageBlock,
  index: number,
  highlights?: Highlight[],
  isStreaming?: boolean,
  customCodeRenderer?: (content: string, language: string) => React.ReactNode,
  chatId?: string
): React.ReactNode => {
  switch (block.type) {
    case "text":
      return (
        <motion.p
          key={`text-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.08 }}
          className="mb-5 leading-[1.85] text-[15.5px] text-foreground/90 font-medium tracking-[0.015em] [word-spacing:0.08em] first:mt-0"
          data-block-index={index}
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
          className="my-6 flex items-center gap-4"
        >
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
          <span className="text-muted-foreground/40 text-xs">✦</span>
          <div className="flex-1 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
        </motion.div>
      );

    case "heading":
      const HeadingTag = `h${block.level}` as keyof JSX.IntrinsicElements;
      const headingClasses = {
        1: "text-[22px] font-bold mb-5 mt-7 text-foreground tracking-[-0.02em] flex items-center gap-3",
        2: "text-[19px] font-bold mb-4 mt-6 text-foreground tracking-[-0.01em] flex items-center gap-2.5",
        3: "text-[17px] font-semibold mb-3 mt-5 text-foreground flex items-center gap-2",
      };
      const headingDecoration = {
        1: (
          <span className="flex-shrink-0 w-1.5 h-5 rounded-full bg-foreground/80" />
        ),
        2: (
          <span className="flex-shrink-0 w-1 h-4 rounded-full bg-foreground/60" />
        ),
        3: (
          <span className="text-foreground/50">▸</span>
        ),
      };

      return (
        <motion.div
          key={`heading-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.08 }}
        >
          <HeadingTag className={cn(headingClasses[block.level])} data-block-index={index}>
            {headingDecoration[block.level]}
            {block.content}
          </HeadingTag>
        </motion.div>
      );

    case "code":
      if (customCodeRenderer) {
        return (
          <motion.div
            key={`code-${index}`}
            initial={{ opacity: 0.8 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.15 }}
            className="my-4 sm:my-5 w-full max-w-full min-w-0 overflow-hidden"
            style={{ contain: 'layout' }}
          >
            {customCodeRenderer(block.content, block.language)}
          </motion.div>
        );
      }
      return (
        <motion.div
          key={`code-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15 }}
          className="my-4 sm:my-5 w-full max-w-full min-w-0"
          style={{
            contain: 'layout',
            maxWidth: '100%',
            overflow: 'hidden',
          }}
        >
          <CodeBlock language={block.language}>{block.content}</CodeBlock>
        </motion.div>
      );

    case "list":
      const ListTag = block.ordered ? 'ol' : 'ul';
      const listClasses = block.ordered
        ? "list-none ml-0 mb-5 space-y-2.5"
        : "list-none ml-0 mb-5 space-y-2.5";

      return (
        <motion.div
          key={`list-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.08 }}
          className="my-4"
        >
          <ListTag className={listClasses}>
            {block.items.map((item, itemIndex) => (
              <motion.li
                key={`item-${index}-${itemIndex}`}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15, delay: itemIndex * 0.025 }}
                className="leading-[1.75] text-[15px] text-foreground/90 font-medium tracking-[0.01em] flex items-start gap-3 group"
              >
                {block.ordered ? (
                  <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-muted/80 text-muted-foreground text-sm font-semibold flex items-center justify-center mt-0.5 border border-border/40 transition-colors">
                    {itemIndex + 1}
                  </span>
                ) : (
                  <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-foreground/80 mt-2.5 opacity-90" />
                )}
                <span className="flex-1 pt-0.5">{renderTextBlock(item, highlights, index)}</span>
              </motion.li>
            ))}
          </ListTag>
        </motion.div>
      );

    case "table":
      return (
        <motion.div
          key={`table-${index}`}
          initial={{ opacity: 0.8, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="my-5 group"
        >
          <div className="overflow-x-auto thin-scrollbar rounded-xl border border-border/30 bg-gradient-to-b from-card/60 to-card/40 shadow-md backdrop-blur-sm">
            <table className="w-full border-collapse text-sm min-w-[400px]">
              <thead>
                <tr className="bg-gradient-to-r from-muted/70 via-muted/50 to-muted/70 border-b border-border/40">
                  {block.headers.map((header, hIndex) => (
                    <th
                      key={`th-${index}-${hIndex}`}
                      className={cn(
                        "px-5 py-4 text-left font-semibold text-foreground tracking-wide border-b border-border/30",
                        "first:pl-6 last:pr-6 text-[13.5px] uppercase",
                        hIndex === 0 && "rounded-tl-xl",
                        hIndex === block.headers.length - 1 && "rounded-tr-xl"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        {hIndex === 0 && (
                          <span className="w-1.5 h-4 rounded-full bg-gradient-to-b from-primary to-primary/50" />
                        )}
                        {header}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/15">
                {block.rows.map((row, rowIndex) => (
                  <motion.tr
                    key={`tr-${index}-${rowIndex}`}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.12, delay: rowIndex * 0.015 }}
                    className={cn(
                      "transition-all duration-200 hover:bg-primary/[0.04] group/row",
                      rowIndex % 2 === 0 ? "bg-transparent" : "bg-muted/[0.08]"
                    )}
                  >
                    {row.map((cell, cellIndex) => (
                      <td
                        key={`td-${index}-${rowIndex}-${cellIndex}`}
                        className={cn(
                          "px-5 py-3.5 text-foreground/80 first:pl-6 last:pr-6 text-[14px]",
                          cellIndex === 0 && "font-medium text-foreground/95"
                        )}
                      >
                        {renderTextBlock(cell, highlights, index)}
                      </td>
                    ))}
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          {block.rows.length > 3 && (
            <div className="mt-2.5 text-xs text-muted-foreground/50 text-right pr-2 flex items-center justify-end gap-1.5">
              <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
              {block.rows.length} rows
            </div>
          )}
        </motion.div>
      );

    case "blockquote":
      return (
        <motion.div
          key={`blockquote-${index}`}
          initial={{ opacity: 0.8, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.15 }}
          className="my-5"
        >
          <blockquote className="relative pl-6 py-4 pr-5 border-l-[3px] border-primary/50 bg-gradient-to-r from-muted/50 via-muted/25 to-transparent rounded-r-xl overflow-hidden">
            <div className="absolute -top-2 left-1 text-6xl text-primary/[0.08] font-serif leading-none select-none pointer-events-none">
              "
            </div>
            <Quote className="absolute top-3 right-3 w-5 h-5 text-primary/10" />
            <p className="text-[15px] text-foreground/80 italic leading-[1.8] relative z-10 pl-1">
              {block.content}
            </p>
          </blockquote>
        </motion.div>
      );

    case "callout":
      const calloutConfig = {
        info: {
          icon: Info,
          bgClass: "bg-gradient-to-r from-blue-500/10 via-blue-500/5 to-transparent border-blue-500/30",
          iconClass: "text-blue-500",
          titleClass: "text-blue-600 dark:text-blue-400",
          title: "ℹ️ Info",
          glowClass: "shadow-blue-500/5"
        },
        tip: {
          icon: Lightbulb,
          bgClass: "bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border-amber-500/30",
          iconClass: "text-amber-500",
          titleClass: "text-amber-600 dark:text-amber-400",
          title: "💡 Tip",
          glowClass: "shadow-amber-500/5"
        },
        warning: {
          icon: AlertTriangle,
          bgClass: "bg-gradient-to-r from-orange-500/10 via-orange-500/5 to-transparent border-orange-500/30",
          iconClass: "text-orange-500",
          titleClass: "text-orange-600 dark:text-orange-400",
          title: "⚠️ Warning",
          glowClass: "shadow-orange-500/5"
        },
        success: {
          icon: CheckCircle2,
          bgClass: "bg-gradient-to-r from-green-500/10 via-green-500/5 to-transparent border-green-500/30",
          iconClass: "text-green-500",
          titleClass: "text-green-600 dark:text-green-400",
          title: "✅ Success",
          glowClass: "shadow-green-500/5"
        }
      };

      const config = calloutConfig[block.variant] || calloutConfig.info;
      const CalloutIcon = config.icon;

      return (
        <motion.div
          key={`callout-${index}`}
          initial={{ opacity: 0.8, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "my-5 p-4 rounded-xl border shadow-sm",
            config.bgClass,
            config.glowClass
          )}
        >
          <div className="flex items-start gap-3">
            <div className={cn(
              "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center",
              config.iconClass.replace('text-', 'bg-').replace('500', '500/15')
            )}>
              <CalloutIcon className={cn("w-4 h-4", config.iconClass)} />
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn("font-semibold text-sm mb-1.5", config.titleClass)}>
                {config.title}
              </p>
              <p className="text-[14.5px] text-foreground/75 leading-relaxed">
                {block.content}
              </p>
            </div>
          </div>
        </motion.div>
      );

    case "tasklist":
      return (
        <motion.div
          key={`tasklist-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.1 }}
          className="my-4 space-y-2.5"
        >
          {block.items.map((item, itemIndex) => (
            <motion.div
              key={`task-${index}-${itemIndex}`}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15, delay: itemIndex * 0.025 }}
              className={cn(
                "flex items-center gap-3 p-3.5 rounded-xl border transition-all duration-200 group",
                item.checked
                  ? "bg-gradient-to-r from-green-500/[0.08] to-green-500/[0.02] border-green-500/25"
                  : "bg-gradient-to-r from-muted/40 to-muted/20 border-border/40 hover:bg-muted/50 hover:border-border/50"
              )}
            >
              <div className={cn(
                "flex-shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200",
                item.checked
                  ? "bg-gradient-to-br from-green-500 to-green-600 border-green-500 shadow-sm shadow-green-500/25"
                  : "border-muted-foreground/30 group-hover:border-muted-foreground/40"
              )}>
                {item.checked && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className={cn(
                "text-[15px] leading-relaxed transition-colors",
                item.checked ? "text-foreground/55 line-through decoration-foreground/20" : "text-foreground/90"
              )}>
                {item.text}
              </span>
            </motion.div>
          ))}
        </motion.div>
      );

    case "steps":
      return (
        <motion.div
          key={`steps-${index}`}
          initial={{ opacity: 0.8 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.1 }}
          className="my-6 relative pl-2"
        >
          <div className="absolute left-[17px] top-12 bottom-8 w-0.5 bg-gradient-to-b from-primary via-primary/30 to-transparent rounded-full" />
          <div className="space-y-4">
            {block.items.map((item, itemIndex) => (
              <motion.div
                key={`step-${index}-${itemIndex}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: itemIndex * 0.04 }}
                className="flex items-start gap-4 relative group"
              >
                <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-primary via-primary to-primary/80 text-primary-foreground font-bold text-sm flex items-center justify-center shadow-lg shadow-primary/25 z-10 ring-[3px] ring-background transition-transform duration-200 group-hover:scale-105">
                  {itemIndex + 1}
                </div>
                <div className="flex-1 pt-1 pb-2">
                  <div className="p-4 rounded-xl bg-gradient-to-r from-muted/35 via-muted/20 to-transparent border border-border/25 group-hover:from-muted/45 group-hover:border-border/40 transition-all duration-200 shadow-sm">
                    <p className="text-[15px] text-foreground/90 leading-[1.75]">
                      {renderTextBlock(item, highlights, index)}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      );

    case "definition":
      return (
        <motion.div
          key={`definition-${index}`}
          initial={{ opacity: 0.8, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15 }}
          className="my-5 p-5 rounded-xl bg-gradient-to-br from-muted/45 via-muted/25 to-transparent border border-border/35 shadow-sm hover:border-border/45 transition-colors duration-200"
        >
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-br from-primary/25 to-primary/10 border border-primary/15 flex items-center justify-center shadow-sm">
              <span className="text-xl">📖</span>
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-[16.5px] font-bold text-primary mb-2 flex items-center gap-2">
                {block.term}
              </h4>
              <p className="text-[14.5px] text-foreground/75 leading-[1.75]">
                {block.definition}
              </p>
            </div>
          </div>
        </motion.div>
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

    case "action":
      if (block.data?.type === "media_play") {
        const payload = block.data.payload;
        return (
          <div key={`action-${index}`} className="my-4">
            <MediaActionCard
              payload={payload}
              chatId={chatId}
            />
          </div>
        );
      }
      if (block.data?.type === "suggestions") {
        return (
          <div key={`action-${index}`} className="my-4">
            <SuggestionChips
              suggestions={block.data.payload?.suggestions || []}
              chatId={chatId}
            />
          </div>
        );
      }
      return null;

    case "ask_flow":
      return (
        <motion.div
          key={`ask-${index}`}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="my-5 rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 overflow-hidden shadow-sm"
        >
          {/* Header */}
          <div className="px-4 py-2.5 bg-indigo-500/10 border-b border-indigo-500/10 flex items-center gap-2.5">
            <span className="flex items-center justify-center w-6 h-6 rounded-md bg-indigo-500/20 text-indigo-400">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M15 10l5 5-5 5" /><path d="M4 4v7a4 4 0 004 4h12" /></svg>
            </span>
            <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Ask Flow Context</span>
          </div>

          {/* Selected Text (Context) */}
          <div className="px-4 py-3 bg-black/10 border-b border-indigo-500/10">
            <div className="relative pl-3 border-l-2 border-indigo-500/30">
              <p className="text-[13.5px] font-mono text-muted-foreground/90 whitespace-pre-wrap leading-relaxed line-clamp-[10]">
                {block.selectedText}
              </p>
            </div>
          </div>

          {/* User Instruction */}
          <div className="p-4 bg-background/40">
            <div className="flex items-start gap-3">
              <span className="mt-1 text-foreground/50">💬</span>
              <p className="text-[15.5px] font-medium text-foreground leading-relaxed">
                {block.instruction}
              </p>
            </div>
          </div>
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
  chatId,
}: MessageBlockRendererProps & { chatId?: string }) => {
  if (!blocks || blocks.length === 0) {
    return null;
  }

  // Debug log highlights received
  if (import.meta.env.DEV && highlights && highlights.length > 0) {
    console.log(`📝 MessageBlockRenderer received ${highlights.length} highlights:`, highlights);
  }

  return (
    <div className={cn("message-blocks ai-message", className)}>
      {(() => {
        let currentGlobalOffset = 0;
        return blocks.map((block, index) => {
          let blockLength = 0;

          if (block.type === 'text' || block.type === 'code' || block.type === 'heading') {
            const renderedBlockContent = block.content ? stripMarkdown(block.content) : '';
            blockLength = renderedBlockContent.length;
          } else if (block.type === 'list' && block.items) {
            const renderedItems = block.items.map(item => item ? stripMarkdown(item) : '');
            blockLength = renderedItems.reduce((acc, item) => acc + item.length, 0);
            if (block.items.length > 1) {
              blockLength += (block.items.length - 1);
            }
          }

          const canonicalStart = typeof block.startIndex === 'number' ? block.startIndex : currentGlobalOffset;
          const canonicalEnd = typeof block.endIndex === 'number' ? block.endIndex : (canonicalStart + blockLength);

          const blockHighlights = (highlights || [])
            .filter(h => {
              const overlaps = h.startIndex < canonicalEnd && h.endIndex > canonicalStart;
              return overlaps;
            })
            .map(h => ({
              ...h,
              startIndex: Math.max(0, h.startIndex - canonicalStart),
              endIndex: Math.min(canonicalEnd - canonicalStart, h.endIndex - canonicalStart)
            }));

          const renderedBlock = renderBlock(block, index, blockHighlights, isStreaming, customCodeRenderer, chatId);

          currentGlobalOffset += blockLength;
          if (blockLength > 0 && index < blocks.length - 1) {
            currentGlobalOffset += 1;
          }

          return renderedBlock;
        });
      })()}
    </div>
  );
}, (prevProps, nextProps) => {
  const blocksEqual = JSON.stringify(prevProps.blocks) === JSON.stringify(nextProps.blocks);
  const streamingEqual = prevProps.isStreaming === nextProps.isStreaming;
  const chatIdEqual = prevProps.chatId === nextProps.chatId;

  const sig = (arr?: Highlight[]) => {
    if (!arr || arr.length === 0) return "";
    return arr
      .map(h => `${h.startIndex}:${h.endIndex}:${h.color}`)
      .join("|");
  };

  const highlightsEqual = sig(prevProps.highlights) === sig(nextProps.highlights);

  return blocksEqual && streamingEqual && highlightsEqual && chatIdEqual;
});

MessageBlockRenderer.displayName = "MessageBlockRenderer";
