import { useEffect, useMemo, useState, useRef } from "react";
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
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { HighlightMenu } from "./HighlightMenu";
import { useChatStore } from "@/stores/chatStore";

interface MessageBubbleProps {
  message: Message;
  onCreateMiniAgent: (selectedText: string) => void;
  onAddHighlight: (color: string, text: string) => void; // Accept any HEX color code
  hasMiniAgent?: boolean;
  onOpenMiniAgent?: () => void;
  onOpenHighlights?: () => void;
  isStreaming?: boolean; // Actively receiving chunks
  isThinking?: boolean; // Waiting for first chunk (shows thinking state)
}

let currentUtterance: SpeechSynthesisUtterance | null = null;
let currentSpeakingId: string | null = null;

export const MessageBubble = ({
  message,
  onCreateMiniAgent,
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
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerIndex, setViewerIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [profileAvatar, setProfileAvatar] = useState<string | null>(null);
  const [profileName, setProfileName] = useState<string>("User");
  const tooltipSide = "bottom";
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);

  const { profile } = useProfileStore();

  useEffect(() => {
    setProfileAvatar(profile.avatarUrl || "");
    setProfileName(profile.name || "User");
  }, [profile]);

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
      console.error("Error calculating selection offsets:", error);
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
      setIsSpeaking(false);
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
    setIsSpeaking(true);
    currentUtterance.onend = () => {
      if (currentSpeakingId === message.id) {
        setIsSpeaking(false);
      }
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
   * Render text with highlights using a positional tree structure
   * Supports nested and overlapping highlights correctly
   */
  const renderWithHighlights = () => {
    const text = message.content;
    const highlights = message.highlights || [];
    
    if (highlights.length === 0) return text;
    
    // Sort highlights by start position, then by length (longer first for proper nesting)
    const sortedHighlights = [...highlights].sort((a, b) => {
      if (a.startOffset !== b.startOffset) {
        return a.startOffset - b.startOffset;
      }
      // If same start, longer highlight comes first (outer wrapper)
      return (b.endOffset - b.startOffset) - (a.endOffset - a.startOffset);
    });
    
    // Color mapping - matches HighlightMenu palette (12 colors)
    const colorMap: Record<string, string> = {
      yellow: "#FEF08A",
      green: "#BBF7D0",
      blue: "#BFDBFE",
      pink: "#FBCFE8",
      orange: "#FED7AA",
      purple: "#E9D5FF",
      teal: "#99F6E4",
      lime: "#D9F99D",
      rose: "#FECDD3",
      cyan: "#A5F3FC",
      amber: "#FDE68A",
      mint: "#A7F3D0",
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
      
      if (node.children.length === 0) {
        // Leaf node - just render highlighted text
        return (
          <span
            key={`${node.id}-${node.start}`}
            style={{ 
              backgroundColor: node.color.startsWith('#') ? node.color : (colorMap[node.color] || '#FEF08A'), 
              color: 'black' 
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
            backgroundColor: node.color.startsWith('#') ? node.color : (colorMap[node.color] || '#FEF08A'), 
            color: 'black' 
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
        "flex gap-3 group mb-4",
        isUser ? "flex-row-reverse self-end" : "self-start"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "w-8 h-8 rounded-full overflow-hidden flex items-center justify-center shrink-0 border border-border",
          isUser ? "bg-secondary" : "bg-secondary"
        )}
      >
        {isUser ? (
          profileAvatar ? (
            <img src={profileAvatar} alt={profileName} className="w-full h-full object-cover" />
          ) : (
            <span className="text-xs font-semibold">
              {(profileName || "U").trim().charAt(0).toUpperCase()}
            </span>
          )
        ) : (
          <img src="/pyramid.svg" alt="Prism" className="w-4 h-4" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          isUser
            ? "relative text-right max-w-[720px] w-fit sm:max-w-[720px]"
            : "relative text-left w-full max-w-none pr-[2.9rem]"
        )}
      > 
        <div
          className={cn(
            "inline-block rounded-[16px] text-[16px] leading-[1.5] break-words whitespace-pre-wrap font-[Inter,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif] [word-break:normal] [overflow-wrap:break-word] text-left [&_p]:mb-[6px] transition-all duration-150 ease-out",
            isUser
              ? "bg-secondary text-secondary-foreground px-[18px] py-[14px] ml-2 shadow-sm"
              : "text-foreground px-0 py-0"
          )}
          onMouseUp={handleMouseUp}
          data-message-content // Marker for selection offset calculation
        >
          {images.length > 0 && (
            <div className={cn("mb-3 grid gap-2", images.length === 1 ? "grid-cols-1" : images.length === 2 ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3") }>
              {images.map((img, idx) => (
                <button key={img.id} type="button" onClick={() => { setViewerIndex(idx); setZoom(1); setViewerOpen(true); }} className="block w-full overflow-hidden rounded-lg bg-secondary">
                  <img
                    src={img.thumbUrl || img.url}
                    alt={img.name}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-28 sm:h-36 object-cover"
                    sizes="(max-width: 640px) 45vw, 30vw"
                  />
                </button>
              ))}
            </div>
          )}
          {files.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {files.map((f) => (
                <a key={f.id} href={f.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-2 py-1 rounded-md bg-secondary text-xs border border-border hover:bg-secondary/80">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary" />
                  <span className="truncate max-w-[10rem]">{f.name}</span>
                </a>
              ))}
            </div>
          )}
          
          {/* Show thinking state when waiting for first chunk */}
          {isThinking && !isUser && (
            <div className="flex items-center gap-3 text-muted-foreground py-2">
              <TypingIndicator />
              <span className="text-sm">Thinking...</span>
            </div>
          )}
          
          {/* Show content when not thinking */}
          {!isThinking && renderWithHighlights()}
          
          {/* Streaming cursor - ONLY show while actively streaming */}
          {isStreaming && !isThinking && !isUser && message.content.length > 0 && (
            <span className="inline-block w-0.5 h-5 bg-primary ml-1 animate-pulse" />
          )}
          
          {/* Highlights Indicator - Right top corner, vertically stacked (lower) */}
          {message.highlights && message.highlights.length > 0 && (
            <button
              onClick={() => onOpenHighlights?.()}
              className="absolute -right-2 top-8 w-6 h-6 rounded-full bg-gradient-to-br from-yellow-200 via-yellow-300 to-amber-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(252,211,77,0.5)] hover:shadow-[0_6px_20px_rgba(252,211,77,0.65)] hover:scale-110 transition-all border-[2.5px] border-white/90 z-20"
              title={`${message.highlights.length} highlight${message.highlights.length > 1 ? 's' : ''}`}
            >
              <Highlighter className="w-3 h-3 text-amber-700 drop-shadow-sm" />
            </button>
          )}
        </div>

        {/* Mini Agent Indicator - Right top corner, vertically stacked (upper) */}
        {hasMiniAgent && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            whileHover={{ scale: 1.15, y: -2 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
            onClick={onOpenMiniAgent}
            className="absolute -right-2 -top-2 w-7 h-7 rounded-full bg-gradient-to-br from-violet-200 via-purple-200 to-purple-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(196,181,253,0.5)] hover:shadow-[0_6px_20px_rgba(196,181,253,0.65)] transition-all border-[2.5px] border-white/90 backdrop-blur-sm group z-20"
            title="Open Mini-Agent"
          >
            <div className="relative">
              <Bot className="w-3.5 h-3.5 text-purple-700 drop-shadow-sm group-hover:drop-shadow-md transition-all" />
              {/* Subtle pulse effect */}
              <div className="absolute inset-0 rounded-full bg-white/30 animate-ping opacity-75" 
                style={{ animationDuration: '2s' }} 
              />
            </div>
          </motion.button>
        )}

        {/* AI Message Actions - only show when streaming is complete */}
        {!isUser && !isStreaming && !isThinking && (
          <div className="flex items-center justify-start gap-1.5 mt-1.5 whitespace-nowrap overflow-x-auto opacity-50 hover:opacity-100 transition-opacity duration-200">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1.5 py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Like" onClick={toggleLike}>
                    <ThumbsUp className={cn("w-4 h-4", liked ? "text-white" : "text-muted-foreground")} fill={liked ? "currentColor" : "none"} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Like</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1.5 py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Dislike" onClick={toggleDislike}>
                    <ThumbsDown className={cn("w-4 h-4", disliked ? "text-red-400" : "text-muted-foreground")} fill={disliked ? "currentColor" : "none"} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Dislike</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" onClick={handleCopy} className="px-1.5 py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Copy">
                    {copied ? (
                      <span className="inline-flex items-center">
                        <svg className="w-4 h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                      </span>
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Copy</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" onClick={handleSpeakToggle} className="px-1.5 py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label={isSpeaking ? "Stop" : "Speak"}>
                    {isSpeaking ? (
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="6" y="6" width="12" height="12"/></svg>
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">{isSpeaking ? "Stop" : "Speak"}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1.5 py-1 rounded-md text-muted-foreground hover:bg-gray-700/40" aria-label="Regenerate">
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Regenerate</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* User Message Actions - On Hover */}
        {isUser && (
          <div className="flex items-center justify-end gap-1.5 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap overflow-x-auto">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" onClick={handleCopy} className="px-1.5 py-1 rounded-md text-muted-foreground" aria-label="Copy">
                    {copied ? (
                      <span className="inline-flex items-center">
                        <svg className="w-4 h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                      </span>
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side={tooltipSide} sideOffset={8} className="text-xs py-1 px-2">Copy</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon-sm" className="px-1.5 py-1 rounded-md text-muted-foreground" aria-label="Edit">
                    <Pencil className="w-4 h-4" />
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
          isHighlighted={() => {
            const highlights = message.highlights || [];
            return highlights.some(
              (h) => h.startOffset === selectedRange.start && h.endOffset === selectedRange.end
            );
          }}
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
            onCreateMiniAgent(selectedText);
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
};
