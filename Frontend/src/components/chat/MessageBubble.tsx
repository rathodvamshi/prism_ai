import { useEffect, useMemo, useState, useRef, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Attachment, Message } from "@/types/chat";
import { useProfileStore } from "@/stores/profileStore";
import { Button } from "@/components/ui/button";
import { TypingIndicator } from "@/components/chat/LoadingSkeletons";
import {
  ThumbsUp,
  ThumbsDown,
  Copy,
  Volume2,
  RefreshCw,
  Pencil,
  Highlighter,
  Loader2,
  Bot,
  Calendar,
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { HighlightMenu } from "./HighlightMenu";
import { useChatStore } from "@/stores/chatStore";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from "./CodeBlock";
import { TextFormatter } from "@/lib/textFormatter";
import { Separator } from "@/components/ui/separator-premium";
import { Callout } from "@/components/ui/callout";
import { StreamingMessage } from "./StreamingMessage";
import { ActionCard, ActionCardState } from "./ActionCard";

interface MessageBubbleProps {
  message: Message;
  onHighlight?: (messageId: string, text: string, startIndex: number, endIndex: number) => void;
  onCreateMiniAgent?: (messageId: string, selectedText: string) => void;
  miniAgent?: any;
  onOpenHighlightsPanel?: (messageId: string) => void;
  showHighlightsPanel?: boolean;
  isSpeaking?: boolean;
  onSpeak?: (messageId: string, text: string) => void;
  onStopSpeaking?: () => void;
  // Legacy support
  onAddHighlight?: (color: string, text: string) => void;
  hasMiniAgent?: boolean;
  onOpenMiniAgent?: () => void;
  onOpenHighlights?: () => void;
  isStreaming?: boolean;
  isThinking?: boolean;
}

let currentUtterance: SpeechSynthesisUtterance | null = null;
let currentSpeakingId: string | null = null;

/**
 * GPT-Style Message Bubble Component
 * 
 * Performance Optimizations:
 * 1. Memoized to prevent unnecessary re-renders
 * 2. Stable message keys (no remounting)
 * 3. Append-only content updates
 * 4. Lazy highlight rendering
 */
export const MessageBubble = memo(({
  message,
  onHighlight,
  onCreateMiniAgent,
  miniAgent,
  onOpenHighlightsPanel,
  showHighlightsPanel,
  isSpeaking,
  onSpeak,
  onStopSpeaking,
  // Legacy support
  onAddHighlight,
  hasMiniAgent,
  onOpenMiniAgent,
  onOpenHighlights,
  isStreaming = false,
  isThinking = false,
}: MessageBubbleProps) => {
  const { toast } = useToast();
  const [selectedText, setSelectedText] = useState("");
  const [selectedRange, setSelectedRange] = useState<{start: number; end: number} | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ x: number; y: number; bottom: number; width: number } | null>(null);
  const [isRecoloring, setIsRecoloring] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const isUser = message.role === "user";
  const images = (message.attachments || []).filter((a) => a.type === "image");
  const files = (message.attachments || []).filter((a) => a.type === "file");
  const action = message.action;
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerIndex, setViewerIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [profileAvatar, setProfileAvatar] = useState<string | null>(null);
  const [profileName, setProfileName] = useState<string>("User");
  const tooltipSide = "bottom";
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [taskConfirmed, setTaskConfirmed] = useState(false);
  const [taskCancelled, setTaskCancelled] = useState(false);
  const [taskTimePassed, setTaskTimePassed] = useState(false);
  const [autoDismissed, setAutoDismissed] = useState(false);
  const [showReschedule, setShowReschedule] = useState(false);
  const hasUserRespondedRef = useRef(false);
  const { confirmTaskDraft, addMessage, currentChatId, chats } = useChatStore();

  const { profile } = useProfileStore();

  useEffect(() => {
    setProfileAvatar(profile.avatarUrl || "");
    setProfileName(profile.name || "User");
  }, [profile]);

  // Initialize confirmation state from database (persisted action)
  useEffect(() => {
    if (action && (action as any).confirmed) {
      setTaskConfirmed(true);
      hasUserRespondedRef.current = true;
    }
    if (action && (action as any).cancelled) {
      setTaskCancelled(true);
      hasUserRespondedRef.current = true;
    }
  }, [action]);

  // Auto-dismiss logic: If user doesn't respond and moves to next message
  useEffect(() => {
    if (!action || !(action as any).payload?.due_date || isUser) return;
    if (taskConfirmed || taskCancelled || hasUserRespondedRef.current) return;

    // Get current chat messages
    const currentChat = chats.find(c => c.id === currentChatId);
    if (!currentChat) return;

    // Find this message's index
    const messageIndex = currentChat.messages.findIndex(m => m.id === message.id);
    if (messageIndex === -1) return;

    // Check if there are newer AI messages after this one
    const hasNewerMessages = currentChat.messages.slice(messageIndex + 1).some(m => m.role === "assistant");
    
    if (hasNewerMessages && !hasUserRespondedRef.current) {
      // User moved on without responding - auto-dismiss as "No"
      setAutoDismissed(true);
    }
  }, [action, chats, currentChatId, message.id, taskConfirmed, taskCancelled, isUser]);

  /**
   * Get exact selection offsets using DOM Range API
   * This correctly handles multiple occurrences of the same text
   */
  const getSelectionOffsets = (containerElement: HTMLElement, range: Range): { start: number; end: number } | null => {
    try {
      // Create a range from start of container to start of selection
      const preRange = document.createRange();
      preRange.selectNodeContents(containerElement);
      preRange.setEnd(range.startContainer, range.startOffset);
      
      const start = preRange.toString().length;
      const end = start + range.toString().length;
      
      return { start, end };
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[MessageBubble] Selection offset calculation error:', error);
      }
      return null;
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();

    if (text && text.length > 0 && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      // The currentTarget is the message content container with data-message-content attribute
      const messageElement = e.currentTarget as HTMLElement;
      
      if (rect && range && messageElement) {
        // Use DOM Range API to get exact selection offsets
        const offsets = getSelectionOffsets(messageElement, range);
        
        if (offsets && offsets.start >= 0 && offsets.end > offsets.start) {
          // Check if selection overlaps with existing highlight
          const overlappingHighlight = message.highlights?.find(
            h => offsets.start >= h.startOffset && offsets.end <= h.endOffset
          );
          
          setSelectedText(text);
          setSelectedRange({ start: offsets.start, end: offsets.end });
          
          // Pass raw selection rectangle data to HighlightMenu
          // Let HighlightMenu calculate perfect position (like ChatGPT does)
          setMenuPosition({
            x: rect.left + rect.width / 2, // Center of selection
            y: rect.top,                    // Top edge of selection
            bottom: rect.bottom,            // Bottom edge of selection  
            width: rect.width,
          });
          
          // If it's an exact match with existing highlight, allow re-coloring
          if (overlappingHighlight && 
              offsets.start === overlappingHighlight.startOffset && 
              offsets.end === overlappingHighlight.endOffset) {
            // User can re-color this highlight
            setIsRecoloring(overlappingHighlight.id);
          } else {
            setIsRecoloring(null);
          }
        }
      }
    } else {
      setSelectedText("");
      setSelectedRange(null);
      setMenuPosition(null);
      setIsRecoloring(null);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const handleSpeakToggle = () => {
    // Stop any ongoing speech
    if (speechSynthesis.speaking) {
      speechSynthesis.cancel();
      currentUtterance = null;
      currentSpeakingId = null;
      // If we were already speaking this message, just stop
      return;
    }
    // Start speaking this message
    currentUtterance = new SpeechSynthesisUtterance(message.content);
    currentUtterance.volume = 1.0; // loud and clear
    currentUtterance.rate = 1.0;   // natural speed
    currentUtterance.pitch = 1.0;  // normal tone
    currentSpeakingId = message.id;
    currentUtterance.onend = () => {
      currentUtterance = null;
      currentSpeakingId = null;
    };
    speechSynthesis.speak(currentUtterance);
  };

  const toggleLike = () => {
    if (liked) {
      setLiked(false);
    } else {
      setLiked(true);
      setDisliked(false);
    }
  };

  const toggleDislike = () => {
    if (disliked) {
      setDisliked(false);
    } else {
      setDisliked(true);
      setLiked(false);
    }
  };

  const closeMenu = () => {
    setSelectedText("");
    setSelectedRange(null);
    setMenuPosition(null);
    setIsRecoloring(null);
    window.getSelection()?.removeAllRanges();
  };

  // Click outside to close popup
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node) && menuPosition) {
        closeMenu();
      }
    };

    if (menuPosition) {
      // Small delay to prevent immediate close from the same click that opened it
      setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
      }, 100);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuPosition]);


  /**
   * Render text with markdown, code blocks, highlights, and auto-formatting
   * Supports nested and overlapping highlights correctly
   */
  const renderWithHighlights = () => {
    let text = message.content;
    const highlights = message.highlights || [];
    
    // For AI messages that are streaming, use StreamingMessage component
    if (!isUser && (isStreaming || isThinking)) {
      return (
        <StreamingMessage
          content={text}
          isStreaming={isStreaming}
          isThinking={isThinking}
        />
      );
    }
    
    // Apply text formatting pipeline for completed AI messages
    if (!isUser) {
      text = TextFormatter.format(text);
      text = TextFormatter.splitLongParagraphs(text);
    }
    
    // For user messages or messages without code blocks, use simple rendering
    if (isUser || !text.includes('```')) {
      if (highlights.length === 0) return text;
      // Apply highlights for user messages
      return renderHighlightedText(text, highlights);
    }
    
    // For completed AI messages with code blocks, use markdown
    return (
      <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            
            return !inline ? (
              <CodeBlock language={match ? match[1] : 'text'}>
                {codeString}
              </CodeBlock>
            ) : (
              <CodeBlock inline>{codeString}</CodeBlock>
            );
          },
          p({ children }) {
            // Apply highlights to paragraph content if available
            if (highlights.length > 0 && typeof children === 'string') {
              return <p className="mb-3 leading-7">{renderHighlightedText(children, highlights)}</p>;
            }
            return <p className="mb-3 leading-7">{children}</p>;
          },
          // Custom callout syntax: :::warning ... :::
          blockquote({ children }) {
            const content = String(children);
            
            // Check if it's a callout
            const calloutMatch = content.match(/:::(warning|tip|info|important)\s*([\s\S]*?):::/i);
            if (calloutMatch) {
              const type = calloutMatch[1].toLowerCase() as 'warning' | 'tip' | 'info' | 'important';
              const text = calloutMatch[2].trim();
              return <Callout type={type}>{text}</Callout>;
            }
            
            // Regular blockquote
            return (
              <blockquote className="border-l-4 border-primary/40 pl-4 py-2 my-3 bg-muted/30 rounded-r-md italic text-muted-foreground">
                {children}
              </blockquote>
            );
          },
          hr: () => <Separator />,
          strong({ children }) {
            return <strong className="font-semibold text-foreground">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic text-foreground/90">{children}</em>;
          },
          ul({ children }) {
            return <ul className="list-disc list-outside ml-5 mb-3 space-y-1.5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal list-outside ml-5 mb-3 space-y-1.5">{children}</ol>;
          },
          li({ children }) {
            return <li className="leading-7 pl-1">{children}</li>;
          },
          table({ children }) {
            return (
              <div className="my-4 overflow-x-auto rounded-lg border border-border">
                <table className="w-full border-collapse">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-muted/50">{children}</thead>;
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-border">{children}</tbody>;
          },
          tr({ children }) {
            return <tr className="hover:bg-muted/30 transition-colors">{children}</tr>;
          },
          th({ children }) {
            return <th className="px-4 py-2 text-left text-sm font-semibold border-b border-border">{children}</th>;
          },
          td({ children }) {
            return <td className="px-4 py-2 text-sm">{children}</td>;
          },
          h1({ children }) {
            return <h1 className="text-2xl font-bold mb-3 mt-6">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-xl font-bold mb-3 mt-5">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-lg font-semibold mb-2 mt-4">{children}</h3>;
          },
          h4({ children }) {
            return <h4 className="text-base font-semibold mb-2 mt-3">{children}</h4>;
          },
          a({ href, children }) {
            return <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium">{children}</a>;
          },
        }}
      >
        {text}
      </ReactMarkdown>
      </div>
    );
  };

  /**
   * Render text with highlights only (for user messages)
   */
  const renderHighlightedText = (text: string, highlights: typeof message.highlights) => {
    if (!highlights || highlights.length === 0) return text;
    
    // Sort highlights by start position, then by length (longer first for proper nesting)
    const sortedHighlights = [...highlights].sort((a, b) => {
      if (a.startOffset !== b.startOffset) {
        return a.startOffset - b.startOffset;
      }
      // If same start, longer highlight comes first (outer wrapper)
      return (b.endOffset - b.startOffset) - (a.endOffset - a.startOffset);
    });
    
    // Helper function to get the display color (supports both HEX and color names)
    const getDisplayColor = (color: string): string => {
      // If it's already a HEX color, use it directly
      if (color.startsWith('#')) {
        return color;
      }
      
      // Legacy color name mapping (for backwards compatibility)
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
      
      return colorMap[color.toLowerCase()] || "#FFD93D"; // Default to yellow if not found
    };
    
    // Build a tree structure for nested highlights
    interface HighlightNode {
      start: number;
      end: number;
      color: string;
      id: string;
      children: HighlightNode[];
    }
    
    const buildTree = (highlights: typeof sortedHighlights): HighlightNode[] => {
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
        
        // Find parent (first highlight that contains this one)
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
    
    // Render tree recursively
    const renderNode = (node: HighlightNode, textContent: string): React.ReactNode => {
      const nodeText = textContent.slice(node.start, node.end);
      const bgColor = getDisplayColor(node.color);
      
      if (node.children.length === 0) {
        // Leaf node - just render highlighted text
        return (
          <span
            key={`${node.id}-${node.start}`}
            style={{ 
              backgroundColor: bgColor, 
              color: '#000000',
              border: '1px solid rgba(0,0,0,0.08)'
            }}
            className="rounded-[3px] px-0.5"
          >
            {nodeText}
          </span>
        );
      }
      
      // Node with children - render with nested highlights
      const parts: React.ReactNode[] = [];
      let cursor = node.start;
      
      for (const child of node.children) {
        // Add text before child
        if (cursor < child.start) {
          parts.push(textContent.slice(cursor, child.start));
        }
        
        // Add child node
        parts.push(renderNode(child, textContent));
        cursor = child.end;
      }
      
      // Add remaining text
      if (cursor < node.end) {
        parts.push(textContent.slice(cursor, node.end));
      }
      
      return (
        <span
          key={`${node.id}-${node.start}`}
          style={{ 
            backgroundColor: bgColor, 
            color: '#000000',
            border: '1px solid rgba(0,0,0,0.08)'
          }}
          className="rounded-[3px] px-0.5"
        >
          {parts}
        </span>
      );
    };
    
    // Render complete text with tree
    const parts: React.ReactNode[] = [];
    let cursor = 0;
    
    for (const root of tree) {
      // Add text before root
      if (cursor < root.start) {
        parts.push(text.slice(cursor, root.start));
      }
      
      // Add root node with all its children
      parts.push(renderNode(root, text));
      cursor = root.end;
    }
    
    // Add remaining text
    if (cursor < text.length) {
      parts.push(text.slice(cursor));
    }
    
    return parts;
  };

  return (
    <>
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
      className={cn(
        "flex gap-2 sm:gap-3 group mb-3 sm:mb-4",
        isUser ? "flex-row-reverse self-end" : "self-start"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "w-7 h-7 sm:w-8 sm:h-8 rounded-full overflow-hidden flex items-center justify-center shrink-0 border border-border",
          isUser ? "bg-secondary" : "bg-secondary"
        )}
      >
        {isUser ? (
          profileAvatar ? (
            <img src={profileAvatar} alt={profileName} className="w-full h-full object-cover" />
          ) : (
            <span className="text-[10px] sm:text-xs font-semibold">
              {(profileName || "U").trim().charAt(0).toUpperCase()}
            </span>
          )
        ) : (
          <img src="/pyramid.svg" alt="Prism" className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          isUser
            ? "relative text-right max-w-[85%] sm:max-w-[720px] w-fit"
            : "relative text-left w-full max-w-none pr-8 sm:pr-[2.9rem]"
        )}
      > 
        <div
          className={cn(
            "inline-block rounded-xl sm:rounded-[16px] break-words font-[Inter,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif] [word-break:normal] [overflow-wrap:break-word] text-left transition-all duration-150 ease-out",
            isUser
              ? "bg-secondary text-secondary-foreground px-3 py-2.5 sm:px-[18px] sm:py-[14px] ml-1 sm:ml-2 shadow-sm text-[15px] sm:text-[16px] leading-[1.5] whitespace-pre-wrap"
              : "text-foreground px-0 py-0 text-[15px] sm:text-[17px] leading-[1.6] sm:leading-[1.7] font-medium [word-spacing:0.08em] [&_p]:mb-[6px]"
          )}
          onMouseUp={handleMouseUp}
          data-message-content
        >
          {images.length > 0 && (
            <div className={cn("mb-2 sm:mb-3 grid gap-1.5 sm:gap-2", images.length === 1 ? "grid-cols-1" : images.length === 2 ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3") }>
              {images.map((img, idx) => (
                <button key={img.id} type="button" onClick={() => { setViewerIndex(idx); setZoom(1); setViewerOpen(true); }} className="block w-full overflow-hidden rounded-md sm:rounded-lg bg-secondary">
                  <img
                    src={img.thumbUrl || img.url}
                    alt={img.name}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-24 sm:h-28 md:h-36 object-cover"
                    sizes="(max-width: 640px) 45vw, 30vw"
                  />
                </button>
              ))}
            </div>
          )}
          {files.length > 0 && (
            <div className="mb-2 sm:mb-3 flex flex-wrap gap-1.5 sm:gap-2">
              {files.map((f) => (
                <a key={f.id} href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 sm:gap-2 px-2 py-1 rounded-md bg-secondary text-[11px] sm:text-xs border border-border hover:bg-secondary/80">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary" />
                  <span className="truncate max-w-[8rem] sm:max-w-[10rem]">{f.name}</span>
                </a>
              ))}
            </div>
          )}
          
          {/* Render content with streaming support */}
          {renderWithHighlights()}

          
          {/* Task confirmation card - ONLY show when both description AND due_date exist */}
          {!isThinking && action && 'payload' in action && (action as any).type === "task_draft" && (action as any).payload?.due_date && (
            <ActionCard
              state={
                autoDismissed && !showReschedule && !taskConfirmed && !(action as any).confirmed
                  ? ActionCardState.AUTO_DISMISSED
                  : showReschedule && !taskConfirmed && !(action as any).confirmed
                  ? ActionCardState.RESCHEDULING
                  : taskCancelled
                  ? ActionCardState.CANCELLED
                  : taskTimePassed
                  ? ActionCardState.TIME_PASSED
                  : taskConfirmed || (action as any).confirmed
                  ? ActionCardState.CONFIRMED
                  : ActionCardState.ASK_CONFIRM
              }
              taskDescription={(action as any).payload?.description || "Task"}
              dueDate={(action as any).payload.due_date}
              dueDateHumanReadable={(action as any).payload.due_date_human_readable}
              confirmedAt={(action as any).confirmedAt}
              isDuplicate={(action as any).confirmationMessage?.includes("already exists")}
              onConfirm={async () => {
                hasUserRespondedRef.current = true;
                
                // ⚡ Optimistic UI update - show confirmed immediately
                setTaskConfirmed(true);
                
                try {
                  // ☁️ Use due_date_iso if available (preferred format), fallback to due_date
                  const dueDateToSend = (action as any).payload?.due_date_iso || 
                                       (action as any).payload?.due_date;
                  
                  if (!dueDateToSend) {
                    toast({
                      title: "❌ Missing Information",
                      description: "Due date is required. Please try again with a specific time.",
                      variant: "destructive",
                    });
                    setTaskConfirmed(false);
                    return;
                  }
                  
                  await confirmTaskDraft(
                    message.id,
                    (action as any).payload?.description || message.content,
                    dueDateToSend
                  );
                  
                  // Success - already showing confirmed state
                  const isDuplicate = (action as any).confirmationMessage?.includes("already exists");
                  
                  toast({
                    title: isDuplicate ? "⚠️ Already Scheduled" : "✅ Perfect! I've got it.",
                    description: isDuplicate 
                      ? "This reminder already exists. No duplicate created."
                      : "Your reminder is safely stored. I'll notify you on time!",
                    variant: "default",
                  });
                } catch (error: any) {
                  // 🔄 Rollback on error
                  setTaskConfirmed(false);
                  
                  if (error?.response?.data?.detail === "time_passed" || error?.message?.includes("time_passed")) {
                    setTaskTimePassed(true);
                    toast({
                      title: "⏰ Time Has Passed",
                      description: "The scheduled time has already passed. Please choose a future time.",
                      variant: "destructive",
                    });
                  } else {
                    toast({
                      title: "❌ Oops! Something went wrong.",
                      description: "I couldn't save that reminder. Please try again.",
                      variant: "destructive",
                    });
                  }
                }
              }}
              onCancel={async () => {
                hasUserRespondedRef.current = true;
                setTaskCancelled(true);
                
                const taskDesc = (action as any).payload?.description;
                if (taskDesc && currentChatId) {
                  await addMessage(currentChatId, {
                    role: "user",
                    content: "No, I want to change the time for this reminder",
                  });
                }
              }}
              onReschedule={() => setShowReschedule(true)}
            />
          )}
          
          {/* Rich action payloads (e.g., video) */}
          {!isThinking && action?.type === "video" && action.data?.url && (
            <div className="mt-2 sm:mt-3 w-full">
              <div className="aspect-video w-full overflow-hidden rounded-md border border-border/60 bg-black">
                <iframe
                  title="video-player"
                  src={action.data.url}
                  className="h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
          )}
          
          {/* Highlights Indicator - Right top corner, vertically stacked (lower) */}
          {message.highlights && message.highlights.length > 0 && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onOpenHighlights?.()}
                    className="absolute -right-1.5 sm:-right-2 top-7 sm:top-8 w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-gradient-to-br from-yellow-200 via-yellow-300 to-amber-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(252,211,77,0.5)] hover:shadow-[0_6px_20px_rgba(252,211,77,0.65)] hover:scale-110 transition-all border-[2px] sm:border-[2.5px] border-white/90 z-20"
                  >
                    <Highlighter className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-amber-700 drop-shadow-sm" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="left" className="text-xs py-1 px-2">
                  {message.highlights.length} Highlight{message.highlights.length > 1 ? 's' : ''}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Mini Agent Indicator - Right top corner, vertically stacked (upper) */}
        {hasMiniAgent && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <motion.button
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  whileHover={{ scale: 1.15, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                  transition={{ type: "spring", stiffness: 400, damping: 17 }}
                  onClick={onOpenMiniAgent}
                  className="absolute -right-1.5 sm:-right-2 -top-1.5 sm:-top-2 w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-gradient-to-br from-violet-200 via-purple-200 to-purple-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(196,181,253,0.5)] hover:shadow-[0_6px_20px_rgba(196,181,253,0.65)] transition-all border-[2px] sm:border-[2.5px] border-white/90 backdrop-blur-sm group z-20"
                >
                  <div className="relative">
                    <Bot className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-purple-700 drop-shadow-sm group-hover:drop-shadow-md transition-all" />
                    {/* Subtle pulse effect */}
                    <div className="absolute inset-0 rounded-full bg-white/30 animate-ping opacity-75" 
                      style={{ animationDuration: '2s' }} 
                    />
                  </div>
                </motion.button>
              </TooltipTrigger>
              <TooltipContent side="left" className="text-xs py-1 px-2">
                Mini-Agent
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        {/* AI Message Actions - only show when response is complete */}
        {!isUser && !isStreaming && !isThinking && message.content.trim() && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1, ease: "easeOut" }}
            className="flex items-center justify-start gap-1 sm:gap-1.5 mt-1 sm:mt-1.5 whitespace-nowrap overflow-x-auto opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Like" onClick={toggleLike}>
                    <ThumbsUp className={cn("w-3.5 h-3.5 sm:w-4 sm:h-4", liked ? "text-white" : "text-muted-foreground")} fill={liked ? "currentColor" : "none"} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Like</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon-sm" className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Dislike" onClick={toggleDislike}>
                      <ThumbsDown className={cn("w-3.5 h-3.5 sm:w-4 sm:h-4", disliked ? "text-red-400" : "text-muted-foreground")} fill={disliked ? "currentColor" : "none"} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Dislike</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon-sm" onClick={handleCopy} className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Copy">
                      {copied ? (
                        <span className="inline-flex items-center">
                          <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                        </span>
                      ) : (
                        <Copy className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Copy</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" onClick={handleSpeakToggle} className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label={isSpeaking ? "Stop" : "Speak"}>
                    {isSpeaking ? (
                      <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="6" y="6" width="12" height="12"/></svg>
                    ) : (
                      <Volume2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">{isSpeaking ? "Stop" : "Speak"}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Regenerate">
                    <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Regenerate</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </motion.div>
        )}

        {/* User Message Actions - On Hover */}
        {isUser && (
          <div className="flex items-center justify-end gap-1 sm:gap-1.5 mt-1 sm:mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap overflow-x-auto">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" onClick={handleCopy} className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground" aria-label="Copy">
                    {copied ? (
                      <span className="inline-flex items-center">
                        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                      </span>
                    ) : (
                      <Copy className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Copy</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1 sm:px-1.5 py-0.5 sm:py-1 rounded-md text-muted-foreground" aria-label="Edit">
                    <Pencil className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Edit</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>

      {/* Highlight Menu */}
      {menuPosition && selectedText && selectedRange && (
        <HighlightMenu
          position={menuPosition}
          selectedText={selectedText}
          menuRef={menuRef}
          isHighlighted={
            (message.highlights || []).some(
              (h) => h.startOffset === selectedRange.start && h.endOffset === selectedRange.end
            )
          }
          onClose={closeMenu}
          onHighlight={async (color) => {
            if (!selectedRange) return;
            
            const { currentChatId, addHighlight, removeHighlight } = useChatStore.getState();
            if (currentChatId && selectedRange.start >= 0 && selectedRange.end > selectedRange.start) {
              // If re-coloring an existing highlight, remove it first
              if (isRecoloring) {
                await removeHighlight(currentChatId, message.id, (h) => h.id === isRecoloring);
              }
              
              // Add new highlight (or re-add with new color)
              await addHighlight(currentChatId, message.id, {
                text: selectedText,
                color: color, // Use actual HEX color code from color picker
                startOffset: selectedRange.start,
                endOffset: selectedRange.end,
              });
            }
            closeMenu();
          }}
          onDeleteHighlight={async () => {
            if (!selectedRange) return;
            
            const { currentChatId, removeHighlight } = useChatStore.getState();
            if (currentChatId && selectedRange.start >= 0 && selectedRange.end > selectedRange.start) {
              await removeHighlight(currentChatId, message.id, (h) => 
                h.startOffset === selectedRange.start && h.endOffset === selectedRange.end
              );
            }
            closeMenu();
          }}
          onCreateMiniAgent={() => {
            onCreateMiniAgent(message.id, selectedText);
            closeMenu();
          }}
          onSpeak={() => {
            const u = new SpeechSynthesisUtterance(selectedText);
            speechSynthesis.cancel();
            speechSynthesis.speak(u);
            closeMenu();
          }}
          onCopy={() => {
            navigator.clipboard.writeText(selectedText);
          }}
          hasMiniAgent={hasMiniAgent}
          messageId={message.id}
        />
      )}
    </motion.div>
    {viewerOpen && (
      <div className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center">
        <button className="absolute top-3 right-3 text-white/90 text-xl" onClick={() => setViewerOpen(false)}>×</button>
        <button className="absolute left-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.max(0, i - 1))}>‹</button>
        <button className="absolute right-3 top-1/2 -translate-y-1/2 text-white/80 text-2xl" onClick={() => setViewerIndex((i) => Math.min(images.length - 1, i + 1))}>›</button>
        <div className="flex flex-col items-center gap-3">
          <img src={images[viewerIndex]?.url} alt="image" className="max-h-[80vh] w-auto object-contain rounded" style={{ transform: `scale(${zoom})` }} />
          <div className="flex items-center gap-3 text-white/80">
            <button className="px-3 py-1 bg-white/10 rounded" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}>-</button>
            <span>{Math.round(zoom * 100)}%</span>
            <button className="px-3 py-1 bg-white/10 rounded" onClick={() => setZoom((z) => Math.min(3, z + 0.25))}>+</button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for React.memo
  // Only re-render when these specific props change
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.highlights?.length === nextProps.message.highlights?.length &&
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.isThinking === nextProps.isThinking &&
    prevProps.hasMiniAgent === nextProps.hasMiniAgent
  );
});

MessageBubble.displayName = "MessageBubble";
