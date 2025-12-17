import React, { useRef, useEffect, useState, useCallback } from 'react';
import { List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
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
}

/**
 * 🚀 VirtualizedMessageList - High Performance Message Rendering
 * 
 * ✅ Only renders visible messages (DOM stays light)
 * ✅ Handles 1000+ messages smoothly
 * ✅ Auto-scrolls to bottom on new messages
 * ✅ Preserves scroll position on updates
 * ✅ Calculates dynamic heights for variable message sizes
 */
export const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = React.memo(({
  messages,
  onHighlight,
  onCreateMiniAgent,
  getMiniAgentByMessage,
  onOpenHighlightsPanel,
  activeHighlightsMessageId,
  isSpeaking,
  onSpeak,
  onStopSpeaking,
  scrollToBottom = true,
  onScrollStateChange
}) => {
  const listRef = useRef<any>(null);
  const [rowHeights, setRowHeights] = useState<Record<number, number>>({});
  const rowHeightCache = useRef<Record<number, number>>({});
  const measurementCache = useRef<Record<string, number>>({});

  // Estimate row height based on message content
  const estimateRowHeight = useCallback((index: number): number => {
    if (rowHeightCache.current[index]) {
      return rowHeightCache.current[index];
    }

    const message = messages[index];
    if (!message) return 100;

    // Use cached measurement if available
    if (measurementCache.current[message.id]) {
      return measurementCache.current[message.id];
    }

    // Estimate based on content length
    const baseHeight = 80; // Min height for avatar + padding
    const contentLength = message.content?.length || 0;
    const linesEstimate = Math.ceil(contentLength / 60); // ~60 chars per line
    const contentHeight = linesEstimate * 24; // ~24px per line
    const highlightHeight = (message.highlights?.length || 0) * 30;
    const miniAgentHeight = getMiniAgentByMessage(message.id) ? 40 : 0;
    
    const estimated = baseHeight + contentHeight + highlightHeight + miniAgentHeight;
    
    // Cache the estimate
    rowHeightCache.current[index] = estimated;
    measurementCache.current[message.id] = estimated;
    
    return estimated;
  }, [messages, getMiniAgentByMessage]);

  // Get actual row height (uses cache or estimate)
  const getRowHeight = (index: number): number => {
    return rowHeights[index] || estimateRowHeight(index);
  };

  // Set row height after measurement
  const setRowHeight = useCallback((index: number, height: number) => {
    setRowHeights(prev => {
      if (prev[index] === height) return prev;
      
      const newHeights = { ...prev, [index]: height };
      rowHeightCache.current[index] = height;
      
      // Cache by message ID for persistence
      const message = messages[index];
      if (message) {
        measurementCache.current[message.id] = height;
      }
      
      return newHeights;
    });

    // Reset row height cache in list
    if (listRef.current) {
      listRef.current.resetAfterIndex(index, false);
    }
  }, [messages]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollToBottom && messages.length > 0 && listRef.current) {
      // Small delay to ensure heights are calculated
      const timer = setTimeout(() => {
        listRef.current?.scrollToItem(messages.length - 1, 'end');
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages.length, scrollToBottom]);

  // Track scroll position
  const handleScroll = useCallback(({ scrollOffset, scrollUpdateWasRequested }: any) => {
    if (!scrollUpdateWasRequested && onScrollStateChange && listRef.current) {
      // Check if user is at bottom (within 50px threshold)
      const list = listRef.current;
      // @ts-ignore - accessing private property
      const totalHeight = list._outerRef?.scrollHeight || 0;
      // @ts-ignore
      const visibleHeight = list._outerRef?.clientHeight || 0;
      const isAtBottom = totalHeight - (scrollOffset + visibleHeight) < 50;
      
      onScrollStateChange(isAtBottom);
    }
  }, [onScrollStateChange]);

  // Row renderer
  const Row = useCallback(({ index, style }: any) => {
    const message = messages[index];
    if (!message) return null;

    return (
      <div style={style}>
        <MessageRow
          message={message}
          onHighlight={onHighlight}
          onCreateMiniAgent={onCreateMiniAgent}
          getMiniAgentByMessage={getMiniAgentByMessage}
          onOpenHighlightsPanel={onOpenHighlightsPanel}
          activeHighlightsMessageId={activeHighlightsMessageId}
          isSpeaking={isSpeaking}
          onSpeak={onSpeak}
          onStopSpeaking={onStopSpeaking}
          onHeightChange={(height) => setRowHeight(index, height)}
        />
      </div>
    );
  }, [
    messages,
    onHighlight,
    onCreateMiniAgent,
    getMiniAgentByMessage,
    onOpenHighlightsPanel,
    activeHighlightsMessageId,
    isSpeaking,
    onSpeak,
    onStopSpeaking,
    setRowHeight
  ]);

  // Reset cache when messages change significantly
  useEffect(() => {
    const currentIds = messages.map(m => m.id).join(',');
    const cachedIds = Object.keys(measurementCache.current).join(',');
    
    if (currentIds !== cachedIds) {
      // Clear cache for messages that no longer exist
      const currentIdSet = new Set(messages.map(m => m.id));
      Object.keys(measurementCache.current).forEach(id => {
        if (!currentIdSet.has(id)) {
          delete measurementCache.current[id];
        }
      });
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p className="text-sm">No messages yet. Start a conversation!</p>
      </div>
    );
  }

  return (
    <AutoSizer>
      {({ height, width }) => {
        const ListComponent = List as any;
        return (
          <ListComponent
            ref={listRef}
            height={height}
            width={width}
            itemCount={messages.length}
            itemSize={getRowHeight}
            onScroll={handleScroll}
            overscanCount={5}
          >
            {Row}
          </ListComponent>
        );
      }}
    </AutoSizer>
  );
});

VirtualizedMessageList.displayName = 'VirtualizedMessageList';

/**
 * MessageRow - Individual message with height measurement
 */
interface MessageRowProps {
  message: Message;
  onHighlight: (messageId: string, text: string, startIndex: number, endIndex: number) => void;
  onCreateMiniAgent: (messageId: string, selectedText: string) => void;
  getMiniAgentByMessage: (messageId: string) => any;
  onOpenHighlightsPanel: (messageId: string) => void;
  activeHighlightsMessageId: string | null;
  isSpeaking?: string | null;
  onSpeak?: (messageId: string, text: string) => void;
  onStopSpeaking?: () => void;
  onHeightChange: (height: number) => void;
}

const MessageRow: React.FC<MessageRowProps> = React.memo(({
  message,
  onHighlight,
  onCreateMiniAgent,
  getMiniAgentByMessage,
  onOpenHighlightsPanel,
  activeHighlightsMessageId,
  isSpeaking,
  onSpeak,
  onStopSpeaking,
  onHeightChange
}) => {
  const rowRef = useRef<HTMLDivElement>(null);

  // Measure height after render
  useEffect(() => {
    if (rowRef.current) {
      const height = rowRef.current.offsetHeight;
      if (height > 0) {
        onHeightChange(height);
      }
    }
  }, [message.content, message.highlights?.length, onHeightChange]);

  // Use ResizeObserver for dynamic height changes
  useEffect(() => {
    if (!rowRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const height = entry.contentRect.height;
        if (height > 0) {
          onHeightChange(height);
        }
      }
    });

    resizeObserver.observe(rowRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [onHeightChange]);

  return (
    <div ref={rowRef} className="px-4 py-2">
      <MessageBubble
        message={message}
        onHighlight={onHighlight}
        onCreateMiniAgent={onCreateMiniAgent}
        miniAgent={getMiniAgentByMessage(message.id)}
        onOpenHighlightsPanel={onOpenHighlightsPanel}
        showHighlightsPanel={activeHighlightsMessageId === message.id}
        isSpeaking={isSpeaking === message.id}
        onSpeak={onSpeak}
        onStopSpeaking={onStopSpeaking}
      />
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  return (
    prevProps.message.id === nextProps.message.id &&
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.highlights?.length === nextProps.message.highlights?.length &&
    prevProps.activeHighlightsMessageId === nextProps.activeHighlightsMessageId &&
    prevProps.isSpeaking === nextProps.isSpeaking &&
    prevProps.getMiniAgentByMessage(prevProps.message.id) === 
      nextProps.getMiniAgentByMessage(nextProps.message.id)
  );
});

MessageRow.displayName = 'MessageRow';
