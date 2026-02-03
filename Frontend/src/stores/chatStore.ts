const generateId = () => Math.random().toString(36).substring(2, 15);
import { create } from "zustand";
import { Chat, Highlight, Message, MiniAgent, MiniAgentMessage, Task } from "@/types/chat";
import { cleanMessageContent, realignHighlights } from "@/lib/highlightUtils";
import { chatAPI } from "@/lib/api";
import { createMetadataFilter } from "@/lib/streamUtils";
import { useAuthStore } from "./authStore";
import { toast } from "@/hooks/use-toast";

interface ChatState {
  chats: Chat[];
  currentChatId: string | null;
  isDraftSession: boolean; // True when in "New Chat" mode before first message
  isCreatingSession: boolean; // True while session is being created
  pendingFirstMessage: string | null; // First message waiting for session creation
  tasks: Task[];
  miniAgents: MiniAgent[];
  activeMiniAgentId: string | null;
  sidebarExpanded: boolean;
  activeTab: "history" | "tasks" | "media";
  isLoadingChats: boolean;
  isSendingMessage: boolean;
  isStreaming: boolean;
  lastSynced: Record<string, number>; // Map of chatId/sessionId -> timestamp
  hasMore: boolean; // For pagination
  freeLimitExceeded: boolean; // True when user hits free usage limit
  limitExceededType: "free_limit" | "all_keys_exhausted"; // Type of limit exceeded
  // Error recovery
  lastFailedMessage: { chatId: string; content: string; attachments?: any[] } | null;
  askFlowContext: { text: string; source?: string } | null;

  // Actions
  createChat: () => Promise<string>;
  setCurrentChat: (id: string) => void;
  addMessage: (chatId: string, message: Omit<Message, "id" | "timestamp">) => Promise<void>;
  deleteChat: (id: string) => Promise<void>;
  renameChat: (id: string, title: string) => Promise<void>;
  pinChat: (id: string, isPinned: boolean) => Promise<void>;
  saveChat: (id: string, isSaved: boolean) => Promise<void>;

  createTask: (title: string, description?: string, dueDate?: Date, timeSeconds?: number, imageUrl?: string) => Promise<string>;
  toggleTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  loadTasksFromBackend: () => Promise<void>;
  confirmTaskDraft: (messageId: string, description: string, dueDate?: string) => Promise<void>;

  createMiniAgent: (messageId: string, selectedText: string, userPrompt?: string) => Promise<string>;
  fetchMiniAgent: (agentId: string) => Promise<void>;
  addMiniAgentMessage: (agentId: string, content: string) => Promise<void>;
  deleteMiniAgent: (id: string) => Promise<void>;
  updateMiniAgentSnippet: (agentId: string, selectedText: string) => Promise<void>;
  setActiveMiniAgent: (id: string | null) => Promise<void>;
  loadSessionMiniAgents: (sessionId: string, force?: boolean) => Promise<void>;

  addHighlight: (chatId: string, messageId: string, highlight: Omit<Highlight, "id">) => Promise<void>;
  removeHighlight: (chatId: string, messageId: string, predicate: (h: Highlight) => boolean) => Promise<void>;
  updateHighlightNote: (chatId: string, messageId: string, highlightId: string, note: string) => Promise<void>;
  updateHighlightColor: (chatId: string, messageId: string, highlightId: string, color: string) => Promise<void>;

  markActionExecuted: (chatId: string, messageId: string) => void;

  toggleSidebar: () => void;
  setActiveTab: (tab: "history" | "tasks" | "media") => void;
  // Session helpers
  isSessionEmpty: () => boolean;
  createSessionIfNeeded: () => Promise<string>;
  startNewSession: () => Promise<string | null>;
  startDraftSession: () => void; // Enter draft mode (no backend call)
  clearDraftSession: () => void; // Clear draft mode
  hydrateFromStorage: () => void;

  // Backend synchronization
  loadChatsFromBackend: (loadMore?: boolean) => Promise<void>;
  syncChatWithBackend: (chatId: string, force?: boolean) => Promise<void>;
  loadSessionData: (sessionId: string) => Promise<void>;

  // Local highlight ranges (hex colors) per chat
  addRangeHighlight: (chatId: string, msgId: string, start: number, end: number, colorHex: string) => void;
  removeRangeHighlight: (chatId: string, msgId: string, start: number, end: number) => void;
  getMessageRangeHighlights: (chatId: string, msgId: string) => Array<{ msgId: string; range: [number, number]; color: string }>;

  // Streaming
  sendMessageStream: (chatId: string, content: string, onToken: (token: string) => void, onComplete: () => void) => Promise<void>;

  // API Keys / Free limit
  setFreeLimitExceeded: (exceeded: boolean, type?: "free_limit" | "all_keys_exhausted") => void;

  // Error recovery
  clearLastFailedMessage: () => void;
  retryLastFailedMessage: () => Promise<void>;
  setAskFlowContext: (context: { text: string; source?: string } | null) => void;
}


// MongoDB is the source of truth

// Filler words to remove from title generation
const FILLER_WORDS = [
  'play', 'show', 'tell me', 'can you', 'please', 'could you', 'would you',
  'i want to', 'i need to', 'help me', 'how to', 'what is', 'what are',
  'give me', 'find me', 'search for', 'look up', 'get me', 'open',
  'hey', 'hi', 'hello', 'okay', 'ok', 'um', 'uh', 'like', 'just'
];

// Derive a readable chat title from the first user message
const deriveTitleFrom = (text: string): string => {
  if (!text) return "New Chat";
  let t = text.replace(/\s+/g, " ").trim().toLowerCase();
  if (!t) return "New Chat";

  // Remove filler words from the beginning
  for (const filler of FILLER_WORDS) {
    if (t.startsWith(filler + ' ')) {
      t = t.slice(filler.length + 1).trim();
    }
  }

  // Capitalize first letter of each word
  t = t.split(' ').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');

  if (!t) return "New Chat";

  const max = 28; // Shorter max for cleaner sidebar
  if (t.length <= max) return t;

  // Try to break at word boundary
  const lastSpace = t.lastIndexOf(" ", max);
  const slicePoint = lastSpace > 15 ? lastSpace : max;
  return t.slice(0, slicePoint).trim() + "…";
};

export const useChatStore = create<ChatState>((set, get) => ({
  chats: [],
  currentChatId: null,
  isDraftSession: false, // Draft mode - no session created yet
  isCreatingSession: false, // True while session is being created on first message
  pendingFirstMessage: null as string | null, // Store first message while creating session
  tasks: [],
  miniAgents: [],
  activeMiniAgentId: null,
  sidebarExpanded: true,
  activeTab: "history",
  isLoadingChats: false,
  isSendingMessage: false,
  isStreaming: false,
  lastSynced: {},
  hasMore: true,
  freeLimitExceeded: false,
  limitExceededType: "free_limit",
  lastFailedMessage: null,
  askFlowContext: null,

  setAskFlowContext: (context) => set({ askFlowContext: context }),

  setFreeLimitExceeded: (exceeded, type = "free_limit") => set({
    freeLimitExceeded: exceeded,
    limitExceededType: type
  }),

  clearLastFailedMessage: () => set({ lastFailedMessage: null }),

  retryLastFailedMessage: async () => {
    const { lastFailedMessage, addMessage } = get();
    if (!lastFailedMessage) return;

    const { chatId, content, attachments } = lastFailedMessage;
    set({ lastFailedMessage: null });

    try {
      await addMessage(chatId, { role: "user", content, attachments });
    } catch (error) {
      console.error("Retry failed:", error);
      // Re-store the failed message for another retry attempt
      set({ lastFailedMessage: { chatId, content, attachments } });
      throw error;
    }
  },

  loadChatsFromBackend: async (loadMore = false) => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;

    // Prevent fetching if not authenticated
    if (!isAuthenticated) {
      return;
    }

    // Only set loading if not loading more to prevent full list skeleton flash
    if (!loadMore) {
      set({ isLoadingChats: true });
    }

    try {
      const currentChats = get().chats;
      const skip = loadMore ? currentChats.length : 0;
      const limit = 20;

      const response = await chatAPI.getUserChats(limit, skip);

      if (response.status === 200 && response.data?.chats) {
        // Map backend chats - use MongoDB data as source of truth
        const backendChats = response.data.chats.map((chat: any) => {
          // Handle date parsing - support ISO strings and Date objects
          let createdAt: Date;
          let updatedAt: Date;

          try {
            createdAt = chat.created_at instanceof Date
              ? chat.created_at
              : new Date(chat.created_at || chat.createdAt); // Support both snake and camel

            updatedAt = chat.updated_at instanceof Date
              ? chat.updated_at
              : new Date(chat.updated_at || chat.updatedAt || chat.created_at); // Support both

            // Validate dates
            if (isNaN(createdAt.getTime())) {
              createdAt = new Date();
            }
            if (isNaN(updatedAt.getTime())) {
              updatedAt = createdAt;
            }
          } catch (e) {
            console.warn('Date parsing error:', e, chat);
            createdAt = new Date();
            updatedAt = new Date();
          }

          return {
            id: chat.id || chat.chat_id, // Support both
            title: chat.title || "New Chat",
            messages: [], // Will be loaded when session is opened
            miniAgents: [],
            createdAt,
            updatedAt,
            isPinned: chat.isPinned || false,  // From MongoDB - preserves rename
            isSaved: chat.isSaved || false,    // From MongoDB
            messageCount: chat.message_count || chat.messageCount || 0,
          };
        });

        // Determine if there are more chats to load
        set({ hasMore: backendChats.length === limit });

        if (loadMore) {
          // Append mode: Filter duplicates
          const existingIds = new Set(currentChats.map(c => c.id));
          const newUniqueChats = backendChats.filter((c: Chat) => !existingIds.has(c.id));
          set(state => ({ chats: [...state.chats, ...newUniqueChats] }));
        } else {
          // Smart Replace Mode
          // 1. Create map of existing chats to preserve their data (messages, miniAgents)
          const existingMap = new Map(currentChats.map(c => [c.id, c]));

          const mergedChats = backendChats.map((newChat: Chat) => {
            const existing = existingMap.get(newChat.id);
            // If we have detailed data locally, preserve it!
            if (existing && (existing.messages.length > 0 || existing.miniAgents.length > 0)) {
              return {
                ...newChat,
                messages: existing.messages,
                miniAgents: existing.miniAgents,
                // Keep local optimistic updates if any, but backend title prevails usually
              };
            }
            return newChat;
          });

          // 2. CRITICAL: Preserve currently active chat if it's "off-screen" (not in first 20)
          // This prevents deep-linked old chats from disappearing from state
          const currentId = get().currentChatId;
          if (currentId) {
            const activeInNew = mergedChats.find(c => c.id === currentId);
            if (!activeInNew) {
              const activeChat = existingMap.get(currentId);
              if (activeChat) {
                console.log('🛡️ Preserving active chat not in primary list:', currentId);
                mergedChats.push(activeChat);
              }
            }
          }

          set({ chats: mergedChats });

          // ✅ FIX: Do NOT auto-select any session on initial load
          // Let user explicitly click a session to activate it
          // This matches ChatGPT behavior and prevents confusion
        }

      } else {
        console.warn('⚠️ Invalid response from backend:', response);
      }
    } catch (error) {
      console.error('❌ Failed to load chats from backend:', error);
      if (!loadMore) {
        set({ chats: [], currentChatId: null });
      }
    } finally {
      set({ isLoadingChats: false });
    }
  },

  // Sync specific chat with backend - fetches ALL conversation messages
  syncChatWithBackend: async (chatId: string, force: boolean = false) => {
    // Check if synced recently (within 2s) unless forced
    // Reduced from 60s to 2s to ensure we get fresh data but debounce rapid calls
    const lastSyncTime = get().lastSynced[chatId] || 0;
    if (!force && Date.now() - lastSyncTime < 2000) {
      // console.log(`Stats for ${chatId} are fresh, skipping sync.`);
      return;
    }

    try {
      const response = await chatAPI.getChatHistory(chatId);
      if (response.status === 200 && response.data?.messages) {
        // Map messages with proper highlight field mapping AND action payload
        const messages = response.data.messages.map((msg: any) => {
          // Map highlights with correct field names (frontend uses startIndex/endIndex)
          const highlights = (msg.highlights || []).map((h: any) => ({
            id: h.id || h.highlightId || h.highlight_id || generateId(),
            text: h.text || h.highlightedText || '',
            color: h.color || '#FFD93D',
            startIndex: h.startIndex ?? h.start_index ?? h.startOffset ?? 0,
            endIndex: h.endIndex ?? h.end_index ?? h.endOffset ?? 0,
            note: h.note || '',
            createdAt: h.createdAt ? new Date(h.createdAt) : new Date(),
          }));


          // Extract action payload from metadata (restored from MongoDB)
          const actionPayload = msg.metadata?.action_payload || msg.action;

          // Disable auto-execution for restored history messages
          if (actionPayload?.payload) {
            actionPayload.payload.executeOnce = false;
          }

          return {
            id: msg.id || msg.message_id || generateId(),
            role: msg.role || "user",
            content: msg.content || msg.text || msg.message || msg.response || "",
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            highlights,
            action: actionPayload, // ✅ Restore confirmation state from database
          };
        });

        // Update ONLY the specific chat - prevent message mixing
        set((state) => ({
          chats: state.chats.map((chat) => {
            if (chat.id === chatId) {
              // Update this specific chat with messages from MongoDB
              return {
                ...chat,
                messages, // Full conversation from MongoDB - replaces local messages
                messageCount: messages.length, // Update message count
                title: response.data?.title || chat.title, // Use MongoDB title (preserves rename)
                updatedAt: response.data?.updated_at
                  ? new Date(response.data.updated_at)
                  : chat.updatedAt
              };
            }
            // Don't modify other chats - prevent message mixing
            return chat;
          }),
          lastSynced: { ...state.lastSynced, [chatId]: Date.now() },
        }));
      }
    } catch (error) {
      console.error('Failed to sync chat with backend:', error);
      // If session not found, remove it from local state
      if (error instanceof Error && (error.message.includes('404') || error.message.includes('not found'))) {
        set((state) => ({
          chats: state.chats.filter((chat) => chat.id !== chatId),
          currentChatId: state.currentChatId === chatId ? null : state.currentChatId
        }));
      }
    }
  },

  // Batch load session data (messages, highlights, mini agents) in ONE API call
  loadSessionData: async (sessionId: string) => {
    // Prevent duplicate loads
    const state = get();
    // Check if we recently synced this session (within 2s) to avoid double-fetching
    const lastSync = state.lastSynced[sessionId] || 0;
    if (Date.now() - lastSync < 2000) {
      console.log(`⏳ Skipping duplicate data fetch for ${sessionId}`);
      return;
    }

    if (state.isLoadingChats) {
      return;
    }

    set({ isLoadingChats: true });

    try {
      let data;

      // CACHE REMOVED: Always fetch fresh data from backend
      const response = await chatAPI.loadSessionData(sessionId);
      if (response.status === 200 && response.data) {
        data = response.data;
        console.log("🔥 [loadSessionData] API Response Data:", data);
      } else {
        console.error("❌ [loadSessionData] API Failed:", response);
      }

      if (data) {
        const { session, messages, highlights, miniAgents } = data;
        console.log(`📦 [loadSessionData] Parsed: ${messages?.length} messages, ${highlights?.length} highlights`);


        // 🔍 DEBUG: Log raw mini-agent data from backend
        console.log(`🔍 [loadSessionData] Raw miniAgents from backend:`, miniAgents);
        if (miniAgents?.length > 0) {
          miniAgents.forEach((agent: any) => {
            console.log(`   Agent ${agent.agentId || agent.id}: messages=${agent.messages?.length || 0}, hasConversation=${agent.hasConversation}`);
          });
        }

        // Build highlights map for O(1) lookup instead of O(n*m) filtering
        const highlightsByMessageId = new Map<string, any[]>();
        (highlights || []).forEach((h: any) => {
          const messageId = h.messageId || h.message_id;
          if (messageId) {
            if (!highlightsByMessageId.has(messageId)) {
              highlightsByMessageId.set(messageId, []);
            }
            highlightsByMessageId.get(messageId)!.push(h);
          }
        });

        if (!Array.isArray(messages)) {
          console.error("❌ [loadSessionData] 'messages' is not an array:", messages);
        }

        const mappedMessages = Array.isArray(messages) ? messages.map((msg: any) => {
          const messageHighlights = (highlightsByMessageId.get(msg.id) || []).map((h: any) => ({
            id: h.highlightId || h.id || h.highlight_id || generateId(),
            text: h.text || h.highlightedText || '',
            color: h.color || '#FFD93D',
            // ✅ CONSISTENT: Backend sends startIndex/endIndex
            startIndex: h.startIndex ?? h.start_index ?? 0,
            endIndex: h.endIndex ?? h.end_index ?? 0,
            messageHash: h.messageHash || h.message_hash,  // ✅ NEW: Drift detection
            note: h.note || '',
            createdAt: h.createdAt ? new Date(h.createdAt) : new Date(),
          }));

          // Debug log
          if (messageHighlights.length > 0 && import.meta.env.DEV) {
            console.log(`📍 [HIGHLIGHT_LOAD] Message ${msg.id}:`, {
              highlightCount: messageHighlights.length,
              highlights: messageHighlights.map(h => ({
                id: h.id,
                text: h.text.substring(0, 30) + '...',
                range: [h.startIndex, h.endIndex],
                color: h.color
              }))
            });
          }


          // Realign highlights to handle potential content drift
          // This fixes minor offset issues if the LLM output varied slightly or whitespace was normalized
          const realignedHighlights = realignHighlights(msg.content || msg.text || "", messageHighlights);

          // Extract action payload from metadata (restored from MongoDB)
          const actionPayload = msg.metadata?.action_payload || msg.action;

          // Disable auto-execution for restored session messages
          if (actionPayload?.payload) {
            actionPayload.payload.executeOnce = false;
          }

          return {
            id: msg.id || msg.message_id || generateId(),
            role: msg.role || "user",
            content: msg.content || msg.text || "",
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            highlights: realignedHighlights.filter((h: any) => !h._broken), // Filter out irreparably broken highlights
            action: actionPayload, // ✅ Restore confirmation state from database
          };
        }) : [];

        // Map mini agents with intelligent field mapping
        const mappedMiniAgents = (miniAgents || []).map((agent: any) => {
          const agentMessages = Array.isArray(agent.messages)
            ? agent.messages.map((m: any) => ({
              id: m.id || m.message_id || generateId(),
              role: m.role || 'user',
              content: m.content || m.text || '',
              timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
            }))
            : [];

          const mapped = {
            id: agent.agentId || agent.id || agent.agent_id || generateId(),
            messageId: agent.messageId || agent.message_id || '',
            sessionId: agent.sessionId || agent.session_id || sessionId,
            title: agent.title || "Mini Agent",
            // ✅ FIX: Use selectedText (matching TypeScript interface MiniAgent)
            selectedText: agent.selectedText || agent.selected_text || agent.snippet || "",
            messages: agentMessages,
            createdAt: agent.createdAt ? new Date(agent.createdAt) : new Date(),
            hasConversation: agentMessages.length > 0,
          };
          console.log('📦 [loadSessionData] Mapped mini-agent:', mapped.id, 'messageId:', mapped.messageId, 'hasConversation:', mapped.hasConversation, 'messagesCount:', agentMessages.length);
          if (agentMessages.length > 0) {
            console.log('📨 Mini-agent messages:', agentMessages.map(m => ({ role: m.role, content: m.content?.substring(0, 50) })));
          }
          return mapped;
        });

        console.log(`✅ [loadSessionData] Mapped ${mappedMiniAgents.length} mini-agents for session ${sessionId}`);

        const totalHighlights = mappedMessages.reduce((sum, msg) => sum + (msg.highlights?.length || 0), 0);

        // Check if chat exists in state
        const currentState = get();
        const existingChat = currentState.chats.find(c => c.id === sessionId);

        if (existingChat) {
          // Update existing chat - merge intelligently
          set((state) => ({
            chats: state.chats.map((chat) => {
              if (chat.id === sessionId) {
                return {
                  ...chat,
                  messages: mappedMessages,
                  miniAgents: mappedMiniAgents,
                  title: session?.title || chat.title,
                  updatedAt: session?.updated_at ? new Date(session.updated_at) : chat.updatedAt,
                  isPinned: session?.isPinned ?? chat.isPinned,
                  isSaved: session?.isSaved ?? chat.isSaved,
                };
              }
              return chat;
            }),
            miniAgents: mappedMiniAgents,
            isLoadingChats: false,
            isDraftSession: false, // Clear draft mode when loading session data
          }));
        } else {
          // Create new chat entry
          const newChat: Chat = {
            id: sessionId,
            title: session?.title || "Chat Session",
            messages: mappedMessages,
            miniAgents: mappedMiniAgents,
            createdAt: session?.created_at ? new Date(session.created_at) : new Date(),
            updatedAt: session?.updated_at ? new Date(session.updated_at) : new Date(),
            isPinned: session?.isPinned || false,
            isSaved: session?.isSaved || false,
          };

          set((state) => ({
            chats: [newChat, ...state.chats],
            miniAgents: mappedMiniAgents,
            isLoadingChats: false,
            isDraftSession: false, // Clear draft mode when loading session data
          }));
          console.log(`✅ Added new chat to state`);
        }

        // Check for active generation to resume (Page Reload Recovery)
        chatAPI.checkActiveGeneration(sessionId).then(async (res) => {
          if (res.status === 200 && res.data?.active_generation) {
            const gen = res.data.active_generation;
            console.log("🔄 Found active generation, resuming:", gen);

            const currentState = get();
            // If already handling it, skip
            if (currentState.isStreaming) return;

            // Identify or Create Placeholder Message
            let targetId = generateId();
            let isNew = true;
            const chat = currentState.chats.find(c => c.id === sessionId);
            if (chat && chat.messages.length > 0) {
              const last = chat.messages[chat.messages.length - 1];
              if (last.role === 'assistant') {
                targetId = last.id;
                isNew = false;
              }
            }

            if (isNew) {
              set(state => ({
                isStreaming: true,
                isSendingMessage: false,
                chats: state.chats.map(c => {
                  if (c.id === sessionId) {
                    return {
                      ...c,
                      messages: [...c.messages, {
                        id: targetId,
                        role: 'assistant',
                        content: 'Resuming...', // Visual indicator
                        timestamp: new Date()
                      }]
                    }
                  }
                  return c;
                })
              }));
            } else {
              set({ isStreaming: true, isSendingMessage: false });
            }

            if (['generating', 'streaming'].includes(gen.status)) {
              // Resume
              await chatAPI.resumeMessageStream(
                sessionId,
                gen.generation_id,
                (chunk) => {
                  set(state => ({
                    chats: state.chats.map(c => c.id === sessionId ? {
                      ...c,
                      messages: c.messages.map(m => m.id === targetId ? { ...m, content: m.content + chunk } : m)
                    } : c)
                  }));
                },
                (finalId) => {
                  set(state => ({
                    isStreaming: false,
                    chats: state.chats.map(c => c.id === sessionId ? {
                      ...c,
                      messages: c.messages.map(m => m.id === targetId ? {
                        ...m,
                        id: finalId,
                        content: m.content.replace('Resuming...', '') // Cleanup
                      } : m)
                    } : c)
                  }));
                },
                (err) => set({ isStreaming: false })
              );
            } else if (gen.status === 'completed') {
              // Finalize recovery
              chatAPI.resumeMessageStream(sessionId, gen.generation_id, () => { }, (fid) => {
                set(state => ({
                  isStreaming: false,
                  chats: state.chats.map(c => c.id === sessionId ? {
                    ...c,
                    messages: c.messages.map(m => m.id === targetId ? { ...m, id: fid } : m)
                  } : c)
                }));
              }, () => { });
            }
          }
        }).catch(e => console.warn("Active gen check failed", e));

      } else {
        set({ isLoadingChats: false });
        throw new Error(response.error || 'Failed to load session data');
      }
    } catch (error) {
      set({ isLoadingChats: false });
      throw error;
    }
  },

  createChat: async () => {
    try {
      console.log('🆕 Creating new chat session...');
      const response = await chatAPI.createNewChat();
      console.log('📥 Create chat response:', response);

      if (response.status === 201 && response.data?.chat_id) {
        const chatId = response.data.chat_id;

        // Check if chat already exists (prevent duplicates)
        const state = get();
        const existingChat = state.chats.find(c => c.id === chatId);
        if (existingChat) {
          // Chat already exists - just set it as current
          set({ currentChatId: chatId });
          return chatId;
        }

        // Create new chat object from backend response
        const newChat: Chat = {
          id: chatId,
          title: (response.data.title === "Untitled" ? "New Chat" : response.data.title) || "New Chat",
          messages: [],
          miniAgents: [],
          createdAt: new Date(response.data.created_at),
          updatedAt: new Date(response.data.created_at),
          isPinned: response.data.isPinned || false,  // From MongoDB
          isSaved: response.data.isSaved || false,    // From MongoDB
        };

        // Add to frontend state - prepend to list
        set((state) => {
          // Double-check for duplicates before adding
          if (state.chats.find(c => c.id === chatId)) {
            console.log(`⚠️ Chat ${chatId} already exists, setting as current`);
            return { currentChatId: chatId };
          }
          console.log(`✅ Added new chat to state: ${chatId} (${newChat.title})`);
          return {
            chats: [newChat, ...state.chats],
            currentChatId: chatId,
          };
        });

        // No localStorage - MongoDB is source of truth
        return chatId;
      } else {
        console.error('❌ Invalid response from create chat:', response);
        throw new Error('Failed to create chat: Invalid response');
      }
    } catch (error) {
      console.error("❌ Failed to create new chat:", error);
      throw error; // Don't fallback - let error propagate
    }
  },

  // Returns true if current chat exists and has no messages
  isSessionEmpty: () => {
    const state = get();
    const current = state.chats.find((c) => c.id === state.currentChatId);
    return !!current && current.messages.length === 0;
  },

  // Ensures there is a session to add the first message into
  // This is called when user sends their FIRST message
  createSessionIfNeeded: async () => {
    const state = get();

    // If in draft mode, create a real session now
    if (state.isDraftSession) {
      console.log('📝 Converting draft to real session...');

      // Set creating state for smooth UI transition
      set({ isCreatingSession: true });

      try {
        const newId = await get().createChat();
        set({ isDraftSession: false, isCreatingSession: false });
        return newId;
      } catch (error) {
        set({ isCreatingSession: false });
        throw error;
      }
    }

    const current = state.chats.find((c) => c.id === state.currentChatId);
    if (!current || current.messages.length > 0) {
      set({ isCreatingSession: true });
      try {
        const newId = await get().createChat();
        set({ isCreatingSession: false });
        return newId;
      } catch (error) {
        set({ isCreatingSession: false });
        throw error;
      }
    }
    return current.id;
  },

  // Enter draft mode - NO backend call, NO session created
  // Just shows an empty chat UI ready for input
  startDraftSession: () => {
    console.log('📝 Starting draft session (no backend call)');
    set({
      currentChatId: null,
      isDraftSession: true,
      isCreatingSession: false,
      pendingFirstMessage: null,
      activeMiniAgentId: null
    });
  },

  // Clear draft mode (e.g., when navigating away)
  clearDraftSession: () => {
    set({ isDraftSession: false, isCreatingSession: false, pendingFirstMessage: null });
  },

  // Starts a fresh session - NOW uses draft mode instead of creating immediately
  startNewSession: async () => {
    const state = get();
    const current = state.chats.find((c) => c.id === state.currentChatId);

    // If already in draft mode, stay there
    if (state.isDraftSession) {
      return null;
    }

    // If current chat is empty, reuse it
    if (current && current.messages.length === 0) {
      return current.id;
    }

    // Otherwise, enter draft mode (don't create session yet)
    get().startDraftSession();
    return null; // Return null to indicate draft mode
  },

  setCurrentChat: (id) => {
    // Clear draft mode when selecting an existing chat
    set({ currentChatId: id, isDraftSession: false, activeMiniAgentId: null });

    // Note: Data loading is now handled by Chat.tsx useEffect when sessionId changes
    // This prevents double-loading when both sidebar and route change trigger loads
  },

  addMessage: async (chatId, message) => {
    // Verify chat exists before adding message
    const state = get();
    let targetChat = state.chats.find(c => c.id === chatId);

    // If chat doesn't exist, create it first
    if (!targetChat) {
      console.warn(`Chat ${chatId} not found, creating new chat`);
      const newChatId = await get().createChat();
      if (!newChatId) {
        throw new Error("Failed to create chat for message");
      }
      chatId = newChatId;
      targetChat = get().chats.find(c => c.id === chatId);
      if (!targetChat) {
        throw new Error("Failed to find created chat");
      }
    }

    const tempId = generateId();
    const fullMessage: Message = {
      ...message,
      id: tempId,
      timestamp: new Date(),
    };

    // Optimistic update - ONLY update the target chat
    set((state) => {
      const chats = state.chats.map((chat) => {
        if (chat.id === chatId) {
          // Only update this specific chat - prevent message mixing
          const updatedMessages = [...chat.messages, fullMessage];
          const isFirstMessage = chat.messages.length === 0;
          const shouldDeriveTitle = isFirstMessage && ["New Chat", "Untitled", ""].includes(chat.title);
          // Persist a local snapshot for potential rename
          if (shouldDeriveTitle) {
            // Fire-and-forget persistence after state update
            const newTitle = deriveTitleFrom(fullMessage.content);
            // Schedule rename to avoid blocking UI update
            queueMicrotask(() => {
              try { get().renameChat(chatId, newTitle); } catch { /* noop */ }
            });
          }
          return {
            ...chat,
            messages: updatedMessages,
            messageCount: updatedMessages.length, // Update message count
            updatedAt: new Date(),
            // Immediately mark a useful session name from the first user message
            title: shouldDeriveTitle ? deriveTitleFrom(fullMessage.content) : chat.title,
          };
        }
        // Don't modify other chats
        return chat;
      });
      return { chats, isSendingMessage: true };
    });

    try {
      // Create a temporary AI message for streaming
      let aiTempId = generateId();
      const aiMessage: Message = {
        id: aiTempId,
        role: 'assistant',
        content: '', // Start empty, will be filled as chunks arrive
        timestamp: new Date(),
        action: undefined,
      };

      // Add empty AI message to show loading state
      set(state => ({
        chats: state.chats.map(chat => {
          if (chat.id === chatId) {
            const updatedMessages = [...chat.messages, aiMessage];
            return {
              ...chat,
              messages: updatedMessages,
              messageCount: updatedMessages.length,
              // Keep title that we just derived from user prompt; backend/title events can override later
              title: chat.title,
            };
          }
          return chat;
        }),
        isSendingMessage: true,
        isStreaming: false
      }));

      // 🚀 OPTIMIZED streaming: Batch updates for smooth rendering
      let pendingChunk = '';
      let isFirstChunk = true;
      let updateScheduled = false;
      let lastFlushTime = 0;
      const MIN_FLUSH_INTERVAL = 50; // 20fps - reduces re-renders, smoother UI
      const MIN_CHUNK_SIZE = 10; // Reduced from 20 - show first content faster

      const flushChunks = () => {
        if (!pendingChunk) {
          updateScheduled = false;
          return;
        }

        const now = performance.now();
        const timeSinceLastFlush = now - lastFlushTime;

        // For first chunk, flush immediately to end "thinking" state quickly
        const shouldFlushImmediately = isFirstChunk && pendingChunk.length > 0;

        // Batch more aggressively for subsequent chunks
        if (!shouldFlushImmediately && timeSinceLastFlush < MIN_FLUSH_INTERVAL && pendingChunk.length < MIN_CHUNK_SIZE) {
          updateScheduled = false;
          scheduleUpdate();
          return;
        }

        const chunk = pendingChunk;
        pendingChunk = '';
        updateScheduled = false;
        lastFlushTime = now;

        // 🚀 Single atomic state update
        set(state => {
          const chatIndex = state.chats.findIndex(c => c.id === chatId);
          if (chatIndex === -1) return state;

          const chat = state.chats[chatIndex];
          const msgIndex = chat.messages.findIndex(m => m.id === aiTempId);
          if (msgIndex === -1) return state;

          // Create new message with appended content
          const updatedMessage = {
            ...chat.messages[msgIndex],
            content: chat.messages[msgIndex].content + chunk
          };

          // Create new messages array with updated message
          const newMessages = [
            ...chat.messages.slice(0, msgIndex),
            updatedMessage,
            ...chat.messages.slice(msgIndex + 1)
          ];

          // Create new chats array with updated chat
          const newChats = [
            ...state.chats.slice(0, chatIndex),
            { ...chat, messages: newMessages },
            ...state.chats.slice(chatIndex + 1)
          ];

          return {
            ...state,
            chats: newChats,
            isStreaming: true,
            isSendingMessage: false
          };
        });
      };

      const scheduleUpdate = () => {
        if (updateScheduled) return;
        updateScheduled = true;
        // Use RAF directly for smoother visual updates
        requestAnimationFrame(flushChunks);
      };

      // 🛡️ Metadata filter (uses shared utility)
      const filterInternalMetadata = createMetadataFilter();

      // Stream AI response using streaming endpoint
      await chatAPI.sendMessageStream(
        chatId,
        message.content,
        // onChunk - GPT-style append-only streaming
        (chunk: string) => {
          // 🛡️ SECURITY: Filter out any internal metadata that shouldn't be shown to users
          // This is a safety net in case backend accidentally sends metadata
          const filteredChunk = filterInternalMetadata(chunk);

          // Skip empty chunks after filtering
          if (!filteredChunk) return;

          // First chunk - immediately switch from thinking to streaming
          if (isFirstChunk) {
            isFirstChunk = false;
            set(state => ({
              ...state,
              isStreaming: true,
              isSendingMessage: false
            }));
          }

          // Accumulate chunk and schedule update
          pendingChunk += filteredChunk;
          scheduleUpdate();
        },
        // onComplete - finalize message with real ID from backend
        (messageId: string, metadata?: { key_source?: string; model?: string; usage?: any }) => {
          // Flush any remaining content immediately
          if (pendingChunk) {
            const finalChunk = pendingChunk;
            pendingChunk = '';

            set(state => ({
              chats: state.chats.map(chat => {
                if (chat.id === chatId) {
                  const updatedMessages = chat.messages.map(m =>
                    m.id === aiTempId
                      ? {
                        ...m,
                        id: messageId,
                        content: m.content + finalChunk,
                        keySource: metadata?.key_source as "platform" | "user" | undefined,
                        model: metadata?.model
                      }
                      : m
                  );
                  return {
                    ...chat,
                    messages: updatedMessages,
                    messageCount: updatedMessages.length,
                    updatedAt: new Date()
                  };
                }
                return chat;
              }),
              isSendingMessage: false,
              isStreaming: false
            }));
          } else {
            set(state => ({
              chats: state.chats.map(chat => {
                if (chat.id === chatId) {
                  const updatedMessages = chat.messages.map(m =>
                    m.id === aiTempId
                      ? {
                        ...m,
                        id: messageId,
                        keySource: metadata?.key_source as "platform" | "user" | undefined,
                        model: metadata?.model
                      }
                      : m
                  );
                  return {
                    ...chat,
                    messages: updatedMessages,
                    messageCount: updatedMessages.length,
                    updatedAt: new Date()
                  };
                }
                return chat;
              }),
              isSendingMessage: false,
              isStreaming: false
            }));
          }
        },
        // onError - handle streaming errors
        (error: string) => {
          set({ isSendingMessage: false, isStreaming: false });
          console.error('[Chat] Stream failed:', error);

          // Store failed message for retry (only for non-limit errors)
          const isLimitError =
            error.includes('ALL_KEYS_EXHAUSTED') ||
            error.includes('keys are temporarily exhausted') ||
            error.includes('all your API keys') ||
            error.includes('free AI requests') ||
            error.includes('FREE_LIMIT_EXCEEDED') ||
            error.includes('Free limit reached');

          if (!isLimitError) {
            // Store the failed message for retry
            set({
              lastFailedMessage: {
                chatId,
                content: message.content,
                attachments: message.attachments
              }
            });
          }

          // Check for API key related errors
          if (
            error.includes('ALL_KEYS_EXHAUSTED') ||
            error.includes('keys are temporarily exhausted') ||
            error.includes('all your API keys')
          ) {
            // All keys exhausted - different UI needed
            set({ freeLimitExceeded: true, limitExceededType: "all_keys_exhausted" });
          } else if (
            error.includes('free AI requests') ||
            error.includes('FREE_LIMIT_EXCEEDED') ||
            error.includes('Free limit reached')
          ) {
            // Free tier exhausted - prompt to add key
            set({ freeLimitExceeded: true, limitExceededType: "free_limit" });
          }

          // Remove temp message on error
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                return {
                  ...chat,
                  messages: chat.messages.filter(m => m.id !== aiTempId)
                };
              }
              return chat;
            })
          }));
          throw new Error(error);
        },
        // onAction - attach structured action data to the streaming AI message
        (action: any) => {
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                const updatedMessages = chat.messages.map(m =>
                  m.id === aiTempId ? { ...m, action } : m
                );
                return { ...chat, messages: updatedMessages };
              }
              return chat;
            })
          }));
        },
        // onStatus - update streaming status for long-running tasks (e.g., deep research)
        (status: string) => {
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                const updatedMessages = chat.messages.map(m =>
                  m.id === aiTempId ? { ...m, streamStatus: status } : m
                );
                return { ...chat, messages: updatedMessages };
              }
              return chat;
            })
          }));
        }, // End onStatus

        // onTitle - update chat title in real-time
        (title: string) => {
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                return { ...chat, title: title };
              }
              return chat;
            })
          }));
          // Persist streamed title to MongoDB
          try { get().renameChat(chatId, title); } catch { /* noop */ }
        },
        // ✅ onStart: CRITICAL FIX - Swap temp ID with real ID immediately
        (messageId: string) => {
          console.log(`🔄 Swapping temp ID ${aiTempId} with real ID ${messageId}`);

          // 1. Update store
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                return {
                  ...chat,
                  messages: chat.messages.map(m =>
                    m.id === aiTempId ? { ...m, id: messageId } : m
                  )
                };
              }
              return chat;
            })
          }));

          // 2. Update local variable so subsequent chunks target the correct message
          aiTempId = messageId;
        }
      );

    } catch (error) {
      console.error("Failed to send message:", error);
      // Revert optimistic update on failure - ONLY for target chat
      set((state) => ({
        chats: state.chats.map((chat) => {
          if (chat.id === chatId) {
            return { ...chat, messages: chat.messages.filter((m) => m.id !== tempId) };
          }
          return chat;
        }),
        isSendingMessage: false,
        isStreaming: false
      }));
      throw error; // Re-throw to let caller handle
    }
  },

  deleteChat: async (id) => {
    // Optimistic deletion
    const originalChats = get().chats;
    const originalCurrentChatId = get().currentChatId;

    set((state) => {
      const chats = state.chats.filter((chat) => chat.id !== id);
      // If deleted chat was current, switch to most recent chat
      let newCurrentChatId = state.currentChatId;
      if (state.currentChatId === id) {
        if (chats.length > 0) {
          // Sort by pinned first, then by updatedAt
          const sortedChats = [...chats].sort((a: Chat, b: Chat) => {
            if (a.isPinned && !b.isPinned) return -1;
            if (!a.isPinned && b.isPinned) return 1;
            return b.updatedAt.getTime() - a.updatedAt.getTime();
          });
          newCurrentChatId = sortedChats[0].id;
        } else {
          newCurrentChatId = null;
        }
      }
      // No localStorage - MongoDB is source of truth
      return { chats, currentChatId: newCurrentChatId };
    });

    try {
      const response = await chatAPI.deleteChat(id);
      if (response.status === 200) {
        // Deletion successful - on refresh, deleted chat will NOT come back (MongoDB deleted it)
        console.log("Chat deleted successfully from MongoDB");
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
      // Revert if deletion fails
      set({ chats: originalChats, currentChatId: originalCurrentChatId });
      throw error; // Re-throw to show error to user
    }
  },

  renameChat: async (id, title) => {
    // Optimistic update
    set((state) => ({
      chats: state.chats.map((chat) =>
        chat.id === id ? { ...chat, title } : chat
      ),
    }));

    try {
      const response = await chatAPI.renameChat(id, title);
      if (response.status === 200) {
        // Title updated in MongoDB - will persist after refresh
        // Use title from backend response if available
        const confirmedTitle = response.data?.title || title;
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === id ? { ...chat, title: confirmedTitle } : chat
          ),
        }));
      }
    } catch (error) {
      console.error("Failed to rename chat:", error);
      // Reload from backend on error to get correct title
      get().loadChatsFromBackend();
      throw error;
    }
  },

  pinChat: async (id, isPinned) => {
    // Optimistic update
    set((state) => ({
      chats: state.chats.map((chat) =>
        chat.id === id ? { ...chat, isPinned } : chat
      ),
    }));

    try {
      await chatAPI.pinChat(id, isPinned);
      // On refresh, pin status will persist (MongoDB updated)
    } catch (error) {
      console.error("Failed to pin chat:", error);
      // Reload from backend on error
      get().loadChatsFromBackend();
    }
  },

  saveChat: async (id, isSaved) => {
    // Optimistic update
    set((state) => ({
      chats: state.chats.map((chat) =>
        chat.id === id ? { ...chat, isSaved } : chat
      ),
    }));

    try {
      await chatAPI.saveChat(id, isSaved);
      // On refresh, save status will persist (MongoDB updated)
    } catch (error) {
      console.error("Failed to save chat:", error);
      // Reload from backend on error
      get().loadChatsFromBackend();
    }
  },

  createTask: async (title, description, dueDate, timeSeconds, imageUrl) => {
    try {
      // Combine title and description or just send title as description
      // Backend expects 'description'
      // If we have both, maybe format as "Title: Description" or just use title if description is empty
      const finalDesc = description ? `${title}\n${description}` : title;

      const resp = await chatAPI.confirmTask({
        description: finalDesc,
        due_date: dueDate ? dueDate.toISOString() : undefined,
        time_seconds: timeSeconds,
        image_url: imageUrl,
      });

      if (resp.status === 200 && resp.data) {
        const t = resp.data;
        const newTask: Task = {
          id: t.task_id,
          title: t.description,
          completed: false,
          createdAt: new Date(),
          dueDate: t.due_date ? new Date(t.due_date) : undefined,
          timeSeconds: t.time_seconds,
          imageUrl: t.image_url,
        };

        set((state) => ({ tasks: [newTask, ...state.tasks] }));
        return newTask.id;
      }
    } catch (error) {
      console.error("Failed to create task:", error);
      toast({ title: "Failed to create task", variant: "destructive" });
    }
    return "";
  },

  toggleTask: async (id) => {
    const task = get().tasks.find((t) => t.id === id);
    if (!task) return;

    const newCompleted = !task.completed;
    const newStatus = newCompleted ? "completed" : "pending";

    // Optimistic update
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, completed: newCompleted } : t
      ),
    }));

    try {
      await chatAPI.updateTask({
        task_id: id,
        status: newStatus
      });
    } catch (error) {
      console.error("Failed to toggle task:", error);
      // Revert on failure
      set((state) => ({
        tasks: state.tasks.map((t) =>
          t.id === id ? { ...t, completed: !newCompleted } : t
        ),
      }));
      toast({ title: "Failed to update task", variant: "destructive" });
    }
  },

  deleteTask: async (id) => {
    const originalTasks = get().tasks;

    // Optimistic delete
    set((state) => ({ tasks: state.tasks.filter((task) => task.id !== id) }));

    try {
      await chatAPI.cancelTask({ task_id: id });
    } catch (error) {
      console.error("Failed to delete task:", error);
      // Revert on failure
      set({ tasks: originalTasks });
      toast({ title: "Failed to delete task", variant: "destructive" });
    }
  },

  loadTasksFromBackend: async () => {
    try {
      console.log("📋 Loading tasks from backend...");
      const [pending, completed] = await Promise.all([
        chatAPI.getTasks("pending"),
        chatAPI.getTasks("completed"),
      ]);

      console.log("📋 Pending response:", pending);
      console.log("📋 Completed response:", completed);

      const mapTasks = (resp: any, completedFlag: boolean): Task[] => {
        // Handle both successful response formats
        const taskData = resp.data || [];
        if (resp.error || !Array.isArray(taskData)) {
          console.warn(`⚠️ Invalid task response for ${completedFlag ? 'completed' : 'pending'}:`, resp);
          return [];
        }
        return taskData.map((t: any) => {
          // ☁️ Handle due_date - can be ISO string or datetime object
          let dueDate: Date | undefined = undefined;
          if (t.due_date) {
            try {
              if (typeof t.due_date === 'string') {
                dueDate = new Date(t.due_date);
              } else if (t.due_date instanceof Date) {
                dueDate = t.due_date;
              } else if (t.due_date.$date) {
                // MongoDB extended JSON format
                dueDate = new Date(t.due_date.$date);
              }
            } catch (e) {
              console.warn("Failed to parse due_date:", t.due_date, e);
            }
          }

          return {
            id: t.task_id,
            title: t.description || "Untitled Task",
            completed: completedFlag,
            createdAt: dueDate || new Date(),
            dueDate: dueDate,
            timeSeconds: t.time_seconds,
            imageUrl: t.image_url,
          };
        });
      };

      const tasks = [...mapTasks(pending, false), ...mapTasks(completed, true)];
      set({ tasks });
      console.log(`✅ Loaded ${tasks.length} tasks from backend (${pending.data?.length || 0} pending, ${completed.data?.length || 0} completed)`);
    } catch (e) {
      console.error("❌ Failed to load tasks from backend", e);
    }
  },

  confirmTaskDraft: async (messageId, description, dueDate) => {
    try {
      // ☁️ Ensure due_date is in correct format (ISO or YYYY-MM-DD HH:MM)
      // If dueDate is missing, we can't create the task
      if (!dueDate) {
        throw new Error("Due date is required to create a reminder. Please provide a date and time.");
      }

      // Format dueDate - it should already be a string (ISO or YYYY-MM-DD HH:MM)
      let formattedDueDate = dueDate;
      if (typeof dueDate === 'string') {
        // If it's already a string, use it as-is (should be ISO or YYYY-MM-DD HH:MM)
        formattedDueDate = dueDate;
      }

      // 🧹 Pass session_id to clear draft after confirmation (prevents duplicates)
      const currentSessionId = get().currentChatId;

      const resp = await chatAPI.confirmTask({
        description,
        due_date: formattedDueDate,
        session_id: currentSessionId  // Clear draft on backend after successful creation
      });
      if (resp.status === 200 && resp.data) {
        const t = resp.data;
        const newTask: Task = {
          id: t.task_id,
          title: t.description,
          completed: false,
          createdAt: new Date(t.due_date || new Date().toISOString()),
          dueDate: t.due_date ? new Date(t.due_date) : undefined,
        };

        // Get confirmation message from backend
        const confirmationMsg = t.confirmation_message || `Reminder created successfully for ${description}`;

        set((state) => ({
          tasks: [newTask, ...state.tasks],
          chats: state.chats.map((chat) => ({
            ...chat,
            messages: chat.messages.map((m) =>
              m.id === messageId
                ? {
                  ...m,
                  action: m.action ? {
                    ...m.action,
                    confirmed: true,
                    confirmationMessage: confirmationMsg,
                    confirmedAt: new Date().toISOString()
                  } : m.action
                }
                : m
            ),
          })),
        }));

        // ✅ Database is the single source of truth - no localStorage
        // Refresh task list from backend
        await get().loadTasksFromBackend();

        // Sync chat with backend to persist confirmation state in MongoDB
        const state = get();
        if (state.currentChatId) {
          await get().syncChatWithBackend(state.currentChatId);
        }
      }
    } catch (e) {
      console.error("Failed to confirm task draft", e);
      throw e;
    }
  },

  createMiniAgent: async (messageId, selectedText, userPrompt?: string) => {
    try {
      const state = get();
      const currentChat = state.chats.find(c => c.id === state.currentChatId);

      if (!currentChat) {
        throw new Error("No active chat session");
      }

      console.log('🤖 Creating/Getting Mini Agent for message:', messageId);

      // ⚡ Optimistic: create a temporary agent for instant UI open
      const tempId = `temp_agent_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const optimisticAgent: MiniAgent = {
        id: tempId,
        messageId,
        sessionId: currentChat.id,
        selectedText,
        messages: [],
        createdAt: new Date(),
        hasConversation: false,
      };

      set((state) => ({
        miniAgents: [...state.miniAgents, optimisticAgent],
        activeMiniAgentId: tempId,
        chats: [...state.chats],
      }));

      // Call backend - it will return existing agent or create new one
      const response = await chatAPI.createMiniAgent({
        messageId,
        sessionId: currentChat.id,
        selectedText,
        title: userPrompt
      });

      if (response.status === 201 && response.data?.agentId) {
        const agentData = response.data;
        const isExisting = agentData.isExisting || false;

        console.log(isExisting ? '♻️ Reusing existing Mini Agent:' : '✅ Mini Agent created in database:', agentData.agentId);
        console.log('📦 Backend returned:', {
          agentId: agentData.agentId,
          isExisting,
          hasConversation: agentData.hasConversation,
          messagesCount: agentData.messages?.length || 0
        });

        // Map messages from backend format
        const messages = (agentData.messages || []).map((msg: any) => ({
          id: msg.id || generateId(),
          role: msg.role || "user",
          content: msg.content || msg.text || "",
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        }));

        console.log('📨 Mapped messages:', messages.length, messages.map(m => ({ role: m.role, contentLength: m.content?.length })));

        const agent: MiniAgent = {
          id: agentData.agentId,
          messageId: agentData.messageId,
          sessionId: agentData.sessionId || currentChat.id,
          selectedText: agentData.selectedText,
          messages,
          createdAt: agentData.createdAt ? new Date(agentData.createdAt) : new Date(),
          hasConversation: agentData.hasConversation || messages.length > 0,  // ✅ Calculate from messages if not provided
        };

        console.log('🤖 Final agent state:', { id: agent.id, hasConversation: agent.hasConversation, messagesCount: agent.messages.length });

        // Check if agent already exists in state
        const existingAgentIndex = state.miniAgents.findIndex(a => a.id === agent.id);

        if (existingAgentIndex !== -1) {
          // Replace optimistic or existing agent by id
          set((state) => ({
            miniAgents: state.miniAgents.map(a => (a.id === tempId || a.id === agent.id) ? agent : a),
            activeMiniAgentId: agent.id,
            chats: [...state.chats],
          }));
          console.log('📝 Updated existing/optimistic Mini Agent:', agent.id);
        } else {
          // Replace optimistic temp with real
          set((state) => ({
            miniAgents: state.miniAgents.map(a => a.id === tempId ? agent : a),
            activeMiniAgentId: agent.id,
            chats: [...state.chats],
          }));
          console.log('✅ Mini Agent created and reconciled:', agent.id);
        }

        return agent.id;
      } else {
        console.error('❌ Invalid response:', response);
        throw new Error("Failed to create mini-agent");
      }
    } catch (error) {
      console.error("❌ Failed to create mini-agent:", error);
      // Rollback optimistic temp agent
      try {
        set((state) => ({
          miniAgents: state.miniAgents.filter(a => !a.id.startsWith('temp_agent_')),
          activeMiniAgentId: state.activeMiniAgentId && state.activeMiniAgentId.startsWith('temp_agent_') ? null : state.activeMiniAgentId,
        }));
        toast({ title: "Mini Agent", description: "Failed to create. Please try again.", variant: "destructive" });
      } catch { }
      throw error;
    }
  },

  // Fetch mini agent from backend when opened
  fetchMiniAgent: async (agentId: string) => {
    try {
      const response = await chatAPI.getMiniAgent(agentId);

      if (response.status === 200 && response.data) {
        const agentData = response.data;

        // Map messages from backend format
        const messages = (agentData.messages || []).map((msg: any) => ({
          id: msg.id || generateId(),
          role: msg.role || "user",
          content: msg.content || "",
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        }));

        // Update mini agent in state
        set((state) => ({
          miniAgents: state.miniAgents.map((agent) =>
            agent.id === agentId
              ? {
                ...agent,
                sessionId: agent.sessionId || agentData.sessionId || state.currentChatId || undefined,
                messages,
                selectedText: agentData.selectedText || agent.selectedText,
              }
              : agent
          ),
        }));
      }
    } catch (error) {
      console.error("❌ Failed to fetch mini-agent:", error);
    }
  },

  addMiniAgentMessage: async (agentId, content) => {
    try {
      console.log('💬 Sending Mini Agent message:', agentId);

      // Optimistic update - add user message immediately for instant UI feedback
      const userMessage: MiniAgentMessage = {
        id: generateId(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      // Find the agent's messageId and sessionId for chat update
      const state = get();
      const agent = state.miniAgents.find(a => a.id === agentId);
      const messageId = agent?.messageId;
      const sessionId = state.currentChatId;

      set((state) => ({
        miniAgents: state.miniAgents.map((agent) =>
          agent.id === agentId
            ? {
              ...agent,
              messages: [...agent.messages, userMessage],
              hasConversation: true // ✅ Instant UI update
            }
            : agent
        ),
        // ✅ CRITICAL: Trigger chat re-render to show icon immediately
        chats: [...state.chats],
      }));

      // Call backend - this stores in database and generates AI response
      const response = await chatAPI.sendMiniAgentMessage(agentId, content);

      if (response.status === 200 && response.data) {
        console.log('✅ Mini Agent response received from database');
        console.log('📦 Full response data:', JSON.stringify(response.data, null, 2));
        console.log('👤 User message content:', response.data.userMessage?.content);
        console.log('🤖 AI message content:', response.data.aiMessage?.content);
        console.log('📏 AI content length:', response.data.aiMessage?.content?.length || 0);

        // ✅ CRITICAL: Verify AI content is not empty
        if (!response.data.aiMessage?.content || response.data.aiMessage.content.trim() === '') {
          console.error('❌ EMPTY AI RESPONSE DETECTED!');
          console.error('❌ Raw aiMessage:', response.data.aiMessage);
          throw new Error("AI response is empty - please check backend");
        }

        // Replace optimistic user message with confirmed one from database
        const confirmedUserMessage: MiniAgentMessage = {
          id: response.data.userMessage?.id || userMessage.id,
          role: "user",
          content: response.data.userMessage?.content || content,
          timestamp: response.data.userMessage?.timestamp
            ? new Date(response.data.userMessage.timestamp)
            : new Date(),
        };

        // Add AI response from database
        const aiMessage: MiniAgentMessage = {
          id: response.data.aiMessage?.id || generateId(),
          role: "assistant",
          content: response.data.aiMessage?.content || "",
          timestamp: response.data.aiMessage?.timestamp
            ? new Date(response.data.aiMessage.timestamp)
            : new Date(),
        };

        console.log('📝 Formatted AI message to store:', aiMessage);
        console.log('💬 AI content to display:', aiMessage.content);

        // ✅ CRITICAL FIX: Update both miniAgents AND chats to trigger UI refresh
        set((state) => ({
          miniAgents: state.miniAgents.map((agent) =>
            agent.id === agentId
              ? {
                ...agent,
                messages: [
                  ...agent.messages.filter(m => m.id !== userMessage.id),
                  confirmedUserMessage,
                  aiMessage,
                ],
                hasConversation: true,  // Mark conversation started (synced to database)
              }
              : agent
          ),
          // ✅ CRITICAL: Force chat re-render to update MessageBubble hasConversation prop
          chats: state.chats.map(chat => {
            if (chat.id === sessionId && chat.miniAgents) {
              return {
                ...chat,
                miniAgents: chat.miniAgents.map(ma =>
                  ma.id === agentId
                    ? { ...ma, hasConversation: true, messages: [confirmedUserMessage, aiMessage] }
                    : ma
                )
              };
            }
            return chat;
          }),
        }));

        console.log('✅ Mini Agent messages updated in state and database');

        // Log the updated state for verification
        const updatedAgent = get().miniAgents.find(a => a.id === agentId);
        console.log('🔍 Updated agent in state:', updatedAgent);
        console.log('📨 All messages in agent:', updatedAgent?.messages);
      } else {
        // Error: Remove optimistic message and restore state
        console.error('❌ Failed to send message, removing optimistic update');
        set((state) => ({
          miniAgents: state.miniAgents.map((agent) =>
            agent.id === agentId
              ? { ...agent, messages: agent.messages.filter(m => m.id !== userMessage.id), hasConversation: false }
              : agent
          ),
          chats: [...state.chats], // Trigger refresh
        }));
        throw new Error("Failed to send mini-agent message to database");
      }
    } catch (error) {
      console.error("❌ Failed to send mini-agent message:", error);
      // Error already handled above - optimistic message removed
      throw error;
    }
  },

  deleteMiniAgent: async (id: string) => {
    try {
      console.log('🗑️ Deleting Mini Agent:', id);

      // Get the Mini Agent before deletion to know which message it's tied to
      const state = get();
      const agent = state.miniAgents.find(a => a.id === id);
      const messageId = agent?.messageId;

      // Optimistic update - remove from state immediately for instant UI update
      set((state) => ({
        miniAgents: state.miniAgents.filter((agent) => agent.id !== id),
        activeMiniAgentId: state.activeMiniAgentId === id ? null : state.activeMiniAgentId,
      }));

      // Call backend to delete from database
      const response = await chatAPI.deleteMiniAgent(id);

      if (response.status === 200 && response.data?.success) {
        console.log('✅ Mini Agent deleted from database:', id);

        // Force re-render of messages to update icon visibility
        // Trigger a state update to notify components that mini agent is gone
        if (messageId) {
          set((state) => ({
            // Touch the chats array to trigger reactivity
            chats: [...state.chats]
          }));
        }
      } else {
        // Restore on failure
        console.error('❌ Failed to delete from backend, restoring...');
        if (agent) {
          set((state) => ({
            miniAgents: [...state.miniAgents, agent],
          }));
        }
        throw new Error('Failed to delete mini-agent from database');
      }
    } catch (error) {
      console.error("❌ Failed to delete mini-agent:", error);
      throw error;
    }
  },

  updateMiniAgentSnippet: async (agentId: string, selectedText: string) => {
    try {
      console.log('📝 Updating snippet for Mini Agent:', agentId);
      console.log('📝 New snippet text:', selectedText.substring(0, 100) + '...');

      // Get old snippet for comparison
      const oldAgent = get().miniAgents.find(a => a.id === agentId);
      console.log('📝 Old snippet text:', oldAgent?.selectedText.substring(0, 100) + '...');

      // Optimistic update - update state immediately
      set((state) => ({
        miniAgents: state.miniAgents.map(a =>
          a.id === agentId ? { ...a, selectedText } : a
        ),
        chats: [...state.chats], // Trigger re-render
      }));

      console.log('✅ Snippet updated in state (optimistic)');

      // Update in database
      const response = await chatAPI.updateMiniAgentSnippet(agentId, selectedText);

      if (response.status === 200 && response.data?.success) {
        console.log('✅ Snippet updated in database:', agentId);
      } else {
        console.error('❌ Failed to update snippet in database');
        throw new Error('Failed to update snippet');
      }
    } catch (error) {
      console.error("❌ Failed to update snippet:", error);
      throw error;
    }
  },

  setActiveMiniAgent: async (id: string | null) => {
    set({ activeMiniAgentId: id });

    // Fetch mini agent from backend when opened
    if (id) {
      const state = get();
      const agent = state.miniAgents.find(a => a.id === id);

      if (!agent) {
        // Agent not in state, fetch from backend and add to state
        try {
          const response = await chatAPI.getMiniAgent(id);

          if (response.status === 200 && response.data) {
            const agentData = response.data;

            // Map messages from backend format
            const messages = (agentData.messages || []).map((msg: any) => ({
              id: msg.id || generateId(),
              role: msg.role || "user",
              content: msg.content || "",
              timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            }));

            const newAgent: MiniAgent = {
              id: agentData.agentId,
              messageId: agentData.messageId,
              sessionId: agentData.sessionId || state.currentChatId || undefined,
              selectedText: agentData.selectedText,
              messages,
              createdAt: agentData.createdAt ? new Date(agentData.createdAt) : new Date(),
            };

            set((state) => ({
              miniAgents: [...state.miniAgents, newAgent],
            }));
          }
        } catch (error) {
          console.error("❌ Failed to fetch mini-agent:", error);
        }
      } else if (agent.messages.length === 0) {
        // Agent exists but has no messages, fetch from backend
        await get().fetchMiniAgent(id);
      }
    }
  },

  loadSessionMiniAgents: async (sessionId: string, force: boolean = false) => {
    // Check cache
    const lastSyncTime = get().lastSynced[`${sessionId}_miniAgents`] || 0;
    if (!force && Date.now() - lastSyncTime < 60000) {
      return;
    }

    try {
      const response = await chatAPI.getSessionMiniAgents(sessionId);

      if (response.status === 200 && response.data?.miniAgents) {
        console.log('📥 Loading session mini-agents:', response.data.miniAgents?.length || 0);
        const fetched = response.data.miniAgents.map((agent: any) => {
          // ✅ Map messages first to determine hasConversation
          const messages = (agent.messages || []).map((msg: any) => ({
            id: msg.id || generateId(),
            role: msg.role || "user",
            content: msg.content || msg.text || "",
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          }));

          const mapped = {
            // ✅ FIX: Backend sends 'id', fallback to agentId for compatibility
            id: agent.agentId || agent.id || agent.agent_id,
            messageId: agent.messageId || agent.message_id,
            sessionId: sessionId,
            // ✅ FIX: Map selectedText from various possible field names
            selectedText: agent.selectedText || agent.selected_text || agent.snippet || "",
            messages,
            // ✅ FIX: Calculate hasConversation from messages if not provided
            hasConversation: agent.hasConversation || messages.length > 0,
            createdAt: agent.createdAt ? new Date(agent.createdAt) : new Date(),
          };
          console.log('📦 Mapped mini-agent:', mapped.id, 'messageId:', mapped.messageId, 'hasConversation:', mapped.hasConversation, 'messages:', messages.length);
          return mapped;
        });

        set((state) => {
          // Dedupe by id and prefer latest fetched for this session
          const map = new Map<string, MiniAgent>();
          // Keep existing agents from other sessions
          for (const a of state.miniAgents) {
            if (a.sessionId && a.sessionId !== sessionId) {
              map.set(a.id, a);
            }
          }
          // Add/replace fetched for current session
          for (const a of fetched) {
            map.set(a.id, a);
          }
          return {
            miniAgents: Array.from(map.values()),
            lastSynced: { ...state.lastSynced, [`${sessionId}_miniAgents`]: Date.now() }
          };
        });
      }
    } catch (error) {
      console.error("❌ Failed to load session mini-agents:", error);
    }
  },

  addHighlight: async (chatId: string, messageId: string, highlight: Omit<Highlight, "id">) => {
    // ⚡ OPTIMISTIC UPDATE: Instant UI feedback
    const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const optimisticHighlight: Highlight = {
      id: tempId,
      ...highlight,
    };

    // Get the message text for validation
    const state = get();
    const chat = state.chats.find((c) => c.id === chatId);
    const message = chat?.messages.find((m) => m.id === messageId);

    if (!message) {
      console.error('❌ Message not found:', messageId);
      return;
    }

    // Import validation utilities
    const { generateMessageHashSync, logHighlightDebug, cleanMessageContent, getRenderedText } = await import('@/lib/highlightUtils');

    // ✅ GET RENDERED TEXT (markdown stripped - matches what user sees/selects)
    // CRITICAL: Use the SAME content we're sending to backend (message.content)
    // Backend will: clean_message_content() → strip_markdown()
    // Frontend must match this exactly!
    const renderedContent = getRenderedText(message.content);

    // ✅ SMART POSITION FINDING
    // The DOM selection offsets may not exactly match getRenderedText() output
    // because the DOM and regex-based markdown stripping can differ slightly.
    // Strategy: Find the exact text in the rendered content near the given position.

    let finalStartIndex = highlight.startIndex;
    let finalEndIndex = highlight.endIndex;

    // First, check if the text matches at the exact position
    const textAtPosition = renderedContent.substring(finalStartIndex, finalEndIndex);

    if (textAtPosition !== highlight.text) {
      console.log(`⚠️ Text mismatch at original position [${finalStartIndex}:${finalEndIndex}]`);
      console.log(`   Expected: "${highlight.text}"`);
      console.log(`   Found: "${textAtPosition}"`);

      // Search for the exact text in a radius around the original position
      const searchRadius = 50; // Characters to search in each direction
      const searchStart = Math.max(0, finalStartIndex - searchRadius);
      const searchEnd = Math.min(renderedContent.length, finalEndIndex + searchRadius);
      const searchArea = renderedContent.substring(searchStart, searchEnd);

      const localIndex = searchArea.indexOf(highlight.text);

      if (localIndex !== -1) {
        // Found the text nearby - use corrected position
        finalStartIndex = searchStart + localIndex;
        finalEndIndex = finalStartIndex + highlight.text.length;
        console.log(`🔧 Auto-corrected to position [${finalStartIndex}:${finalEndIndex}]`);
      } else {
        // Try global search as last resort
        const globalIndex = renderedContent.indexOf(highlight.text);
        if (globalIndex !== -1) {
          // Check if this is reasonably close to the original position (within 100 chars)
          if (Math.abs(globalIndex - highlight.startIndex) < 100) {
            finalStartIndex = globalIndex;
            finalEndIndex = globalIndex + highlight.text.length;
            console.log(`🔧 Found text at global position [${finalStartIndex}:${finalEndIndex}]`);
          } else {
            console.error(`❌ Text found but too far from selection (at ${globalIndex}, expected near ${highlight.startIndex})`);
            console.error(`   This may highlight the wrong occurrence - aborting`);
            return;
          }
        } else {
          console.error(`❌ Cannot find text "${highlight.text}" in rendered content`);
          console.error(`   Content length: ${renderedContent.length}`);
          return;
        }
      }
    }

    // Final validation
    const verifyText = renderedContent.substring(finalStartIndex, finalEndIndex);
    if (verifyText !== highlight.text) {
      console.error(`❌ Final verification failed at [${finalStartIndex}:${finalEndIndex}]`);
      console.error(`   Expected: "${highlight.text}"`);
      console.error(`   Found: "${verifyText}"`);
      return;
    }

    console.log(`✅ Validated highlight: "${highlight.text}" at position [${finalStartIndex}:${finalEndIndex}]`);

    // Update the optimistic highlight with corrected indexes
    optimisticHighlight.startIndex = finalStartIndex;
    optimisticHighlight.endIndex = finalEndIndex;

    // Generate message hash using clean content for consistency
    const cleanContent = cleanMessageContent(message.content);
    const messageHash = generateMessageHashSync(cleanContent);

    // Debug log
    logHighlightDebug('CREATE', {
      messageId,
      startIndex: highlight.startIndex,
      endIndex: highlight.endIndex,
      text: highlight.text,
      hash: messageHash
    });

    // ✅ CLIENT-SIDE DUPLICATE DETECTION
    // Check if a highlight with the same range and text already exists
    const existingHighlights = message.highlights || [];
    const isDuplicate = existingHighlights.some(existing => {
      // Check for exact match
      if (existing.startIndex === finalStartIndex &&
        existing.endIndex === finalEndIndex &&
        existing.text.trim() === highlight.text.trim()) {
        return true;
      }

      // Check for overlapping highlights with same text
      const rangesOverlap = (
        finalStartIndex < existing.endIndex &&
        existing.startIndex < finalEndIndex
      );
      const textMatch = existing.text.trim() === highlight.text.trim();

      return rangesOverlap && textMatch;
    });

    if (isDuplicate) {
      console.log(`🔄 Duplicate highlight detected on client - skipping creation`);
      return; // Don't create duplicate
    }

    // 1. Update State Immediately (Optimistic)
    set((state) => ({
      chats: state.chats.map((chat) =>
        chat.id === chatId
          ? {
            ...chat,
            messages: chat.messages.map((msg) =>
              msg.id === messageId
                ? { ...msg, highlights: [...(msg.highlights || []), optimisticHighlight] }
                : msg
            ),
          }
          : chat
      ),
    }));

    try {
      const userId = useAuthStore.getState().user?.id || "anonymous";

      // 2. Network Request with Full Validation Data (use corrected indexes)
      const response = await chatAPI.createHighlight({
        userId,
        sessionId: chatId,
        messageId,
        text: highlight.text,
        color: highlight.color,
        startIndex: finalStartIndex,  // ✅ Use corrected index
        endIndex: finalEndIndex,      // ✅ Use corrected index
        note: highlight.note,
        messageText: message.content,   // ✅ CRITICAL: Send ORIGINAL content, backend will clean it
      });

      // 3. Reconcile / Confirm
      if ((response.status === 201 || response.status === 200) && (response.data?.highlight || response.data?.success)) {
        const payload = response.data;
        const realId = payload.highlight?.highlightId || payload.highlightId || tempId;

        if (!realId) {
          console.warn("⚠️ Created highlight but no ID returned", payload);
        }

        // Update the ID in the store
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === chatId
              ? {
                ...chat,
                messages: chat.messages.map((msg) =>
                  msg.id === messageId
                    ? {
                      ...msg,
                      highlights: (msg.highlights || []).map(h =>
                        h.id === tempId ? { ...h, id: realId } : h
                      )
                    }
                    : msg
                ),
              }
              : chat
          ),
        }));

        console.log('✅ Highlight created successfully:', realId);
        // Silent success - no notification
      } else if (response.data?.isExisting) {
        // Duplicate highlight - this is OK, just use existing
        console.log('ℹ️ Highlight already exists, using existing ID');
        const existingId = response.data.highlight?.highlightId || tempId;
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === chatId
              ? {
                ...chat,
                messages: chat.messages.map((msg) =>
                  msg.id === messageId
                    ? {
                      ...msg,
                      highlights: (msg.highlights || []).map(h =>
                        h.id === tempId ? { ...h, id: existingId } : h
                      )
                    }
                    : msg
                ),
              }
              : chat
          ),
        }));
      } else {
        // Log detailed error info
        console.error('❌ Backend returned error:', {
          status: response.status,
          data: response.data,
          detail: response.data?.detail
        });

        // Extract error message properly
        let errorMessage = "Failed to create highlight";
        if (response.data?.detail) {
          if (typeof response.data.detail === 'string') {
            errorMessage = response.data.detail;
          } else if (typeof response.data.detail === 'object') {
            errorMessage = response.data.detail.message || response.data.detail.error || JSON.stringify(response.data.detail);
          }
        } else if (response.data?.error) {
          errorMessage = response.data.error;
        } else if (response.data?.message) {
          errorMessage = response.data.message;
        }

        throw new Error(errorMessage);
      }
    } catch (error) {
      console.error("❌ Failed to create highlight, rolling back:", error);

      // Silent rollback - no notification, just console log
      // 4. Rollback on Error
      set((state) => ({
        chats: state.chats.map((chat) =>
          chat.id === chatId
            ? {
              ...chat,
              messages: chat.messages.map((msg) =>
                msg.id === messageId
                  ? {
                    ...msg,
                    highlights: (msg.highlights || []).filter(h => h.id !== tempId)
                  }
                  : msg
              ),
            }
            : chat
        ),
      }));
    }
  },

  removeHighlight: async (chatId: string, messageId: string, predicate: (h: Highlight) => boolean) => {
    try {
      const state = get();
      const chat = state.chats.find((c) => c.id === chatId);
      const message = chat?.messages.find((m) => m.id === messageId);
      const highlightToRemove = message?.highlights?.find(predicate);

      if (!highlightToRemove?.id) {
        console.warn("⚠️ No highlight found to remove");
        return;
      }

      // 1. Optimistic UI update - remove immediately for instant feedback
      const previousHighlights = message?.highlights || [];
      set((state) => ({
        chats: state.chats.map((chat) =>
          chat.id === chatId
            ? {
              ...chat,
              messages: chat.messages.map((msg) =>
                msg.id === messageId
                  ? { ...msg, highlights: (msg.highlights || []).filter((h) => !predicate(h)) }
                  : msg
              ),
            }
            : chat
        ),
      }));

      // 2. Backend delete
      try {
        await chatAPI.deleteHighlight(highlightToRemove.id);
        console.log("✅ Highlight deleted successfully");
      } catch (error) {
        console.error("❌ Failed to delete highlight from backend, rolling back:", error);

        // 3. Rollback on error - restore the highlight
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === chatId
              ? {
                ...chat,
                messages: chat.messages.map((msg) =>
                  msg.id === messageId
                    ? { ...msg, highlights: previousHighlights }
                    : msg
                ),
              }
              : chat
          ),
        }));

        // Show error toast
        toast({
          title: "Failed to delete highlight",
          description: "Could not remove the highlight. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("❌ Unexpected error in removeHighlight:", error);
    }
  },

  updateHighlightNote: async (chatId: string, messageId: string, highlightId: string, note: string) => {
    try {
      await chatAPI.updateHighlightNote(highlightId, note);

      // Update local state
      set((state) => ({
        chats: state.chats.map((chat) =>
          chat.id === chatId
            ? {
              ...chat,
              messages: chat.messages.map((msg) =>
                msg.id === messageId
                  ? {
                    ...msg,
                    highlights: (msg.highlights || []).map((h) =>
                      h.id === highlightId ? { ...h, note: note || undefined } : h
                    ),
                  }
                  : msg
              ),
            }
            : chat
        ),
      }));
    } catch (error) {
      console.error("❌ Failed to update highlight note:", error);
    }
  },

  /**
   * Update highlight color in place (smoother UX than delete+create)
   * Optimistic update with backend sync
   */
  updateHighlightColor: async (chatId: string, messageId: string, highlightId: string, color: string) => {
    try {
      // 1. Optimistic UI update - instant feedback
      set((state) => ({
        chats: state.chats.map((chat) =>
          chat.id === chatId
            ? {
              ...chat,
              messages: chat.messages.map((msg) =>
                msg.id === messageId
                  ? {
                    ...msg,
                    highlights: (msg.highlights || []).map((h) =>
                      h.id === highlightId ? { ...h, color } : h
                    ),
                  }
                  : msg
              ),
            }
            : chat
        ),
      }));

      // 2. Backend sync (if API exists)
      try {
        await chatAPI.updateHighlightColor(highlightId, color);
        console.log("✅ Highlight color updated:", highlightId);
      } catch (backendError) {
        console.warn("⚠️ Backend color update failed, keeping local state:", backendError);
        // Don't rollback - the highlight still works locally with new color
      }
    } catch (error) {
      console.error("❌ Failed to update highlight color:", error);
      throw error;
    }
  },



  toggleSidebar: () =>
    set((state) => ({
      sidebarExpanded: !state.sidebarExpanded,
    })),

  setActiveTab: (tab) => set({ activeTab: tab }),

  hydrateFromStorage: () => {
    // Load all chats from MongoDB (single source of truth)
    // No localStorage dependency - everything comes from backend
    get().loadChatsFromBackend();
  },

  // In-memory highlight ranges per chat
  addRangeHighlight: (chatId, msgId, start, end, colorHex) => {
    // This could be moved to the chat messages highlights array if needed
    // For now, this is a no-op since we're removing localStorage
  },
  removeRangeHighlight: (chatId, msgId, start, end) => {
    // No-op since we removed localStorage
  },
  getMessageRangeHighlights: (chatId, msgId) => {
    // Return empty array since we removed localStorage
    return [];
  },

  sendMessageStream: async (chatId, content, onToken, onComplete) => {
    try {
      await chatAPI.sendMessageStream(chatId, content, onToken, () => { }, () => { }, onComplete, (err) => console.error(err));
    } catch (error) {
      console.error("Stream error in store:", error);
    }
  },

  markActionExecuted: (chatId: string, messageId: string) => {
    set((state) => ({
      chats: state.chats.map((chat) => {
        if (chat.id === chatId) {
          return {
            ...chat,
            messages: chat.messages.map((msg) => {
              if (msg.id === messageId && msg.action?.payload) {
                return {
                  ...msg,
                  action: {
                    ...msg.action,
                    payload: {
                      ...msg.action.payload,
                      executeOnce: false,
                    },
                  },
                };
              }
              return msg;
            }),
          };
        }
        return chat;
      }),
    }));
  }
}));

