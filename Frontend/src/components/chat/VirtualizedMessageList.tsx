import React, { useRef, useEffect, useCallback } from 'react';
import { MessageBubble } from './MessageBubble';
import type { Message } from '@/types/chat';

interface VirtualizedMessageListProps {
  messages: Message[];
  onHighlight: (messageId: string, text: string, startIndex: number, endIndex: number) => void;
  onCreateMiniAgent: (messageId: string, selectedText: string) => void;
  getMiniAgentByMessage: (messageId: string) => any;
  onOpenHighlightsPanel: (messageId: string) => void;
  activeHighlightsMessageId: string | null;
  isSpeaking?: string | null;
  onSpeak?: (messageId: string, text: string) => void;
  onStopSpeaking?: () => void;
  scrollToBottom?: boolean;
  onScrollStateChange?: (isAtBottom: boolean) => void;
  isStreamingLogic?: boolean;
  isSendingMessage?: boolean;
  onOpenMiniAgent?: (agentId: string) => void;
  forceScrollSignal?: number; // 🆕 Signal to force scroll to bottom manually
}

/**
 * 🚀 MessageList - Simple Scrollable Message Rendering
 * 
 * ✅ Renders all messages in a scrollable container
 * ✅ Auto-scrolls to bottom on new messages
 * ✅ Works reliably without complex virtualization
 */
export const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = React.memo((props) => {
  const {
    messages = [],
    onHighlight,
    onCreateMiniAgent,
    getMiniAgentByMessage,
    onOpenHighlightsPanel,
    activeHighlightsMessageId,
    isSpeaking,
    onSpeak,
    onStopSpeaking,
    scrollToBottom = true,
    onScrollStateChange,
    isStreamingLogic,
    isSendingMessage,
    onOpenMiniAgent,
    forceScrollSignal = 0,
  } = props;

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  const lastScrollTop = useRef(0);

  console.log('📦 [MessageList] Rendering with', messages.length, 'messages');

  // Manual force scroll trigger (e.g. from "Jump to Bottom" button)
  useEffect(() => {
    if (forceScrollSignal > 0 && bottomRef.current) {
      console.log("⬇️ Forcing scroll to bottom (Signal received)");
      isUserScrolling.current = false; // Reset user scrolling flag
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [forceScrollSignal]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollToBottom && bottomRef.current && !isUserScrolling.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, scrollToBottom]);

  // Initial scroll to bottom
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'auto' });
    }
  }, []);

  // Track scroll position
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const atBottom = scrollHeight - (scrollTop + clientHeight) < 100;

    // Detect if user is scrolling up
    if (scrollTop < lastScrollTop.current - 10) {
      isUserScrolling.current = true;
    }

    // Reset user scrolling flag if at bottom
    if (atBottom) {
      isUserScrolling.current = false;
    }

    lastScrollTop.current = scrollTop;
    onScrollStateChange?.(atBottom);
  }, [onScrollStateChange]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p className="text-sm">No messages yet. Start a conversation!</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="absolute inset-0 overflow-y-auto overflow-x-hidden scroll-smooth will-change-scroll conversation-scrollbar"
    >
      <div className="w-full pt-16 sm:pt-24 pb-4">
        {messages.map((message, index) => {
          const isLast = index === messages.length - 1;
          const isStreaming = isStreamingLogic && isLast && message.role === "assistant";
          const isThinking = isSendingMessage && isLast && message.role === "assistant" && !message.content;

          return (
            <div key={message.id} className="w-full max-w-[850px] mx-auto px-4 pl-6 sm:pl-8 lg:pl-12 py-2">
              <MessageBubble
                message={message}
                onHighlight={onHighlight}
                onCreateMiniAgent={onCreateMiniAgent}
                miniAgent={getMiniAgentByMessage(message.id)}
                onOpenHighlightsPanel={() => onOpenHighlightsPanel(message.id)}
                showHighlightsPanel={activeHighlightsMessageId === message.id}
                isSpeaking={isSpeaking === message.id}
                onSpeak={onSpeak}
                onStopSpeaking={onStopSpeaking}
                isStreaming={isStreaming}
                isThinking={isThinking}
                hasMiniAgent={!!getMiniAgentByMessage(message.id)}
                onOpenMiniAgent={() => {
                  const agent = getMiniAgentByMessage(message.id);
                  if (agent) {
                    onOpenMiniAgent?.(agent.id);
                  }
                }}
              />
            </div>
          );
        })}
        {/* Scroll anchor */}
        <div ref={bottomRef} className="h-1" />
      </div>
    </div>
  );
});

VirtualizedMessageList.displayName = 'VirtualizedMessageList';
