import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/stores/chatStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { X, Send, Trash2, Bot, Quote, Edit2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

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
  const [typingMessageId, setTypingMessageId] = useState<string | null>(null);
  const [typingContent, setTypingContent] = useState("");
  const [collapsedMessages, setCollapsedMessages] = useState<Set<string>>(new Set());
  const [followUpSuggestions, setFollowUpSuggestions] = useState<string[]>([]);
  const [justSentMessageId, setJustSentMessageId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
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
  
  // Get source message info for snippet context
  const getSnippetSourceInfo = () => {
    if (!activeAgent?.messageId) return null;
    
    // Try to find the message in current chat
    const currentChat = useChatStore.getState().chats.find(
      c => c.id === useChatStore.getState().currentChatId
    );
    
    const sourceMessage = currentChat?.messages.find(
      m => m.id === activeAgent.messageId
    );
    
    if (sourceMessage) {
      return {
        timestamp: new Date(sourceMessage.timestamp).toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
        messageId: activeAgent.messageId.slice(0, 8)
      };
    }
    
    return { messageId: activeAgent.messageId.slice(0, 8) };
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
      
      // Track this message for instant visibility
      const tempMessageId = `temp-${Date.now()}`;
      setJustSentMessageId(tempMessageId);
      
      await addMiniAgentMessage(activeMiniAgentId, combinedContent);
      
      // Clear the just-sent tracking after a short delay
      setTimeout(() => setJustSentMessageId(null), 500);
      
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
      console.log('✅ Snippet updated successfully');
    } catch (error) {
      console.error('❌ Failed to update snippet:', error);
      // Restore original snippet on error
      if (activeAgent) {
        setEditedSnippet(activeAgent.selectedText);
      }
    }
  };

  const handleRemoveSnippet = async () => {
    if (!activeMiniAgentId) return;
    
    try {
      await updateMiniAgentSnippet(activeMiniAgentId, "");
      setEditedSnippet("");
      setIsEditingSnippet(false);
      console.log('✅ Snippet removed successfully');
    } catch (error) {
      console.error('❌ Failed to remove snippet:', error);
    }
  };

  return (
    <AnimatePresence>
      {activeAgent && (
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="w-80 h-full bg-card border-l border-border flex flex-col shadow-xl"
          style={{
            minWidth: "320px",
            maxWidth: "600px",
          }}
        >
          {/* Header */}
          <div className="p-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-primary/10 via-primary/5 to-transparent backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <motion.div 
                className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Bot className="w-4 h-4 text-primary" />
              </motion.div>
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <span className="text-primary">🧠</span>
                  Sub-Brain
                </h3>
                <p className="text-xs text-muted-foreground">Clarifier Module</p>
              </div>
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => {
                  deleteMiniAgent(activeAgent.id);
                }}
                className="text-muted-foreground hover:text-destructive"
                title="Delete Sub-Brain"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setActiveMiniAgent(null)}
                className="text-muted-foreground"
                title="Close Sub-Brain"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Messages - Isolated Mini Agent conversation */}
          <ScrollArea className="flex-1 p-4" ref={scrollRef}>
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
                  <div className="mt-6 text-xs text-muted-foreground/50 space-y-1">
                    <p>💡 Tip: Press <kbd className="px-1.5 py-0.5 rounded bg-secondary text-foreground text-[10px]">ESC</kbd> to close</p>
                    <p>⌨️ Press <kbd className="px-1.5 py-0.5 rounded bg-secondary text-foreground text-[10px]">Enter</kbd> to send</p>
                  </div>
                </motion.div>
              )}
              {activeAgent.messages.map((msg, index) => {
                const parsed = parseMessageContent(msg.content);
                const isLongMessage = parsed.text.length > 300;
                const isCollapsed = collapsedMessages.has(msg.id);
                const displayText = isCollapsed ? parsed.text.slice(0, 150) + "..." : parsed.text;
                const isLastAIMessage = msg.role === "assistant" && index === activeAgent.messages.length - 1;
                
                // Highlight current conversation (last user + last AI message)
                const isLastUserMessage = msg.role === "user" && index === activeAgent.messages.length - 2;
                const isCurrentConversation = isLastUserMessage || isLastAIMessage;
                
                // Instant visibility for latest user message, animated for others
                const isJustSent = msg.role === "user" && index === activeAgent.messages.length - 1;
                
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: isJustSent ? 1 : 0, y: isJustSent ? 0 : 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ 
                      duration: isJustSent ? 0 : 0.3,
                      ease: "easeOut"
                    }}
                    className={cn(
                      "flex flex-col",
                      msg.role === "user" ? "items-end" : "items-start",
                      !isCurrentConversation && "opacity-60" // Fade older messages slightly
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[90%] p-3 rounded-xl text-sm leading-relaxed transition-all duration-300",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-sm"
                          : "bg-secondary text-secondary-foreground rounded-bl-sm",
                        isCurrentConversation && "ring-1 ring-primary/20 shadow-sm",
                        isJustSent && "ring-2 ring-primary/40 shadow-md" // Extra highlight for just sent
                      )}
                    >
                      {/* Show snippet if present (for user messages) */}
                      {parsed.snippet && msg.role === "user" && (
                        <div className="mb-2 pb-2 border-b border-primary-foreground/20">
                          <div className="flex items-start gap-1.5">
                            <Quote className="w-3 h-3 mt-0.5 opacity-50 shrink-0" />
                            <p className="text-xs opacity-60 italic">
                              {parsed.snippet}
                            </p>
                          </div>
                        </div>
                      )}
                      <div className="whitespace-pre-wrap break-words">
                        {displayText}
                      </div>
                      {isLongMessage && (
                        <button
                          onClick={() => toggleMessageCollapse(msg.id)}
                          className="text-xs text-primary/70 hover:text-primary mt-1 font-medium"
                        >
                          {isCollapsed ? "Show more ↓" : "Show less ↑"}
                        </button>
                      )}
                      <p className="text-[10px] opacity-50 mt-1">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                    
                    {/* Smart Suggestions Below AI Response */}
                    {isLastAIMessage && followUpSuggestions.length > 0 && (
                      <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-1.5 ml-1 max-w-[90%]"
                      >
                        <div className="flex items-center gap-1 mb-1">
                          <span className="text-[10px] text-muted-foreground/60">💡 You might also ask:</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {followUpSuggestions.map((suggestion, idx) => (
                            <motion.button
                              key={idx}
                              onClick={() => handleSuggestionClick(suggestion)}
                              initial={{ opacity: 0, scale: 0.9 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ delay: idx * 0.1 }}
                              whileHover={{ scale: 1.05, y: -2 }}
                              whileTap={{ scale: 0.95 }}
                              className="text-[10px] px-2 py-1 rounded-md bg-primary/8 hover:bg-primary/15 text-primary/90 hover:text-primary border border-primary/20 hover:border-primary/30 transition-all shadow-sm hover:shadow-md"
                            >
                              {suggestion}
                            </motion.button>
                          ))}
                        </div>
                      </motion.div>
                    )}
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
          </ScrollArea>

          {/* Snippet Section - Above Input */}
          {editedSnippet && (
            <div className="px-4 pt-3 pb-2 border-t border-border bg-secondary/30">
              {/* Snippet Context Preview */}
              {(() => {
                const sourceInfo = getSnippetSourceInfo();
                return sourceInfo && (
                  <div className="mb-2 text-xs text-muted-foreground flex items-center gap-1.5">
                    <span>📍</span>
                    <span>From message</span>
                    {sourceInfo.timestamp && (
                      <span className="text-primary font-medium">{sourceInfo.timestamp}</span>
                    )}
                    <span className="opacity-50">ID: {sourceInfo.messageId}</span>
                  </div>
                );
              })()}
              {isEditingSnippet ? (
                <div className="space-y-2">
                  <ScrollArea className="max-h-24">
                    <textarea
                      value={editedSnippet}
                      onChange={(e) => setEditedSnippet(e.target.value)}
                      className="w-full text-xs bg-background border border-border rounded-md p-2 min-h-[60px] resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                      placeholder="Selected text snippet..."
                    />
                  </ScrollArea>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="default"
                      onClick={handleSaveSnippet}
                      className="h-7 text-xs"
                    >
                      <Check className="w-3 h-3 mr-1" />
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setEditedSnippet(activeAgent.selectedText);
                        setIsEditingSnippet(false);
                      }}
                      className="h-7 text-xs"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Quote className="w-3.5 h-3.5 text-primary/70 shrink-0" />
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
                        <TooltipContent className="text-xs">
                          <p>Edit</p>
                        </TooltipContent>
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
                        <TooltipContent className="text-xs">
                          <p>Remove</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Input - Send messages to Sub-Brain */}
          <div className="border-t border-border bg-card">
            {/* Input Area with Expansion */}
            <div className="p-4">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  placeholder="Ask to Subbrain"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  className="flex-1 resize-none bg-background border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 hover:border-primary/30 transition-all duration-200 shadow-sm focus:shadow-md scrollbar-hide"
                  disabled={isSending}
                  style={{
                    minHeight: '32px',
                    maxHeight: '200px',
                    height: '32px',
                    overflowY: 'hidden'
                  }}
                />
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button 
                    size="icon-sm"
                    onClick={handleSend} 
                    disabled={!input.trim() || isSending}
                    className="h-7 w-7 shrink-0"
                  >
                    <Send className="w-2.5 h-2.5" />
                  </Button>
                </motion.div>
              </div>
            </div>
            
            <p className="text-[10px] text-muted-foreground px-4 pb-3 text-center">
              Sub-Brain • Isolated clarification • Press Enter to send
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
