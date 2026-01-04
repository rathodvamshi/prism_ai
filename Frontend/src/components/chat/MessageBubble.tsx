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
  Brain,
  ChevronDown,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { HighlightMenu } from "./HighlightMenu";
import { useChatStore } from "@/stores/chatStore";
import { StreamingMessage } from "./StreamingMessage";
import { ActionCard, ActionCardState } from "./ActionCard";
import { MessageBlockParser } from "@/lib/messageBlockParser";
import { MessageBlockRenderer } from "./MessageBlockRenderer";

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

interface ThinkingAnimationProps {
  isVisible: boolean;
}

const ThinkingAnimation = ({ isVisible }: ThinkingAnimationProps) => {
  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-1.5 h-6 mb-2 ml-1"
    >
      <motion.div
        className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full"
        animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: 0 }}
      />
      <motion.div
        className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full"
        animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
      />
      <motion.div
        className="w-1.5 h-1.5 bg-muted-foreground/40 rounded-full"
        animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
      />
    </motion.div>
  );
};

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
  const [selectedRange, setSelectedRange] = useState<{ start: number; end: number } | null>(null);
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

  const [showThinking, setShowThinking] = useState(false);

  // Extract Thinking Data
  const { cleanContent, thinkingData } = useMemo(() => {
    if (!message.content) return { cleanContent: "", thinkingData: null };

    // Regex for the thinking data block
    const regex = /<!--THINKING_DATA:(.*?)-->/s;
    const match = message.content.match(regex);

    if (match) {
      try {
        const data = JSON.parse(match[1]);
        return {
          cleanContent: message.content.replace(match[0], "").trim(),
          thinkingData: data
        };
      } catch (e) {
        console.error("Failed to parse thinking data", e);
        return { cleanContent: message.content, thinkingData: null };
      }
    }
    return { cleanContent: message.content, thinkingData: null };
  }, [message.content]);

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

      // Check if selection is within a code block
      let element = range.commonAncestorContainer;

      // Traverse up the DOM tree to check for code block containers
      while (element && element.nodeType !== Node.DOCUMENT_NODE) {
        const currentElement = element.nodeType === Node.ELEMENT_NODE
          ? element as Element
          : element.parentElement;

        if (currentElement) {
          // Check for various code block indicators
          const tagName = currentElement.tagName?.toLowerCase();
          const className = currentElement.className || '';

          // Detect code blocks by:
          // 1. Direct code/pre tags
          // 2. Syntax highlighter components (react-syntax-highlighter)
          // 3. Code block specific classes and data attributes
          // 4. Common code syntax highlighting library classes
          if (tagName === 'code' ||
            tagName === 'pre' ||
            className.includes('language-') ||
            className.includes('hljs') ||
            className.includes('syntax-highlighter') ||
            className.includes('prism-code') ||
            className.includes('react-syntax-highlighter') ||
            className.includes('syntax-highlighter-code') ||
            className.includes('code-block-container') ||
            currentElement.hasAttribute('data-code-block') ||
            currentElement.closest('[data-code-block]') ||
            currentElement.closest('.language-') ||
            currentElement.closest('pre') ||
            currentElement.closest('.syntax-highlighter-code') ||
            currentElement.closest('.code-block-container')) {
            // Selection is within a code block - don't show highlight menu
            setSelectedText("");
            setSelectedRange(null);
            setMenuPosition(null);
            setIsRecoloring(null);
            return;
          }
        }

        element = element.parentNode;
      }

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
   * Parse message content into structured blocks
   * Memoized for performance
   */
  const messageBlocks = useMemo(() => {
    if (!cleanContent) {
      return [];
    }

    // For streaming messages, use StreamingMessage component (handles its own parsing)
    if (!isUser && (isStreaming || isThinking)) {
      return null; // Signal to use StreamingMessage
    }

    // Parse content into structured blocks
    return MessageBlockParser.parse(cleanContent);
  }, [cleanContent, isUser, isStreaming, isThinking]);

  /**
   * Render message content using structured blocks
   */
  const renderWithHighlights = () => {
    const highlights = message.highlights || [];

    // For AI messages that are streaming, use StreamingMessage component
    if (!isUser && (isStreaming || isThinking)) {
      return (
        <StreamingMessage
          content={message.content}
          isStreaming={isStreaming}
          isThinking={isThinking}
        />
      );
    }

    // For user messages, render as simple text with highlights
    if (isUser) {
      if (highlights.length === 0) {
        return <div className="whitespace-pre-wrap">{cleanContent}</div>;
      }
      // Parse and render with highlights
      const blocks = MessageBlockParser.parse(cleanContent);
      return <MessageBlockRenderer blocks={blocks} highlights={highlights} />;
    }

    // For completed AI messages, use structured block renderer
    if (messageBlocks) {
      return <MessageBlockRenderer blocks={messageBlocks} highlights={highlights} />;
    }

    return null;
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
          >
            {images.length > 0 && (
              <div className={cn("mb-2 sm:mb-3 grid gap-1.5 sm:gap-2", images.length === 1 ? "grid-cols-1" : images.length === 2 ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3")}>
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


            {/* Thinking Animation */}
            {!isUser && isThinking && (
              <ThinkingAnimation isVisible={true} />
            )}

            {/* Content Wrapper for Selection Accuracy */}
            <div
              onMouseUp={handleMouseUp}
              data-message-content
              className="relative"
            >
              {/* Render content with streaming support */}
              {renderWithHighlights()}
            </div>

            {/* 🧠 Thinking Transparency Dropdown - Responsive & Premium */}
            {!isUser && thinkingData && (
              <div className="mt-2 sm:mt-3 border-t border-border/60 pt-2 select-none w-full max-w-full">
                <button
                  onClick={() => setShowThinking(!showThinking)}
                  className="flex items-center gap-2 text-[10px] sm:text-xs text-muted-foreground hover:text-primary transition-colors font-medium mb-1 group w-full text-left py-1"
                >
                  <Brain className="w-3.5 h-3.5 sm:w-4 sm:h-4 group-hover:scale-110 transition-transform shrink-0" />
                  <span className="truncate">
                    How I understood this
                  </span>
                  {showThinking ? <ChevronDown className="w-3.5 h-3.5 shrink-0 ml-auto opacity-50" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0 ml-auto opacity-50" />}
                </button>

                <AnimatePresence>
                  {showThinking && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="bg-secondary/30 backdrop-blur-[2px] rounded-lg p-2.5 sm:p-3.5 text-xs space-y-3 sm:space-y-4 mt-1 border border-border/40 shadow-sm relative overflow-hidden">

                        {/* Decorative background element */}
                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl -z-10 translate-x-10 -translate-y-10" />

                        {/* Top Row: Intent & Emotion */}
                        <div className="grid grid-cols-2 gap-3 sm:gap-4">
                          {thinkingData.intent && (
                            <div className="flex flex-col gap-1 sm:gap-1.5 min-w-0">
                              <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 tracking-wider">Intent</span>
                              <div className="flex items-center">
                                <span className="text-foreground/90 font-medium capitalize truncate text-[11px] sm:text-xs">
                                  {thinkingData.intent}
                                </span>
                              </div>
                            </div>
                          )}
                          {thinkingData.emotion && (
                            <div className="flex flex-col gap-1 sm:gap-1.5 min-w-0">
                              <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 tracking-wider">Emotion</span>
                              <div className="flex items-center gap-1.5 sm:gap-2">
                                <span className={cn(
                                  "w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full animate-pulse shrink-0",
                                  thinkingData.emotion === "happiness" ? "bg-green-500" :
                                    thinkingData.emotion === "sadness" ? "bg-blue-500" :
                                      thinkingData.emotion === "anger" ? "bg-red-500" :
                                        "bg-gray-400"
                                )} />
                                <span className="text-foreground/90 font-medium capitalize truncate text-[11px] sm:text-xs">
                                  {thinkingData.emotion}
                                </span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Middle Row: Tone */}
                        {thinkingData.behavior_profile && (
                          <div className="flex flex-col gap-1.5 sm:gap-2">
                            <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 tracking-wider">Tone & Style</span>
                            <div className="flex flex-wrap gap-1.5 sm:gap-2">
                              {thinkingData.behavior_profile.tone && (
                                <span className="bg-primary/5 text-primary border border-primary/10 px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-medium whitespace-nowrap">
                                  {thinkingData.behavior_profile.tone}
                                </span>
                              )}
                              {thinkingData.behavior_profile.warmth !== undefined && (
                                <span className="bg-orange-500/5 text-orange-600/90 dark:text-orange-400 border border-orange-500/10 px-2 py-0.5 rounded-md text-[10px] sm:text-[11px] font-medium whitespace-nowrap">
                                  Warmth: {(thinkingData.behavior_profile.warmth * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Suggestions */}
                        {thinkingData.suggestions && thinkingData.suggestions.length > 0 && (
                          <div className="flex flex-col gap-2 pt-2 border-t border-border/30">
                            <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 tracking-wider flex items-center gap-1.5">
                              <Sparkles className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-yellow-500/80" />
                              Suggested Follow-ups
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {thinkingData.suggestions.map((suggestion: string, idx: number) => (
                                <button
                                  key={idx}
                                  onClick={() => {
                                    useChatStore.getState().sendMessageStream(currentChatId || "", suggestion, () => { }, () => { });
                                  }}
                                  className="text-left px-2 sm:px-3 py-1.5 rounded-lg bg-background/50 hover:bg-background border border-border/40 hover:border-primary/20 transition-all text-[10px] sm:text-xs text-foreground/80 hover:text-primary active:scale-95 shadow-sm hover:shadow"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Pipeline */}
                        <div className="flex flex-col gap-1.5 pt-1 opacity-50 hover:opacity-100 transition-opacity">
                          <span className="text-[9px] sm:text-[10px] uppercase font-bold text-muted-foreground/60 tracking-wider">Processing Pipeline</span>
                          <div className="flex flex-wrap gap-x-1 gap-y-1 items-center">
                            {(thinkingData.pipeline || []).map((step: string, i: number) => (
                              <div key={i} className="flex items-center gap-1">
                                <span className="text-[9px] sm:text-[10px] font-mono bg-background/30 px-1 rounded border border-border/20">{step}</span>
                                {i < (thinkingData.pipeline.length - 1) && <span className="text-muted-foreground/30 text-[9px]">›</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}


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
            {/* Highlights Indicator - Right top corner, vertically stacked (lower) */}
            {message.highlights && message.highlights.length > 0 && (
              <TooltipProvider delayDuration={200}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <motion.button
                      initial={{ scale: 0, opacity: 0, rotate: -20 }}
                      animate={{ scale: 1, opacity: 1, rotate: 0 }}
                      whileHover={{ scale: 1.15, y: -2 }}
                      whileTap={{ scale: 0.95 }}
                      transition={{ type: "spring", stiffness: 400, damping: 15 }}
                      onClick={() => onOpenHighlights?.()}
                      className="absolute -right-1.5 sm:-right-2 top-7 sm:top-8 w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-gradient-to-br from-yellow-200 via-yellow-300 to-amber-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(252,211,77,0.5)] hover:shadow-[0_6px_20px_rgba(252,211,77,0.65)] transition-all border-[2px] sm:border-[2.5px] border-white/90 z-20"
                    >
                      <Highlighter className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-amber-700 drop-shadow-sm" />
                    </motion.button>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="text-xs py-1 px-2">
                    {message.highlights.length} Highlight{message.highlights.length > 1 ? 's' : ''}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>

          {/* Mini Agent Indicator - Right top corner, vertically stacked (upper) */}
          {/* Mini Agent Indicator - Right top corner, vertically stacked (upper) */}
          {hasMiniAgent && (
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <motion.button
                    initial={{ scale: 0, opacity: 0, y: 10 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    whileHover={{ scale: 1.15, y: -3, rotate: 5 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ type: "spring", stiffness: 350, damping: 12 }}
                    onClick={onOpenMiniAgent}
                    className="absolute -right-1.5 sm:-right-2 -top-1.5 sm:-top-2 w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-gradient-to-br from-indigo-300 via-purple-300 to-pink-300 flex items-center justify-center shadow-[0_4px_14px_0_rgba(167,139,250,0.5)] hover:shadow-[0_6px_20px_rgba(167,139,250,0.65)] transition-all border-[2px] sm:border-[2.5px] border-white/90 backdrop-blur-sm group z-20"
                  >
                    <div className="relative flex items-center justify-center">
                      <Bot className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-indigo-700 drop-shadow-sm group-hover:drop-shadow-md transition-all" />
                      {/* Ring ripple effect - gentle and premium */}
                      <span className="absolute inset-0 rounded-full border border-purple-400/40 w-full h-full animate-[ping_2.5s_cubic-bezier(0,0,0.2,1)_infinite]" />
                    </div>
                  </motion.button>
                </TooltipTrigger>
                <TooltipContent side="left" className="text-xs py-1 px-2">
                  Open Mini-Agent
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
                          <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
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
                        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="6" y="6" width="12" height="12" /></svg>
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
                          <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
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
      </motion.div >
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
      )
      }
    </>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for React.memo
  // Only re-render when these specific props change
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.highlights === nextProps.message.highlights && // Reference equality check is sufficient as store creates new arrays
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.isThinking === nextProps.isThinking &&
    prevProps.hasMiniAgent === nextProps.hasMiniAgent &&
    // ✅ CRITICAL: Check mini-agent conversation state to trigger icon display
    prevProps.miniAgent?.hasConversation === nextProps.miniAgent?.hasConversation &&
    prevProps.miniAgent?.messages?.length === nextProps.miniAgent?.messages?.length
  );
});

MessageBubble.displayName = "MessageBubble";
