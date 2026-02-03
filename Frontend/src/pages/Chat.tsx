import React, { useState, useRef, useEffect, lazy, Suspense, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { useProfileStore } from "@/stores/profileStore";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { VirtualizedMessageList } from "@/components/chat/VirtualizedMessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { ConversationLoadingSkeleton } from "@/components/chat/LoadingSkeletons";
import { ConnectionStatus } from "@/components/chat/ConnectionStatus";
import { ChatErrorBoundary } from "@/components/chat/ChatErrorBoundary";
import { FreeLimitExceededPopup } from "@/components/FreeLimitExceededPopup";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

// ⚡ LAZY LOAD: Heavy components loaded only when needed
const MiniAgentPanel = lazy(() => import("@/components/chat/MiniAgentPanel"));
const HighlightsPanel = lazy(() => import("@/components/chat/HighlightsPanel"));
const CommandPalette = lazy(() => import("@/components/command/CommandPalette"));

// Loading fallbacks
import {
  PanelLoadingFallback,
  CommandPaletteLoadingFallback
} from "@/components/chat/LazyLoadingFallbacks";

import { Share, Bot, Loader2, MoreHorizontal, ChevronDown, ArrowDown, Check, Lock, PanelLeft, RefreshCw, AlertTriangle } from "lucide-react";
import { useIsMobile } from "@/hooks/use-mobile";
import { usePageLoadMetrics, usePerformanceMonitor } from "@/hooks/usePerformanceMonitor";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { useNavigate, useParams } from "react-router-dom";
import type { Message } from "@/types/chat";

const models = [
  { id: "llama-3.3-70b-versatile", name: "Llama 3.3 70B", available: true },
  { id: "llama-3.1-8b-instant", name: "Llama 3.1 8B (Fast)", available: true },
  { id: "mixtral-8x7b-32768", name: "Mixtral 8x7B", available: true },
];

const Chat = () => {
  // ⚡ Performance monitoring (development only)
  usePageLoadMetrics();
  usePerformanceMonitor('Chat', process.env.NODE_ENV === 'development');

  const { sessionId } = useParams<{ sessionId?: string }>();
  const [isRestoring, setIsRestoring] = useState(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const [hasNewMessages, setHasNewMessages] = useState(false); // Track new messages while scrolled up
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isUserAtBottomRef = useRef(true); // Track if user is at bottom
  const lastScrollTopRef = useRef(0); // Track scroll direction
  const justCreatedSessionRef = useRef<string | null>(null); // Track newly created session to skip reload
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const [headerModel, setHeaderModel] = useState(models[0]);
  const [resetSignal, setResetSignal] = useState(0);
  const [forceScrollSignal, setForceScrollSignal] = useState(0); // 🆕 Signal for VirtualizedMessageList
  const [isSpeakingGlobal, setIsSpeakingGlobal] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [includeHighlights, setIncludeHighlights] = useState(true);
  const [sharePayload, setSharePayload] = useState<string>("");
  const [activeHighlightsMessageId, setActiveHighlightsMessageId] = useState<string | null>(null);

  const { toast } = useToast();

  const {
    chats,
    currentChatId,
    isDraftSession,
    isCreatingSession,
    miniAgents,
    activeMiniAgentId,
    addMessage,
    createSessionIfNeeded,
    createMiniAgent,
    updateMiniAgentSnippet,
    setActiveMiniAgent,
    addHighlight,
    loadChatsFromBackend,
    loadSessionData,
    setCurrentChat,
    isSendingMessage,
    isStreaming,
    isLoadingChats,
    sidebarExpanded,
    freeLimitExceeded,
    limitExceededType,
    setFreeLimitExceeded,
    lastFailedMessage,
    clearLastFailedMessage,
    retryLastFailedMessage,
  } = useChatStore();

  const currentChat = chats.find((c) => c.id === currentChatId);

  // Get current message from store (reactive to updates)
  const activeHighlightsMessage = activeHighlightsMessageId
    ? currentChat?.messages.find((m) => m.id === activeHighlightsMessageId)
    : null;

  // Auto-close logic: When one panel opens, close the other
  useEffect(() => {
    if (activeMiniAgentId && activeHighlightsMessageId) {
      // If mini-agent opens while highlights is open, close highlights
      setActiveHighlightsMessageId(null);
    }
  }, [activeMiniAgentId]);

  useEffect(() => {
    if (activeHighlightsMessageId && activeMiniAgentId) {
      // If highlights opens while mini-agent is open, close mini-agent
      setActiveMiniAgent(null);
    }
  }, [activeHighlightsMessageId]);

  // 🧠 Preload MiniAgentPanel after idle for faster first open
  useEffect(() => {
    const idle = (window as any).requestIdleCallback || ((fn: any) => setTimeout(fn, 600));
    const cancelIdle = (window as any).cancelIdleCallback || clearTimeout;
    const handle = idle(() => {
      import("@/components/chat/MiniAgentPanel").catch(() => { });
    });
    return () => cancelIdle(handle);
  }, []);

  // Auto-close highlights panel when the message is deleted (not when highlights are empty)
  useEffect(() => {
    if (activeHighlightsMessageId && !activeHighlightsMessage) {
      // Message no longer exists - close panel
      setActiveHighlightsMessageId(null);
    }
  }, [activeHighlightsMessage, activeHighlightsMessageId]);



  // 🔍 Debug: Log mini-agents state when it changes
  useEffect(() => {
    if (import.meta.env.DEV && miniAgents.length > 0) {
      console.log('🤖 [Chat] miniAgents updated:', miniAgents.map(a => ({
        id: a.id?.slice(0, 20) + '...',
        messageId: a.messageId?.slice(0, 8) + '...',
        hasConversation: a.hasConversation,
        messagesCount: a.messages?.length
      })));
    }
  }, [miniAgents]);

  useEffect(() => {
    if (currentChat && currentChat.messages.length === 0) {
      setResetSignal((s) => s + 1);
      if (scrollRef.current) {
        scrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  }, [currentChatId]);

  // GPT-Style scroll tracking with debouncing
  useEffect(() => {
    const scrollElement = scrollRef.current;
    if (!scrollElement) return;

    let scrollTimeout: NodeJS.Timeout | null = null;

    const handleScroll = () => {
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      scrollTimeout = setTimeout(() => {
        const { scrollTop, scrollHeight, clientHeight } = scrollElement;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

        // User is "at bottom" if they are within 150px (even more forgiving for smooth experience)
        const isAtBottom = distanceFromBottom < 150;

        // Detect scroll direction
        const isScrollingUp = scrollTop < lastScrollTopRef.current;
        lastScrollTopRef.current = scrollTop;

        // Smart Lock Logic:
        // 1. If at bottom, LOCK and clear new message indicator
        // 2. If scrolling UP and NOT at bottom, UNLOCK
        // 3. If scrolling DOWN, don't change lock (let them return to bottom)

        if (isAtBottom) {
          isUserAtBottomRef.current = true;
          setShowScrollToBottom(false);
          setHasNewMessages(false); // Clear new message indicator when at bottom
        } else if (isScrollingUp) {
          isUserAtBottomRef.current = false;
          // Show jump button if scrolled up more than 150px (ChatGPT-style threshold)
          if (distanceFromBottom > 150) {
            setShowScrollToBottom(true);
          }
        } else {
          // Scrolling down but not at bottom yet - still show button
          if (distanceFromBottom > 150) {
            setShowScrollToBottom(true);
          }
        }
      }, 8); // ~120fps for ultra-smooth detection
    };

    scrollElement.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      scrollElement.removeEventListener('scroll', handleScroll);
      if (scrollTimeout) clearTimeout(scrollTimeout);
    };
  }, []); // Ref dependency handled by effect lifecycle

  // Track new messages while user is scrolled up
  useEffect(() => {
    if (currentChat?.messages?.length && !isUserAtBottomRef.current && showScrollToBottom) {
      setHasNewMessages(true);
    }
  }, [currentChat?.messages?.length, showScrollToBottom]);

  // � NO AUTO-SCROLL during streaming
  // User controls scroll manually. Only show "scroll to bottom" button if they scroll up.
  // This prevents page jumping/blinking during response generation.

  // Initial scroll handling - scroll to bottom when session is loaded
  useEffect(() => {
    if (currentChat && currentChat.messages.length > 0 && !isRestoring && !isLoadingChats) {
      // Allow DOM to paint first, then scroll to bottom
      const scrollTimer = setTimeout(() => {
        isUserAtBottomRef.current = true;
        if (scrollRef.current) {
          const { scrollHeight, clientHeight } = scrollRef.current;
          scrollRef.current.scrollTo({ top: scrollHeight - clientHeight, behavior: "auto" });
        }
        // Also use bottomRef as backup
        bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
      }, 50); // Reduced delay for snappier feel

      return () => clearTimeout(scrollTimer);
    }
  }, [currentChatId, resetSignal, isRestoring, isLoadingChats, currentChat?.messages?.length]);


  const scrollToBottom = () => {
    isUserAtBottomRef.current = true;
    setShowScrollToBottom(false);
    setHasNewMessages(false);

    // Smooth scroll with force signal for VirtualizedMessageList
    setForceScrollSignal(prev => prev + 1);

    // Fallback for non-virtualized views (loading/empty)
    if (scrollRef.current) {
      const { scrollHeight, clientHeight } = scrollRef.current;
      scrollRef.current.scrollTo({
        top: scrollHeight - clientHeight,
        behavior: "smooth"
      });
    }
    // Backup: use bottomRef
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  };

  // Keyboard shortcut: End key to scroll to bottom
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // End key or Ctrl+End to scroll to bottom
      if (e.key === 'End' || (e.ctrlKey && e.key === 'End')) {
        if (showScrollToBottom) {
          e.preventDefault();
          scrollToBottom();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showScrollToBottom]);

  // Hydrate store and show skeleton while restoring
  useEffect(() => {
    let cancelled = false;

    // Load session data from URL parameter if present
    const loadSession = async () => {
      // Reset isRestoring when sessionId changes (show loading state)
      if (sessionId) {
        setIsRestoring(true);
      }

      try {
        if (sessionId) {
          // Skip reload if we just created this session (optimistic update is already in place)
          if (justCreatedSessionRef.current === sessionId) {
            console.log('⏭️ Skipping reload for just-created session:', sessionId);
            justCreatedSessionRef.current = null; // Clear the flag
            setIsRestoring(false);
            return;
          }

          // Check if session already loaded in state (prevent duplicate loads)
          const existingChat = chats.find(c => c.id === sessionId);
          const hasMessages = existingChat && existingChat.messages && existingChat.messages.length > 0;

          if (hasMessages && !cancelled) {
            // Session already loaded - just set as current
            setCurrentChat(sessionId);
            setIsRestoring(false);
            return;
          }

          // Load from backend
          if (!cancelled) {
            await loadSessionData(sessionId);
            setCurrentChat(sessionId);
            // Set isRestoring to false after data is loaded
            setIsRestoring(false);
          }
        } else {
          // No session ID in URL - we're in draft mode or viewing chat list
          // Set isRestoring to false immediately since there's nothing to restore
          setIsRestoring(false);

          // Load all chats if empty
          if (chats.length === 0 && !cancelled) {
            await loadChatsFromBackend();
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load session:', error);

          // Check for 404 Not Found or specific error message
          const isNotFound = (error as any)?.message?.includes('404') ||
            (error as any)?.message?.includes('not found') ||
            (error as any)?.status === 404;

          if (isNotFound) {
            toast({
              title: "Session not found",
              description: "The chat session provided does not exist or has been deleted.",
              variant: "destructive",
            });
            // Navigate to root to start fresh
            navigate('/chat', { replace: true });
            setIsRestoring(false);
            return;
          }

          toast({
            title: "Failed to load chat",
            description: "Could not load the requested chat session. Retrying...",
            variant: "destructive",
          });

          // Retry once after 1 second for non-404 errors
          setTimeout(() => {
            if (!cancelled && sessionId) {
              loadSessionData(sessionId).then(() => {
                setCurrentChat(sessionId);
                setIsRestoring(false);
              }).catch(err => {
                console.error('Retry failed:', err);
                setIsRestoring(false);
              });
            }
          }, 1000);

          // Also set isRestoring false after scheduling retry
          setIsRestoring(false);
        }
      }
    };

    loadSession();

    // Cleanup function to prevent state updates after unmount
    return () => {
      cancelled = true;
    };
  }, [sessionId]); // Re-run when sessionId changes

  // Track global speech state for showing Stop button
  useEffect(() => {
    const interval = setInterval(() => {
      try {
        setIsSpeakingGlobal(speechSynthesis.speaking);
      } catch { }
    }, 250);
    return () => clearInterval(interval);
  }, []);

  const stopAllSpeech = () => {
    try {
      speechSynthesis.cancel();
      setIsSpeakingGlobal(false);
    } catch { }
  };

  const handleSend = async (message: string, attachments?: any[]) => {
    // Validate message - don't create session for empty/trivial input
    const trimmedMessage = message.trim();
    if (!trimmedMessage || trimmedMessage.length < 1) {
      return;
    }

    let targetId = currentChatId;
    let isNewSession = false;

    // If in draft mode or no current chat, create session NOW (on first real message)
    if (!targetId || isDraftSession) {
      console.log('🆕 Creating session on first message...');

      // Clear restoring state since we're creating, not restoring
      setIsRestoring(false);

      try {
        // createSessionIfNeeded now handles isCreatingSession state internally
        targetId = await createSessionIfNeeded();
        isNewSession = true;
      } catch (error) {
        console.error('Failed to create session:', error);
        toast({
          title: "Error",
          description: "Failed to create chat session. Please try again.",
          variant: "destructive",
        });
        return;
      }
    }

    if (!targetId) {
      toast({
        title: "Error",
        description: "Failed to create chat session. Please try again.",
        variant: "destructive",
      });
      return;
    }

    try {
      // addMessage from chatStore handles:
      // 1. Optimistic user message update
      // 2. API call to backend
      // 3. Backend response handling
      // 4. AI response addition
      // All in one call - no duplicate API calls

      // Start the message sending - this adds the optimistic update
      const messagePromise = addMessage(targetId, { role: "user", content: message, attachments });

      // If this was a new session, navigate AFTER optimistic update is in place
      if (isNewSession && targetId) {
        // Mark this session as just-created to skip reload on navigation
        justCreatedSessionRef.current = targetId;

        // Small delay to ensure state update propagates before navigation
        await new Promise(resolve => setTimeout(resolve, 50));

        // Navigate to the new session URL with smooth transition
        // Use replace to avoid back button going to empty /chat
        navigate(`/chat/${targetId}`, { replace: true });
      }

      // Wait for message to complete
      await messagePromise;
    } catch (error) {
      console.error("Error sending message:", error);

      toast({
        title: "Connection Error",
        description: "Unable to connect to the AI service. Please check your connection.",
        variant: "destructive",
      });
    }
  };

  const handleRetryMessage = async () => {
    if (!lastFailedMessage) return;

    try {
      await retryLastFailedMessage();
      toast({
        title: "Message Sent",
        description: "Your message was successfully resent.",
      });
    } catch (error) {
      toast({
        title: "Retry Failed",
        description: "Unable to send the message. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleCreateMiniAgent = async (messageId: string, selectedText: string) => {
    try {
      // Check if Mini Agent already exists for this message
      const existingAgent = miniAgents.find(a => a.messageId === messageId);

      if (existingAgent) {
        console.log('♻️ Mini Agent exists for this message:', existingAgent.id);
        console.log('📌 Current active agent:', activeMiniAgentId);
        console.log('📝 New selected text:', selectedText.substring(0, 50) + '...');

        // If agent is already open, just update the snippet
        if (activeMiniAgentId === existingAgent.id) {
          console.log('✅ Agent is OPEN - Updating snippet directly');
          await updateMiniAgentSnippet(existingAgent.id, selectedText);
          console.log('✅ Snippet updated successfully');
        } else {
          console.log('📂 Agent exists but CLOSED - Reopening with new snippet');
          // If agent exists but not open, reuse it (backend will update snippet)
          await createMiniAgent(messageId, selectedText);
        }
      } else {
        console.log('🆕 No existing agent - Creating new one');
        // No existing agent, create new one
        await createMiniAgent(messageId, selectedText);
      }
    } catch (error) {
      console.error("❌ Failed to create/update mini-agent:", error);
    }
  };

  const handleAddHighlight = (
    messageId: string,
    color: "yellow" | "green" | "blue" | "pink",
    text: string
  ) => {
    if (currentChatId) {
      addHighlight(currentChatId, messageId, {
        text,
        color,
        startIndex: 0,
        endIndex: text.length,
      });
    }
  };

  const getMiniAgentByMessage = useCallback((messageId: string) => {
    return miniAgents.find(a => a.messageId === messageId);
  }, [miniAgents]);

  const handleTextHighlight = useCallback((messageId: string, text: string, startIndex: number, endIndex: number) => {
    if (currentChatId) {
      addHighlight(currentChatId, messageId, {
        text,
        color: "yellow",
        startIndex,
        endIndex
      });
    }
  }, [currentChatId, addHighlight]);

  const handleVirtualScrollStateChange = useCallback((isAtBottom: boolean) => {
    setShowScrollToBottom(!isAtBottom);
  }, []);

  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);

  const handleSpeak = useCallback((messageId: string, text: string) => {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => {
      setPlayingMessageId(null);
      setIsSpeakingGlobal(false);
    };
    utterance.onerror = () => {
      setPlayingMessageId(null);
      setIsSpeakingGlobal(false);
    };
    setPlayingMessageId(messageId);
    setIsSpeakingGlobal(true);
    speechSynthesis.speak(utterance);
  }, []);

  const handleStopSpeaking = useCallback(() => {
    speechSynthesis.cancel();
    setPlayingMessageId(null);
    setIsSpeakingGlobal(false);
  }, []);

  return (
    <ChatErrorBoundary>
      <div className="flex h-screen min-h-0 overflow-hidden bg-background">
        <ConnectionStatus />
        <ChatSidebar />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 relative">
          {/* Header */}
          <header className={cn(
            "absolute top-0 left-0 right-0 h-14 flex items-center justify-between gap-2 px-3 sm:px-4 z-10 transition-all duration-200 ease-in-out",
            sidebarExpanded && !isMobile
              ? "bg-background border-b border-border shadow-sm"
              : "bg-transparent border-b border-transparent"
          )}>
            <div className="flex items-center gap-2 min-w-0 flex-1">
              {isMobile && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground mr-1"
                  onClick={() => useChatStore.getState().toggleSidebar()}
                >
                  <MoreHorizontal className="w-5 h-5" />
                </Button>
              )}
              {/* Title area: desktop shows project name; mobile shows just PRISM title */}
              {false ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-1 text-xs text-muted-foreground truncate"
                    >
                      {headerModel.name}
                      <ChevronDown className="w-3 h-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {models.map((m) => (
                      <DropdownMenuItem
                        key={m.id}
                        onClick={() => {
                          if (m.available) {
                            setHeaderModel(m);
                          } else {
                            toast({
                              title: "Model Unavailable",
                              description: "This model requires a premium subscription.",
                            });
                          }
                        }}
                        className={cn("gap-2", !m.available && "opacity-60")}
                      >
                        {m.available ? (
                          <Check className="w-4 h-4 text-success" />
                        ) : (
                          <Lock className="w-4 h-4 text-muted-foreground" />
                        )}
                        {m.name}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <h2
                  aria-label="Prism"
                  className={cn(
                    "font-bold tracking-tight leading-none truncate transition-all duration-300",
                    sidebarExpanded ? "text-lg sm:text-xl" : "text-base sm:text-lg",
                    // Subtle gradient for simple, beautiful look
                    "bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent"
                  )}
                >
                  Prism
                </h2>
              )}
            </div>
            <div className="flex items-center gap-1 sm:gap-2 shrink-0">
              {/* New Chat */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-muted-foreground"
                      aria-label="New Chat"
                      onClick={() => {
                        // Enter draft mode - NO backend call
                        useChatStore.getState().startDraftSession();
                        navigate('/chat');
                      }}
                    >
                      <span className="sr-only">New Chat</span>
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                    </Button>
                  </TooltipTrigger>
                  {!isMobile && <TooltipContent side="bottom">New Chat</TooltipContent>}
                </Tooltip>
              </TooltipProvider>

              {/* Share */}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-muted-foreground"
                      aria-label="Share"
                      onClick={() => {
                        const chatId = currentChatId;
                        if (!chatId || !currentChat) return;
                        const base: any = {
                          chatId,
                          messages: currentChat.messages.map((m) => ({ id: m.id, role: m.role, content: m.content })),
                        };
                        // Build payload preview; link generated on Copy/Open
                        setSharePayload(JSON.stringify(base, null, 2));
                        setShareOpen(true);
                      }}
                    >
                      <Share className="w-4 h-4 sm:w-5 sm:h-5" />
                    </Button>
                  </TooltipTrigger>
                  {!isMobile && <TooltipContent side="bottom">Share</TooltipContent>}
                </Tooltip>
              </TooltipProvider>

              {/* Global Stop Speech */}
              {isSpeakingGlobal && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-muted-foreground"
                        onClick={stopAllSpeech}
                      >
                        <svg className="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="6" y="6" width="12" height="12" /></svg>
                      </Button>
                    </TooltipTrigger>
                    {!isMobile && <TooltipContent side="bottom">Stop Speech</TooltipContent>}
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </header>

          {/* Messages - ⚡ VIRTUALIZED for performance */}
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            {/* Determine which view to show - MUTUALLY EXCLUSIVE */}
            {(() => {
              // Priority 1: Loading states
              if (isLoadingChats) {
                return (
                  <ScrollArea className="flex-1 h-full scroll-smooth will-change-scroll" viewportRef={scrollRef}>
                    <div className="w-full max-w-[850px] mx-auto pt-16 sm:pt-24 pb-4 sm:pb-10 px-4 pl-6 sm:pl-8 lg:pl-12">
                      <ConversationLoadingSkeleton />
                    </div>
                  </ScrollArea>
                );
              }

              // Priority 2: Restoring state
              if (isRestoring) {
                return (
                  <ScrollArea className="flex-1 h-full scroll-smooth will-change-scroll" viewportRef={scrollRef}>
                    <div className="w-full max-w-[850px] mx-auto pt-16 sm:pt-24 pb-4 sm:pb-10 px-4 pl-6 sm:pl-8 lg:pl-12">
                      <div className="space-y-4">
                        <div className="h-6 w-32 sm:w-40 bg-muted animate-pulse rounded" />
                        <div className="space-y-2">
                          <div className="h-4 w-full bg-muted animate-pulse rounded" />
                          <div className="h-4 w-2/3 bg-muted animate-pulse rounded" />
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                );
              }

              // Priority 3: Creating session
              if (isCreatingSession) {
                return (
                  <ScrollArea className="flex-1 h-full scroll-smooth will-change-scroll" viewportRef={scrollRef}>
                    <div className="w-full max-w-[850px] mx-auto pt-16 sm:pt-24 pb-4 sm:pb-10 px-4 pl-6 sm:pl-8 lg:pl-12">
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.2 }}
                        className="flex flex-col items-center justify-center py-16 gap-4"
                      >
                        <div className="relative">
                          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Loader2 className="w-6 h-6 text-primary animate-spin" />
                          </div>
                          <motion.div
                            className="absolute inset-0 rounded-full border-2 border-primary/30"
                            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                          />
                        </div>
                        <p className="text-sm text-muted-foreground">Setting up your chat...</p>
                      </motion.div>
                    </div>
                  </ScrollArea>
                );
              }

              // Priority 4: Show messages if we have them
              if (currentChat && currentChat.messages && currentChat.messages.length > 0) {
                return (
                  <div className="flex-1 min-h-0 relative">
                    <VirtualizedMessageList
                      messages={currentChat.messages}
                      onHighlight={handleTextHighlight}
                      onCreateMiniAgent={handleCreateMiniAgent}
                      onOpenMiniAgent={setActiveMiniAgent}
                      getMiniAgentByMessage={getMiniAgentByMessage}
                      onOpenHighlightsPanel={(id) => setActiveHighlightsMessageId(id)}
                      activeHighlightsMessageId={activeHighlightsMessageId}
                      isSpeaking={playingMessageId}
                      onSpeak={handleSpeak}
                      onStopSpeaking={handleStopSpeaking}
                      scrollToBottom={!showScrollToBottom}
                      onScrollStateChange={handleVirtualScrollStateChange}
                      isStreamingLogic={isStreaming}
                      isSendingMessage={isSendingMessage}
                      forceScrollSignal={forceScrollSignal}
                    />
                  </div>
                );
              }

              // Priority 5: Empty welcome (draft mode or no messages)
              return (
                <ScrollArea className="flex-1 h-full scroll-smooth will-change-scroll" viewportRef={scrollRef}>
                  <div className="w-full max-w-[850px] mx-auto pt-16 sm:pt-24 pb-4 sm:pb-10 px-4 pl-6 sm:pl-8 lg:pl-12">
                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                      className="py-8 sm:py-16"
                    >
                      <EmptyWelcome onSend={handleSend} />
                    </motion.div>
                  </div>
                </ScrollArea>
              );
            })()}

          </div>

          {/* Input with scroll button positioned above it */}
          <div className="relative">
            {/* Jump to latest button - Clean & Simple */}
            <AnimatePresence>
              {showScrollToBottom && (
                <motion.button
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.2 }}
                  onClick={scrollToBottom}
                  aria-label="Jump to latest message"
                  className={cn(
                    "absolute z-20 left-1/2 -translate-x-1/2",
                    "-top-14", // Position above input box
                    "w-10 h-10", // 40px circular button
                    "flex items-center justify-center",
                    "rounded-full",
                    "bg-background border border-border",
                    "shadow-sm",
                    "text-muted-foreground",
                    "hover:bg-accent hover:text-foreground hover:border-primary/30",
                    "active:scale-95",
                    "transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
                    "cursor-pointer"
                  )}
                >
                  <ArrowDown className="w-5 h-5" />

                  {/* New message indicator dot */}
                  {hasNewMessages && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full border-2 border-background"
                    />
                  )}
                </motion.button>
              )}
            </AnimatePresence>

            {/* Error Recovery Banner */}
            <AnimatePresence>
              {lastFailedMessage && lastFailedMessage.chatId === currentChatId && (
                <motion.div
                  initial={{ opacity: 0, y: 10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, y: 10, height: 0 }}
                  className="mb-2 mx-4"
                >
                  <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-destructive/10 border border-destructive/20">
                    <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
                    <span className="text-sm text-destructive flex-1 truncate">
                      Message failed to send
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                        onClick={clearLastFailedMessage}
                      >
                        Dismiss
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 px-3 text-xs border-destructive/30 text-destructive hover:bg-destructive/10"
                        onClick={handleRetryMessage}
                        disabled={isSendingMessage || isStreaming}
                      >
                        {isSendingMessage ? (
                          <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3 mr-1.5" />
                        )}
                        Retry
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <ChatInput
              onSend={handleSend}
              isLoading={isSendingMessage || isStreaming}
              resetSignal={resetSignal}
            />
          </div>
        </div>

        {/* ⚡ LAZY: Mini Agent Panel */}
        {activeMiniAgentId && (
          <Suspense fallback={<PanelLoadingFallback />}>
            <MiniAgentPanel />
          </Suspense>
        )}

        {/* ⚡ LAZY: Highlights Panel */}
        {activeHighlightsMessage && (
          <Suspense fallback={<PanelLoadingFallback />}>
            <HighlightsPanel
              highlights={activeHighlightsMessage.highlights || []}
              onClose={() => setActiveHighlightsMessageId(null)}
              onUpdateNote={async (highlightId, note) => {
                if (currentChatId && activeHighlightsMessage) {
                  await useChatStore.getState().updateHighlightNote(currentChatId, activeHighlightsMessage.id, highlightId, note);
                }
              }}
              onDeleteNote={async (highlightId) => {
                if (currentChatId && activeHighlightsMessage) {
                  await useChatStore.getState().updateHighlightNote(currentChatId, activeHighlightsMessage.id, highlightId, "");
                }
              }}
              onDeleteHighlight={async (highlightId) => {
                if (currentChatId && activeHighlightsMessage) {
                  await useChatStore.getState().removeHighlight(currentChatId, activeHighlightsMessage.id, (h) => h.id === highlightId);
                }
              }}
            />
          </Suspense>
        )}

        {/* ⚡ LAZY: Command Palette */}
        <Suspense fallback={<CommandPaletteLoadingFallback />}>
          <CommandPalette />
        </Suspense>
        {/* Share Dialog */}
        <Dialog open={shareOpen} onOpenChange={setShareOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Share Conversation</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={includeHighlights}
                  onChange={(e) => setIncludeHighlights(e.target.checked)}
                />
                Include highlights in shared version
              </label>
              <div className="text-xs text-muted-foreground">
                Copy payload to share or send to backend later.
              </div>
              <pre className="bg-card border border-border rounded p-2 text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                {sharePayload}
              </pre>
            </div>
            <DialogFooter>
              <Button
                variant="ghost"
                onClick={() => setShareOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (!currentChatId || !currentChat) return;
                  const base: any = {
                    chatId: currentChatId,
                    messages: currentChat.messages.map((m) => ({ id: m.id, role: m.role, content: m.content })),
                  };
                  if (includeHighlights) {
                    // Highlights are now stored in message highlights array
                    const highlights: any[] = [];
                    currentChat.messages.forEach(msg => {
                      if (msg.highlights) {
                        msg.highlights.forEach(h => {
                          highlights.push({ msgId: msg.id, highlight: h });
                        });
                      }
                    });
                    if (highlights.length > 0) {
                      const json = JSON.stringify(highlights);
                      const compressed = btoa(unescape(encodeURIComponent(json)));
                      base.highlights = compressed;
                    }
                  }
                  const final = JSON.stringify(base);
                  const base64 = btoa(unescape(encodeURIComponent(final)));
                  const link = `${window.location.origin}/share.html#${base64}`;
                  try {
                    navigator.clipboard.writeText(link);
                    toast({ title: "Link copied", description: "Shareable link copied to clipboard." });
                    setShareOpen(false);
                  } catch { }
                }}
              >
                Copy Link
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Free Limit Exceeded Popup */}
      <FreeLimitExceededPopup
        open={freeLimitExceeded}
        onOpenChange={setFreeLimitExceeded}
        exceededType={limitExceededType}
        onKeyAdded={() => {
          // Key was added successfully, user can continue chatting
          setFreeLimitExceeded(false);
        }}
      />
    </ChatErrorBoundary>
  );
};

export default Chat;

const EmptyWelcome: React.FC<{ onSend: (text: string) => void }> = ({ onSend }) => {
  const { profile } = useProfileStore();
  const name = profile.name;

  const starterTiles = [
    { title: "Project Brainstorm", desc: "Ideas for my next big project", icon: "🚀", color: "from-blue-500/20 to-cyan-500/20" },
    { title: "Code Architect", desc: "Design a scalable app architecture", icon: "💻", color: "from-purple-500/20 to-indigo-500/20" },
    { title: "Deep Explanation", desc: "Explain quantum physics like I'm five", icon: "🔬", color: "from-amber-500/20 to-orange-500/20" },
    { title: "Creative Writing", desc: "Write a sci-fi story set on Mars", icon: "🖋️", color: "from-rose-500/20 to-pink-500/20" },
    { title: "Study Buddy", desc: "Help me memorize these concepts", icon: "📚", color: "from-green-500/20 to-teal-500/20" },
    { title: "Data Analyst", desc: "Analyze this trend for insights", icon: "📊", color: "from-teal-500/20 to-emerald-500/20" },
  ];

  return (
    <div className="max-w-4xl mx-auto text-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="inline-flex items-center gap-2 rounded-full px-4 py-2 mb-8 bg-primary/5 border border-primary/10 backdrop-blur-sm">
          <Bot className="w-4 h-4 text-primary" />
          <span className="text-xs font-semibold tracking-wider text-primary uppercase">Prism Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground mb-4 leading-tight">
          Welcome back{name ? `, ${name.split(' ')[0]}` : ""} <span className="inline-block animate-[wave_2s_ease-in-out_infinite]">👋</span>
        </h1>

        <p className="text-xl text-muted-foreground/80 max-w-xl mx-auto mb-16 leading-relaxed">
          I'm your personal AI partner, ready to help you create, learn, and build anything you can imagine.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-left">
          {starterTiles.map((tile, i) => (
            <motion.button
              key={tile.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 + (i * 0.05) }}
              onClick={() => onSend(tile.desc)}
              className={cn(
                "group relative p-6 rounded-2xl border border-border/50 bg-card/30 backdrop-blur-md",
                "hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-1 transition-all duration-300",
                "overflow-hidden cursor-pointer"
              )}
            >
              <div className={cn("absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity", tile.color)} />
              <div className="text-3xl mb-4 transform group-hover:scale-110 transition-transform duration-300">{tile.icon}</div>
              <h3 className="font-bold text-foreground mb-1 group-hover:text-primary transition-colors">{tile.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{tile.desc}</p>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
};
