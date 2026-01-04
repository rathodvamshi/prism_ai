import React, { useState, useRef, useEffect, lazy, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { useProfileStore } from "@/stores/profileStore";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble } from "@/components/chat/MessageBubble";
// import { VirtualizedMessageList } from "@/components/chat/VirtualizedMessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { ConversationLoadingSkeleton } from "@/components/chat/LoadingSkeletons";
import { ConnectionStatus } from "@/components/chat/ConnectionStatus";
import { ChatErrorBoundary } from "@/components/chat/ChatErrorBoundary";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";

// ⚡ LAZY LOAD: Heavy components loaded only when needed
const MiniAgentPanel = lazy(() => import("@/components/chat/MiniAgentPanel"));
const HighlightsPanel = lazy(() => import("@/components/chat/HighlightsPanel"));
const SettingsModal = lazy(() => import("@/components/settings/SettingsModal"));
const CommandPalette = lazy(() => import("@/components/command/CommandPalette"));

// Loading fallbacks
import {
  PanelLoadingFallback,
  ModalLoadingFallback,
  CommandPaletteLoadingFallback
} from "@/components/chat/LazyLoadingFallbacks";

import { Share, Bot, Loader2, MoreHorizontal, ChevronDown, Check, Lock } from "lucide-react";
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
  { id: "gpt-4o-mini", name: "GPT-4o Mini", available: true },
  { id: "gpt-4o", name: "GPT-4o", available: false },
  { id: "claude-3", name: "Claude 3", available: false },
];

const Chat = () => {
  // ⚡ Performance monitoring (development only)
  usePageLoadMetrics();
  usePerformanceMonitor('Chat', process.env.NODE_ENV === 'development');

  const { sessionId } = useParams<{ sessionId?: string }>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState("general");
  const [isRestoring, setIsRestoring] = useState(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isUserAtBottomRef = useRef(true); // Track if user is at bottom
  const lastScrollTopRef = useRef(0); // Track scroll direction
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const [headerModel, setHeaderModel] = useState(models[0]);
  const [resetSignal, setResetSignal] = useState(0);
  const [isSpeakingGlobal, setIsSpeakingGlobal] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [includeHighlights, setIncludeHighlights] = useState(true);
  const [sharePayload, setSharePayload] = useState<string>("");
  const [activeHighlightsMessageId, setActiveHighlightsMessageId] = useState<string | null>(null);
  const { toast } = useToast();

  const {
    chats,
    currentChatId,
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

  // Auto-close highlights panel when message has no highlights or doesn't exist
  useEffect(() => {
    if (activeHighlightsMessageId && (!activeHighlightsMessage || !activeHighlightsMessage.highlights || activeHighlightsMessage.highlights.length === 0)) {
      setActiveHighlightsMessageId(null);
    }
  }, [activeHighlightsMessage?.highlights?.length, activeHighlightsMessageId]);

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
      // Debounce scroll handling for performance
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      scrollTimeout = setTimeout(() => {
        const { scrollTop, scrollHeight, clientHeight } = scrollElement;

        // Calculate distance from bottom
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

        // User is at bottom if within 30px threshold
        const isAtBottom = distanceFromBottom < 30;

        // Detect if user scrolled up manually
        const scrolledUp = scrollTop < lastScrollTopRef.current;

        // If user scrolls up, immediately disable auto-scroll
        if (scrolledUp && distanceFromBottom > 30) {
          isUserAtBottomRef.current = false;
        } else if (isAtBottom) {
          isUserAtBottomRef.current = true;
        }

        // Update last scroll position
        lastScrollTopRef.current = scrollTop;

        // Show jump button if scrolled up during streaming
        const shouldShowButton = !isAtBottom && (isSendingMessage || isStreaming) && distanceFromBottom > 200;
        setShowScrollToBottom(shouldShowButton);
      }, 50); // 50ms debounce
    };

    scrollElement.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      scrollElement.removeEventListener('scroll', handleScroll);
      if (scrollTimeout) clearTimeout(scrollTimeout);
    };
  }, [isSendingMessage, isStreaming]);

  // GPT-Style auto-scroll during streaming (smooth, respects user position)
  useEffect(() => {
    if ((isSendingMessage || isStreaming) && isUserAtBottomRef.current) {
      // Use RAF for smooth 60fps scrolling
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
        });
      });
    }
  }, [isSendingMessage, isStreaming, currentChat?.messages.length, currentChat?.messages[currentChat?.messages.length - 1]?.content]);

  // Hide scroll button when streaming stops
  useEffect(() => {
    if (!isSendingMessage && !isStreaming) {
      setShowScrollToBottom(false);
    }
  }, [isSendingMessage, isStreaming]);

  // Smooth scroll when user sends message - center it nicely
  useEffect(() => {
    if (currentChat && currentChat.messages.length > 0) {
      const lastMessage = currentChat.messages[currentChat.messages.length - 1];
      if (lastMessage.role === 'user') {
        // User just sent a message - scroll to show it centered
        isUserAtBottomRef.current = true;
        setShowScrollToBottom(false);

        // Small delay to ensure DOM is updated
        setTimeout(() => {
          requestAnimationFrame(() => {
            bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
          });
        }, 50);
      }
    }
  }, [currentChat?.messages.length]);

  const scrollToBottom = () => {
    isUserAtBottomRef.current = true;
    setShowScrollToBottom(false);
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  // Hydrate store and show skeleton while restoring
  useEffect(() => {
    let cancelled = false;

    // Load session data from URL parameter if present
    const loadSession = async () => {
      try {
        if (sessionId) {
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
          }
        } else {
          // No session ID in URL - load all chats if empty
          if (chats.length === 0 && !cancelled) {
            await loadChatsFromBackend();
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load session:', error);
          toast({
            title: "Failed to load chat",
            description: "Could not load the requested chat session. Retrying...",
            variant: "destructive",
          });

          // Retry once after 1 second
          setTimeout(() => {
            if (!cancelled && sessionId) {
              loadSessionData(sessionId).then(() => {
                setCurrentChat(sessionId);
              }).catch(err => {
                console.error('Retry failed:', err);
              });
            }
          }, 1000);
        }
      } finally {
        if (!cancelled) {
          // Brief skeleton to emulate smooth restore
          setTimeout(() => {
            if (!cancelled) {
              setIsRestoring(false);
            }
          }, 300);
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
    let targetId = currentChatId;
    if (!targetId) {
      targetId = await createSessionIfNeeded();
    }

    if (!targetId) return;

    try {
      // addMessage from chatStore handles:
      // 1. Optimistic user message update
      // 2. API call to backend
      // 3. Backend response handling
      // 4. AI response addition
      // All in one call - no duplicate API calls
      await addMessage(targetId, { role: "user", content: message, attachments });
    } catch (error) {
      console.error("Error sending message:", error);

      toast({
        title: "Connection Error",
        description: "Unable to connect to the AI service. Please check your connection.",
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
        startOffset: 0,
        endOffset: text.length,
      });
    }
  };

  const openApiSettings = () => {
    if (isMobile) {
      navigate("/settings?tab=api");
    } else {
      setSettingsTab("api");
      setSettingsOpen(true);
    }
  };

  return (
    <ChatErrorBoundary>
      <div className="flex h-screen min-h-0 overflow-hidden bg-background">
        <ConnectionStatus />
        <ChatSidebar onOpenSettings={() => (isMobile ? navigate("/settings") : setSettingsOpen(true))} />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 w-full">
          {/* Header */}
          <header className={cn(
            "shrink-0 h-14 flex items-center justify-between gap-2 px-3 sm:px-4 transition-all duration-200",
            sidebarExpanded
              ? "bg-background border-b border-border/50"
              : "bg-transparent"
          )}>
            <div className="flex items-center gap-2 min-w-0 flex-1">
              {isMobile && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground"
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
                            openApiSettings();
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
                <h2 className="text-sm sm:text-base font-medium text-foreground truncate">PRISM</h2>
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
                      onClick={async () => {
                        const newSessionId = await useChatStore.getState().startNewSession();
                        if (newSessionId) {
                          navigate(`/chat/${newSessionId}`);
                        }
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
          <div className="flex-1 overflow-hidden">
            {(!currentChat || currentChat.messages.length === 0) && !isRestoring && !isLoadingChats && (
              <ScrollArea className="flex-1 h-full">
                <div className="max-w-3xl mx-auto py-4 sm:py-6 px-3 sm:px-6">
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="py-8 sm:py-16"
                  >
                    <EmptyWelcome />
                  </motion.div>
                </div>
              </ScrollArea>
            )}

            {isLoadingChats && (
              <ScrollArea className="flex-1 h-full">
                <div className="max-w-3xl mx-auto py-4 sm:py-6 px-3 sm:px-6">
                  <ConversationLoadingSkeleton />
                </div>
              </ScrollArea>
            )}

            {isRestoring && !isLoadingChats && (
              <ScrollArea className="flex-1 h-full">
                <div className="max-w-3xl mx-auto py-4 sm:py-6 px-3 sm:px-6">
                  <div className="space-y-4">
                    <div className="h-6 w-32 sm:w-40 bg-muted animate-pulse rounded" />
                    <div className="space-y-2">
                      <div className="h-4 w-full bg-muted animate-pulse rounded" />
                      <div className="h-4 w-2/3 bg-muted animate-pulse rounded" />
                    </div>
                  </div>
                </div>
              </ScrollArea>
            )}

            {currentChat && currentChat.messages.length > 0 && !isLoadingChats && (
              <ScrollArea className="flex-1 h-full">
                <div className="max-w-3xl mx-auto py-4 sm:py-6 px-3 sm:px-6 space-y-4 sm:space-y-6">
                  {currentChat.messages.map((message) => {
                    const agentForMessage = miniAgents.find(a => a.messageId === message.id);
                    // Use index to detect last message
                    const index = currentChat.messages.indexOf(message);
                    return (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        onHighlight={(messageId, text, startIndex, endIndex) => {
                          if (currentChatId) {
                            addHighlight(currentChatId, messageId, {
                              text,
                              color: "yellow",
                              startOffset: startIndex,
                              endOffset: endIndex
                            });
                          }
                        }}
                        onCreateMiniAgent={handleCreateMiniAgent}
                        miniAgent={agentForMessage}
                        hasMiniAgent={!!agentForMessage}
                        onOpenMiniAgent={() => {
                          if (agentForMessage) {
                            setActiveMiniAgent(agentForMessage.id);
                          }
                        }}
                        onOpenHighlights={() => setActiveHighlightsMessageId(message.id)}
                        showHighlightsPanel={activeHighlightsMessageId === message.id}
                        isSpeaking={isSpeakingGlobal && currentChatId === message.id}
                        // 🧠 Thinking Logic (Latest AI message + isSendingMessage/isStreaming)
                        isThinking={
                          message.role === "assistant" &&
                          index === currentChat.messages.length - 1 &&
                          isSendingMessage
                        }
                      />
                    );
                  })}
                  <div ref={bottomRef} />
                </div>
              </ScrollArea>
            )}

            {/* Jump to latest button */}
            <AnimatePresence>
              {showScrollToBottom && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="absolute bottom-20 sm:bottom-32 left-1/2 -translate-x-1/2 z-10"
                >
                  <Button
                    onClick={scrollToBottom}
                    size="sm"
                    className="shadow-lg bg-background border border-border hover:bg-secondary gap-1.5 sm:gap-2 rounded-full px-3 sm:px-4 py-2 text-xs sm:text-sm"
                  >
                    <ChevronDown className="w-3 h-3 sm:w-4 sm:h-4" />
                    <span className="hidden sm:inline">Jump to latest</span>
                    <span className="sm:hidden">Latest</span>
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Input */}
          <ChatInput
            onSend={handleSend}
            isLoading={isSendingMessage || isStreaming}
            onOpenApiSettings={openApiSettings}
            resetSignal={resetSignal}
          />
        </div>

        {/* ⚡ LAZY: Mini Agent Panel */}
        {activeMiniAgentId && (
          <Suspense fallback={<PanelLoadingFallback />}>
            <MiniAgentPanel />
          </Suspense>
        )}

        {/* ⚡ LAZY: Highlights Panel */}
        {activeHighlightsMessage && activeHighlightsMessage.highlights && activeHighlightsMessage.highlights.length > 0 && (
          <Suspense fallback={<PanelLoadingFallback />}>
            <HighlightsPanel
              highlights={activeHighlightsMessage.highlights}
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

        {/* ⚡ LAZY: Settings Modal */}
        {settingsOpen && (
          <Suspense fallback={<ModalLoadingFallback />}>
            <SettingsModal
              open={settingsOpen}
              onOpenChange={setSettingsOpen}
              defaultTab={settingsTab}
            />
          </Suspense>
        )}

        {/* ⚡ LAZY: Command Palette */}
        <Suspense fallback={<CommandPaletteLoadingFallback />}>
          <CommandPalette onOpenSettings={() => (isMobile ? navigate("/settings") : setSettingsOpen(true))} />
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
    </ChatErrorBoundary>
  );
};

export default Chat;

const EmptyWelcome: React.FC = () => {
  const { profile } = useProfileStore();
  const name = profile.name;

  return (
    <div className="max-w-xl mx-auto text-center px-4">
      <div className="inline-block rounded-xl sm:rounded-2xl px-3 sm:px-4 py-1.5 sm:py-2 mb-3 sm:mb-4 bg-card/50 border border-border">
        <span className="text-xs sm:text-sm text-muted-foreground">Welcome to PRISM</span>
      </div>
      <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-foreground">
        Hello{name ? `! ${name}` : "!"} <span className="align-middle">👋</span>
      </h1>
      <p className="text-xs sm:text-sm text-muted-foreground mt-2 sm:mt-3">
        Ask me anything you want.
      </p>
    </div>
  );
};
