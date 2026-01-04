import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { X, Trash2, Bot, Edit2, Check, SendHorizontal, ArrowRight, CornerDownRight, CornerUpRight, ThumbsUp, ThumbsDown, Volume2, RefreshCw, Repeat } from "lucide-react";
import { cn } from "@/lib/utils";
import { MessageBlockRenderer } from "./MessageBlockRenderer";
import { MessageBlockParser } from "@/lib/messageBlockParser";
import { CodeBlock } from "./CodeBlock";
import { VirtualFileCard } from "./VirtualFileCard";
import { ArrowLeft, Copy, Download } from "lucide-react";
import { MiniAgentMessageActions } from "./MiniAgentMessageActions";

/**
 * Mini Agent Panel Component
 * 
 * 🎯 PURPOSE:
 * - Provide isolated doubt-clarifier interface for selected text
 * - Each Mini Agent tied to ONE Main Agent message
 * - Maintains independent conversation history
 * 
 * ✨ FEATURES PER SPEC:
 * - Shows selected text snippet (editable/removable)
 * - Side panel with smooth animation (ChatGPT-style)
 * - Persistent conversation across refresh
 * - Same typing animation as main chat
 * - Resizable width (min/max limits)
 */
export const MiniAgentPanel = () => {
  const {
    miniAgents,
    activeMiniAgentId,
    setActiveMiniAgent,
    addMiniAgentMessage,
    deleteMiniAgent,
    updateMiniAgentSnippet,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isEditingSnippet, setIsEditingSnippet] = useState(false);
  const [editedSnippet, setEditedSnippet] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [viewingCode, setViewingCode] = useState<{ code: string; language: string; filename: string } | null>(null);

  const [collapsedMessages, setCollapsedMessages] = useState<Set<string>>(new Set());
  const [followUpSuggestions, setFollowUpSuggestions] = useState<string[]>([]);
  const [panelWidth, setPanelWidth] = useState(410); // Default 410px
  const [isResizing, setIsResizing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const draftKey = `sub-brain-draft-${activeMiniAgentId}`;

  const activeAgent = miniAgents.find((a) => a.id === activeMiniAgentId);

  // Helper to parse snippet from message content
  const parseMessageContent = (content: string) => {
    const snippetMatch = content.match(/\[SNIPPET\](.*?)\[\/SNIPPET\](.*)$/s);
    if (snippetMatch) {
      return {
        snippet: snippetMatch[1],
        text: snippetMatch[2],
      };
    }
    return { snippet: null, text: content };
  };




  // Code Renderer Handler for "Code as File" feature
  const handleRenderCode = (code: string, language: string) => {
    // Generate a pseudo-filename based on language or content hash equivalent
    const extMap: Record<string, string> = {
      python: 'py', javascript: 'js', typescript: 'ts', java: 'java',
      cpp: 'cpp', c: 'c', html: 'html', css: 'css', json: 'json',
      sql: 'sql', bash: 'sh', shell: 'sh', go: 'go', rust: 'rs',
      react: 'tsx', jsx: 'jsx', tsx: 'tsx'
    };

    const lang = language.toLowerCase();
    const ext = extMap[lang] || 'txt';
    let filename = `snippet_${Math.floor(Math.random() * 1000)}.${ext}`;

    // 🧠 Smart Naming Heuristics
    try {
      const firstLine = code.trim().split('\n')[0];

      if (lang === 'python') {
        const funcMatch = code.match(/def\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        const classMatch = code.match(/class\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        if (classMatch) filename = `${classMatch[1]}.py`;
        else if (funcMatch) filename = `${funcMatch[1]}.py`;
      }
      else if (['javascript', 'typescript', 'tsx', 'jsx'].includes(lang)) {
        const funcMatch = code.match(/function\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        const constMatch = code.match(/const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=/);
        const classMatch = code.match(/class\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        const componentMatch = code.match(/const\s+([A-Z][a-zA-Z0-9_]*)\s*=\s*\(/); // React Component

        if (componentMatch) filename = `${componentMatch[1]}.${ext}`;
        else if (classMatch) filename = `${classMatch[1]}.${ext}`;
        else if (funcMatch) filename = `${funcMatch[1]}.${ext}`;
        else if (constMatch) filename = `${constMatch[1]}.${ext}`;
      }
      else if (['java', 'csharp', 'cpp', 'c'].includes(lang)) {
        const classMatch = code.match(/class\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        if (classMatch) filename = `${classMatch[1]}.${ext}`;
      }
      else if (lang === 'html') {
        filename = 'index.html';
      }
      else if (lang === 'css') {
        filename = 'style.css';
      }
    } catch (e) {
      // Fallback to random if regex fails
    }

    return (
      <VirtualFileCard
        code={code}
        language={language}
        filename={filename}
        onOpen={(c, l, f) => setViewingCode({ code: c, language: l, filename: f })}
      />
    );
  };

  // Smart scroll to keep current conversation in focus
  useEffect(() => {
    if (activeAgent?.messages.length) {
      const lastMessage = activeAgent.messages[activeAgent.messages.length - 1];

      // Instant scroll for user messages (no delay)
      // Slight delay for AI messages (after thinking animation)
      const scrollDelay = lastMessage.role === 'user' ? 0 : 100;

      setTimeout(() => {
        // Access viewport element inside ScrollArea
        const viewport = scrollViewportRef.current ||
          scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');

        if (viewport) {
          viewport.scrollTo({
            top: viewport.scrollHeight,
            behavior: lastMessage.role === 'user' ? 'auto' : 'smooth'
          });
        }
      }, scrollDelay);
    }
  }, [activeAgent?.messages.length]);

  // Initialize edited snippet when agent changes OR when snippet changes
  useEffect(() => {
    if (activeAgent) {
      setEditedSnippet(activeAgent.selectedText);
      setIsEditingSnippet(false);

      // Restore draft from localStorage
      const savedDraft = localStorage.getItem(draftKey);
      if (savedDraft && !input) {
        setInput(savedDraft);
      }
    }
  }, [activeAgent?.id, activeAgent?.selectedText]);

  // Auto-save draft to localStorage
  useEffect(() => {
    if (input && activeMiniAgentId) {
      localStorage.setItem(draftKey, input);
    }
  }, [input, activeMiniAgentId]);

  // Clear draft after successful send
  const clearDraft = () => {
    if (activeMiniAgentId) {
      localStorage.removeItem(draftKey);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ESC to close panel
      if (e.key === 'Escape' && activeAgent) {
        setActiveMiniAgent(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeAgent]);

  // Auto-focus input on panel open and scroll to bottom
  useEffect(() => {
    if (activeAgent) {
      // Multiple scroll attempts to ensure it works
      const scrollToBottom = () => {
        // Try multiple methods to access viewport
        const viewport = scrollViewportRef.current ||
          scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]') ||
          document.querySelector('[data-radix-scroll-area-viewport]');

        if (viewport) {
          // Force scroll to bottom
          viewport.scrollTop = viewport.scrollHeight;
        }
      };

      // Scroll immediately
      scrollToBottom();

      // Scroll again after animation completes
      setTimeout(scrollToBottom, 350);

      // Final scroll to be sure
      setTimeout(scrollToBottom, 500);

      // Focus input after scrolls
      setTimeout(() => {
        inputRef.current?.focus();
      }, 550);
    }
  }, [activeAgent?.id]);

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      // Reset height to auto to get proper scrollHeight
      textarea.style.height = 'auto';

      // Calculate new height (min 32px, max 200px)
      const newHeight = Math.min(Math.max(textarea.scrollHeight, 32), 200);
      textarea.style.height = `${newHeight}px`;

      // Enable/disable scrolling based on content
      if (textarea.scrollHeight > 200) {
        textarea.style.overflowY = 'auto';
      } else {
        textarea.style.overflowY = 'hidden';
      }
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || !activeMiniAgentId || isSending) return;

    const messageContent = input.trim();
    const snippet = editedSnippet || activeAgent?.selectedText || "";

    // Combine snippet and input as ONE content with delimiter
    const combinedContent = snippet
      ? `[SNIPPET]${snippet}[/SNIPPET]${messageContent}`
      : messageContent;

    setInput("");
    clearDraft();
    setIsSending(true);
    setIsThinking(true);

    try {
      // Clear old suggestions immediately when sending
      setFollowUpSuggestions([]);

      await addMiniAgentMessage(activeMiniAgentId, combinedContent);


      // Smart scroll will be triggered by useEffect on message change
      // Generate smart follow-up suggestions based on question
      const suggestions = generateSmartSuggestions(messageContent, snippet);
      setFollowUpSuggestions(suggestions);

      // Clear snippet after sending successfully
      if (snippet) {
        await updateMiniAgentSnippet(activeMiniAgentId, "");
        setEditedSnippet("");
      }
    } catch (error) {
      console.error("Failed to send Sub-Brain message:", error);
    } finally {
      setIsSending(false);
      setIsThinking(false);
    }
  };

  // Generate contextual follow-up suggestions
  const generateSmartSuggestions = (question: string, snippet: string): string[] => {
    const q = question.toLowerCase();
    const suggestions: string[] = [];

    // Pattern-based suggestion generation
    if (q.includes('what') || q.includes('explain')) {
      suggestions.push("Can you give a practical example?");
      suggestions.push("How is this used in real scenarios?");
    } else if (q.includes('how')) {
      suggestions.push("What are common mistakes?");
      suggestions.push("Can you show step-by-step?");
    } else if (q.includes('why')) {
      suggestions.push("What are the alternatives?");
      suggestions.push("Explain with an analogy");
    } else if (q.includes('difference')) {
      suggestions.push("Which one should I use?");
      suggestions.push("Show comparison example");
    }

    // Generic helpful suggestions
    if (suggestions.length < 3) {
      const generic = [
        "Explain this more simply",
        "Give me an analogy",
        "What's a real-world example?",
        "What are best practices?",
        "What should I avoid?"
      ];
      suggestions.push(...generic.slice(0, 3 - suggestions.length));
    }

    return suggestions.slice(0, 3);
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    setFollowUpSuggestions([]);
  };

  // Toggle message collapse
  const toggleMessageCollapse = (messageId: string) => {
    setCollapsedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  const handleSaveSnippet = async () => {
    if (!activeMiniAgentId) return;

    try {
      await updateMiniAgentSnippet(activeMiniAgentId, editedSnippet);
      setIsEditingSnippet(false);
      if (process.env.NODE_ENV === 'development') {
        console.log('[MiniAgent] Snippet updated successfully');
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[MiniAgent] Failed to update snippet:', error);
      }
      // Restore original snippet on error
      if (activeAgent) {
        setEditedSnippet(activeAgent.selectedText);
      }
    }
  };

  const handleRemoveSnippet = async () => {
    if (!activeMiniAgentId) return;

    try {
      // Clear snippet from backend
      await updateMiniAgentSnippet(activeMiniAgentId, "");

      // Clear all snippet-related states
      setEditedSnippet("");
      setIsEditingSnippet(false);

      // Also update the active agent's selectedText to ensure it's cleared
      if (activeAgent) {
        // This ensures the snippet won't be included in future messages
        activeAgent.selectedText = "";
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('[MiniAgent] Snippet removed completely from all states');
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[MiniAgent] Failed to remove snippet:', error);
      }
    }
  };

  // Handle resize
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  // Auto-expand removed to prevent unwanted width changes


  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;

      const newWidth = window.innerWidth - e.clientX;
      // 1️⃣ WIDTH CONSTRAINTS: Recommended values for responsive design
      // min-width: 260px; max-width: 520px;
      const maxWidth = 520;
      const minWidth = 260;
      const clampedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
      setPanelWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  return (
    <AnimatePresence>
      {activeAgent && (
        <motion.div
          ref={panelRef}
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          style={{ width: `${panelWidth}px` }}
          className="h-full w-full bg-card border-l border-border flex flex-col shadow-xl relative overflow-hidden min-h-0"
        >
          {/* Resize Handle */}
          <div
            onMouseDown={handleMouseDown}
            className={`absolute left-0 top-0 bottom-0 w-1 hover:w-1.5 bg-transparent hover:bg-primary/50 cursor-col-resize transition-all z-50 ${isResizing ? 'bg-primary w-1.5' : ''}`}
            title="Drag to resize"
          />
          {/* Header */}
          <div className="shrink-0 h-14 px-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-primary/10 via-primary/5 to-transparent backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <motion.div
                className="w-5 h-5 rounded-md bg-primary/10 flex items-center justify-center shrink-0"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Bot className="w-3 h-3 text-primary" />
              </motion.div>
              <div className="min-w-0 flex items-baseline gap-2">
                <h3 className="text-xs font-semibold text-foreground flex items-center gap-1.5 truncate">
                  Sub-Brain
                </h3>
                {panelWidth >= 300 && (
                  <span className="text-[10px] text-muted-foreground/80 truncate font-medium">Clarifier</span>
                )}
              </div>
            </div>


            <div className="flex gap-1">
              <TooltipProvider delayDuration={200}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        deleteMiniAgent(activeAgent.id);
                      }}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="text-xs py-1 px-2">
                    Delete
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider delayDuration={200}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setActiveMiniAgent(null)}
                      className="text-muted-foreground"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="text-xs py-1 px-2">
                    Close
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>

          {/* Messages - Isolated Mini Agent conversation */}
          {/* Messages - Isolated Mini Agent conversation */}
          <div
            className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 scroll-smooth scrollbar-thin scrollbar-thumb-primary/10 scrollbar-track-transparent hover:scrollbar-thumb-primary/20 [&_*]:box-border"
            ref={scrollRef}
          >
            <div
              className="space-y-4 pb-4"
              ref={(el) => {
                if (el) {
                  scrollViewportRef.current = el.parentElement as HTMLDivElement;
                }
              }}
            >
              {activeAgent.messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                  className="text-center py-12 px-4"
                >
                  <motion.div
                    className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mx-auto mb-4 shadow-lg"
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <span className="text-3xl">🧠</span>
                  </motion.div>
                  <p className="text-base font-semibold text-foreground mb-2">
                    Sub-Brain: Clarifier Module
                  </p>
                  <p className="text-sm text-muted-foreground mb-1">
                    Ask anything about the selected text
                  </p>
                  <p className="text-xs text-muted-foreground/60">
                    I'll break it down and explain clearly
                  </p>

                </motion.div>
              )}
              {activeAgent.messages.map((msg, index) => {
                if (!msg.content || msg.content.trim() === '') return null;

                const parsed = parseMessageContent(msg.content);
                const isIsLast = index === activeAgent.messages.length - 1;

                // Fallback for empty text
                if (!parsed.text || parsed.text.trim() === '') {
                  parsed.text = "⚠️ Response generated but no content was returned.";
                }

                const isLongMessage = parsed.text.length > 500;
                const isCollapsed = collapsedMessages.has(msg.id);
                // For collapse/expand logic
                const displayText = isCollapsed ? parsed.text : parsed.text; // We handle height truncation instead of text slicing for smoother effect if needed, but keeping simple for now
                // Actually slicing text is safer for large renderings
                const renderText = isCollapsed ? parsed.text.slice(0, 200) + "..." : parsed.text;

                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      "w-full flex gap-3 mb-4 group",
                      msg.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {/* MESSAGE CONTAINER */}
                    <div className={cn(
                      "relative max-w-full flex flex-col",
                      msg.role === "user" ? "items-end" : "items-start"
                    )}>

                      {/* 1. USER SNIPPET (Context) - Strictly for User */}
                      {msg.role === "user" && parsed.snippet && (
                        <div className="flex items-end gap-2 justify-end mb-1 opacity-80">
                          <CornerUpRight className="w-3.5 h-3.5 text-primary/40 shrink-0 mb-0.5" strokeWidth={2} />
                          <div className="text-xs text-muted-foreground italic text-right max-w-[90%] break-words line-clamp-2">
                            "{parsed.snippet}"
                          </div>
                        </div>
                      )}

                      {/* 2. THE VISUAL BUBBLE */}
                      <div className={cn(
                        "transition-all duration-200",
                        "whitespace-normal break-words [overflow-wrap:anywhere]",
                        // ROLE-BASED STYLING
                        msg.role === "user"
                          /* User: Bubble is on the text content itself, this wrapper is transparent */
                          ? "bg-transparent text-foreground border-none shadow-none text-right flex flex-col items-end p-0"
                          /* AI: Bubble is this wrapper - Premium Glassmorphism Design */
                          : "bg-gradient-to-br from-card/80 to-card/40 backdrop-blur-md border border-primary/5 text-foreground/95 rounded-2xl rounded-tl-[2px] shadow-sm p-4 ring-1 ring-white/5"
                      )}>

                        {/* TEXT CONTENT */}
                        <div className={cn(
                          "leading-relaxed",
                          // User: Visual styles applied here
                          msg.role === "user" && "bg-primary/5 backdrop-blur-[1px] border border-primary/10 rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-sm text-sm"
                        )}
                          style={{
                            fontSize: 'clamp(13px, 1.2vw, 15px)',
                            lineHeight: 1.5
                          }}
                        >
                          {msg.role === "user" ? (
                            parsed.text
                          ) : (
                            // AI Content: Strict Overflow Control
                            <div className="w-full min-w-0 overflow-hidden [&_pre]:!max-w-full [&_pre]:!overflow-x-auto [&_div[data-code-block]]:!max-w-full [&_div[data-code-block]]:!overflow-x-auto">
                              <MessageBlockRenderer
                                blocks={MessageBlockParser.parse(renderText)}
                                className={cn("!text-sm w-full", panelWidth < 400 && "!text-xs font-normal")}
                                customCodeRenderer={handleRenderCode}
                              />
                            </div>
                          )}
                        </div>

                        {/* AI FOOTER: Read More */}
                        {msg.role === "assistant" && isLongMessage && (
                          <div className="mt-2 pt-2 border-t border-border/30 flex justify-end">
                            <button
                              onClick={() => toggleMessageCollapse(msg.id)}
                              className="text-xs text-primary/80 hover:text-primary font-medium hover:underline flex items-center gap-1 transition-colors"
                            >
                              {isCollapsed ? "Read more" : "Show less"}
                            </button>
                          </div>
                        )}
                      </div>

                      {/* MESSAGE ACTIONS */}
                      <MiniAgentMessageActions
                        isUser={msg.role === "user"}
                        text={parsed.text}
                        onEdit={() => {
                          setInput(parsed.text);
                          inputRef.current?.focus();
                        }}
                        onRegenerate={() => {
                          setIsThinking(true);
                          addMiniAgentMessage(activeAgent.id, "Regenerate that response", true);
                        }}
                      />

                      {/* AI FOOTER: Suggestions (Outside bubble) */}
                      {msg.role === "assistant" && isIsLast && followUpSuggestions.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2 animate-in fade-in slide-in-from-top-1 duration-300">
                          {followUpSuggestions.map((suggestion, idx) => (
                            <button
                              key={idx}
                              onClick={() => handleSuggestionClick(suggestion)}
                              className="text-xs px-2.5 py-1.5 rounded-full bg-background border border-primary/20 text-primary hover:bg-primary hover:text-primary-foreground transition-all shadow-sm"
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
              {isThinking && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start mb-3"
                >
                  <motion.div
                    className="px-4 py-2.5 rounded-xl text-sm bg-gradient-to-r from-secondary/90 to-secondary/70 text-secondary-foreground rounded-bl-sm border border-primary/20 backdrop-blur-sm shadow-sm"
                    animate={{ boxShadow: ['0 0 0 0 rgba(var(--primary), 0)', '0 0 0 4px rgba(var(--primary), 0.1)', '0 0 0 0 rgba(var(--primary), 0)'] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    style={{
                      // 7️⃣ THINKING / LOADING INDICATOR (SAFE)
                      // align-self: flex-start; max-width: fit-content;
                      maxWidth: 'fit-content'
                    }}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="flex gap-1">
                        <motion.span
                          className="inline-block w-1.5 h-1.5 rounded-full bg-primary"
                          animate={{ y: [0, -6, 0] }}
                          transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut" }}
                        />
                        <motion.span
                          className="inline-block w-1.5 h-1.5 rounded-full bg-primary"
                          animate={{ y: [0, -6, 0] }}
                          transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
                        />
                        <motion.span
                          className="inline-block w-1.5 h-1.5 rounded-full bg-primary"
                          animate={{ y: [0, -6, 0] }}
                          transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
                        />
                      </div>
                      <span className="text-xs font-medium bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">Thinking...</span>
                    </div>
                  </motion.div>
                </motion.div>
              )}
              {isSending && !isThinking && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="max-w-[90%] p-3 rounded-xl text-sm bg-secondary text-secondary-foreground rounded-bl-sm">
                    <div className="flex gap-1">
                      <span className="animate-bounce inline-block">.</span>
                      <span className="animate-bounce inline-block [animation-delay:0.2s]">.</span>
                      <span className="animate-bounce inline-block [animation-delay:0.4s]">.</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          </div>

          {/* Snippet Section - Above Input */}
          {/* Snippet Section - Above Input */}
          {editedSnippet && (
            <div className={cn(
              "px-4 pt-3 pb-2 border-t border-border bg-secondary/30",
              panelWidth < 350 && "px-2 pt-2 pb-1"
            )}>
              {/* Snippet Context Preview */}
              {isEditingSnippet ? (
                <div className="space-y-2">
                  <div className="max-h-24 overflow-y-auto scrollbar-thin scrollbar-thumb-primary/10 scrollbar-track-transparent hover:scrollbar-thumb-primary/20">
                    <textarea
                      value={editedSnippet}
                      onChange={(e) => setEditedSnippet(e.target.value)}
                      className="w-full text-xs bg-background border border-border rounded-md p-2 min-h-[60px] resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="Selected text snippet..."
                    />
                  </div>
                  <div className="flex gap-1 justify-end">
                    {/* Responsive Buttons for Editing */}
                    <Button size="sm" variant="ghost" onClick={() => {
                      setEditedSnippet(activeAgent.selectedText);
                      setIsEditingSnippet(false);
                    }} className="h-6 text-xs px-2">
                      Cancel
                    </Button>
                    <Button size="sm" variant="default" onClick={handleSaveSnippet} className="h-6 text-xs px-2">
                      <Check className="w-3 h-3 mr-1" />
                      Save
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-3.5 h-3.5 text-primary/70 shrink-0" />
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <p className="text-xs text-muted-foreground truncate">
                      {editedSnippet}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setIsEditingSnippet(true)}
                            className="h-6 w-6 hover:bg-blue-500/10 transition-colors"
                          >
                            <Edit2 className="w-3 h-3 text-blue-500" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent className="text-xs">Edit</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={handleRemoveSnippet}
                            className="h-6 w-6 hover:bg-red-500/10 transition-colors"
                          >
                            <X className="w-3 h-3 text-red-500" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent className="text-xs">Remove</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Floating Input Box - Minimal & Clean */}
          <div className={cn(
            "shrink-0 px-4 pb-4 pt-2 space-y-2 border-t border-white/5",
            panelWidth < 400 && "px-2 pb-2 pt-1"
          )}>
            {/* Input Container */}
            <div className={cn(
              "flex items-end gap-2 bg-secondary/30 backdrop-blur-sm rounded-2xl shadow-lg border border-border/20",
              panelWidth < 400 ? "px-2 py-2" : "px-4 py-2.5"
            )}>
              <textarea
                ref={inputRef}
                placeholder={panelWidth < 350 ? "Ask..." : "Ask anything..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                className={cn(
                  "flex-1 resize-none bg-transparent",
                  "text-sm leading-[1.5]",
                  "placeholder:text-muted-foreground/50",
                  "focus:outline-none",
                  // Custom scrollbar styling
                  "scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-transparent",
                  "hover:scrollbar-thumb-primary/30"
                )}
                disabled={isSending}
                rows={1}
                style={{
                  maxHeight: '120px',
                  overflowY: 'auto',
                  lineHeight: '1.5'
                }}
              />

              {/* Send Button - Aligned to bottom */}
              <motion.button
                onClick={handleSend}
                disabled={!input.trim() || isSending}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className={cn(
                  "shrink-0 p-2 rounded-xl self-end",
                  "bg-primary text-primary-foreground",
                  "hover:bg-primary/90",
                  "disabled:bg-muted disabled:text-muted-foreground",
                  "transition-colors duration-200",
                  "disabled:cursor-not-allowed disabled:opacity-50"
                )}
              >
                {isSending ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <SendHorizontal className="w-4 h-4" />
                  </motion.div>
                ) : (
                  <SendHorizontal className="w-4 h-4" />
                )}
              </motion.button>
            </div>

            {panelWidth > 350 && (
              <p className="text-[10px] text-muted-foreground/60 text-center px-2">
                Sub-Brain can make mistakes. Verify important information.
              </p>
            )}
          </div>

          {/* CODE VIEWER OVERLAY - Replaces content when file is open */}
          <AnimatePresence>
            {viewingCode && (
              <motion.div
                initial={{ opacity: 0, x: "100%" }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: "100%" }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="absolute inset-0 z-50 bg-background flex flex-col h-full w-full overflow-hidden"
              >
                {/* Viewer Header */}
                <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4 bg-background/80 backdrop-blur-md sticky top-0 z-10">
                  <div className="flex items-center gap-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 -ml-2 text-muted-foreground hover:text-foreground hover:bg-muted/50"
                      onClick={() => setViewingCode(null)}
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </Button>
                    <div className="flex flex-col min-w-0">
                      <h3 className="text-sm font-semibold truncate flex items-center gap-2">
                        {viewingCode.filename}
                      </h3>
                      <div className="text-[10px] text-muted-foreground flex items-center gap-1.5">
                        <span className="uppercase font-mono text-primary/70">{viewingCode.language}</span>
                        <span className="w-0.5 h-0.5 rounded-full bg-border" />
                        <span>Editable View</span>
                      </div>
                    </div>
                  </div>

                  {/* Header Actions */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-muted-foreground hover:text-foreground"
                      title="Copy Code"
                      onClick={() => {
                        navigator.clipboard.writeText(viewingCode.code);
                        // Optional: trigger a small toast or visual feedback here if possible, 
                        // but sticking to simple action for now.
                      }}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-muted-foreground hover:text-foreground"
                      title="Download"
                      onClick={() => {
                        try {
                          const blob = new Blob([viewingCode.code], { type: "text/plain;charset=utf-8" });
                          const url = URL.createObjectURL(blob);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = viewingCode.filename || "download.txt";
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                          // Cleanup
                          setTimeout(() => URL.revokeObjectURL(url), 100);
                        } catch (err) {
                          console.error("Download failed:", err);
                        }
                      }}
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Viewer Content - Independent Scroll */}
                <div className="flex-1 min-h-0 overflow-y-auto p-4 bg-background scrollbar-thin scrollbar-thumb-primary/10 scrollbar-track-transparent hover:scrollbar-thumb-primary/20">
                  <div className="max-w-full [&_pre]:!m-0 [&_pre]:!bg-transparent">
                    <CodeBlock language={viewingCode.language}>
                      {viewingCode.code}
                    </CodeBlock>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </motion.div>
      )
      }
    </AnimatePresence >
  );
};

export default MiniAgentPanel;
