import { create } from "zustand";
import { Chat, Message, MiniAgent, MiniAgentMessage, Task, Highlight } from "@/types/chat";
import { chatAPI } from "@/lib/api";
import { useAuthStore } from "./authStore";
import { toast } from "@/hooks/use-toast";

interface ChatState {
  chats: Chat[];
  currentChatId: string | null;
  tasks: Task[];
  miniAgents: MiniAgent[];
  activeMiniAgentId: string | null;
  sidebarExpanded: boolean;
  activeTab: "history" | "tasks";
  isLoadingChats: boolean;
  isSendingMessage: boolean;
  isStreaming: boolean;
  lastSynced: Record<string, number>; // Map of chatId/sessionId -> timestamp
  hasMore: boolean; // For pagination

  // Actions
  createChat: () => Promise<string>;
  setCurrentChat: (id: string) => void;
  addMessage: (chatId: string, message: Omit<Message, "id" | "timestamp">) => Promise<void>;
  deleteChat: (id: string) => Promise<void>;
  renameChat: (id: string, title: string) => Promise<void>;
  pinChat: (id: string, isPinned: boolean) => Promise<void>;
  saveChat: (id: string, isSaved: boolean) => Promise<void>;

  createTask: (title: string, chatId?: string) => string;
  toggleTask: (id: string) => void;
  deleteTask: (id: string) => void;
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
  loadSessionHighlights: (sessionId: string, force?: boolean) => Promise<void>;

  toggleSidebar: () => void;
  setActiveTab: (tab: "history" | "tasks") => void;
  // Session helpers
  isSessionEmpty: () => boolean;
  createSessionIfNeeded: () => Promise<string>;
  startNewSession: () => Promise<string | null>;
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
}

const generateId = () => Math.random().toString(36).substring(2, 15);

export const useChatStore = create<ChatState>((set, get) => ({
  chats: [],
  currentChatId: null,
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

          // Set current chat to most recent if none selected (and we didn't just preserve one)
          if (mergedChats.length > 0 && !get().currentChatId) {
            // Sort by pinned first, then by updatedAt
            const sortedChats = [...mergedChats].sort((a: Chat, b: Chat) => {
              if (a.isPinned && !b.isPinned) return -1;
              if (!a.isPinned && b.isPinned) return 1;
              return b.updatedAt.getTime() - a.updatedAt.getTime();
            });
            const mostRecentChat = sortedChats[0];
            set({ currentChatId: mostRecentChat.id });
          }
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
    // Check if synced recently (within 60s) unless forced
    const lastSyncTime = get().lastSynced[chatId] || 0;
    if (!force && Date.now() - lastSyncTime < 60000) {
      // console.log(`Stats for ${chatId} are fresh, skipping sync.`);
      return;
    }

    try {
      const response = await chatAPI.getChatHistory(chatId);
      if (response.status === 200 && response.data?.messages) {
        // Map messages with proper highlight field mapping AND action payload
        const messages = response.data.messages.map((msg: any) => {
          // Map highlights with correct field names
          const highlights = (msg.highlights || []).map((h: any) => ({
            id: h.id || h.highlightId || h.highlight_id || generateId(),
            text: h.text || h.highlightedText || '',
            color: h.color || '#FFD93D',
            // CRITICAL: Backend uses startIndex/endIndex, frontend uses startOffset/endOffset
            startOffset: h.startOffset ?? h.startIndex ?? h.start_index ?? 0,
            endOffset: h.endOffset ?? h.endIndex ?? h.end_index ?? 0,
            note: h.note || '',
            createdAt: h.createdAt ? new Date(h.createdAt) : new Date(),
          }));

          // Extract action payload from metadata (restored from MongoDB)
          const actionPayload = msg.metadata?.action_payload || msg.action;

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
      const response = await chatAPI.loadSessionData(sessionId);

      if (response.status === 200 && response.data) {
        const { session, messages, highlights, miniAgents } = response.data;

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

        // Map messages with highlights attached AND action payload
        const mappedMessages = (messages || []).map((msg: any) => {
          const messageHighlights = (highlightsByMessageId.get(msg.id) || []).map((h: any) => ({
            id: h.highlightId || h.id || h.highlight_id || generateId(),
            text: h.text || h.highlightedText || '',
            color: h.color || '#FFD93D',
            startOffset: h.startOffset ?? h.startIndex ?? h.start_index ?? 0,
            endOffset: h.endOffset ?? h.endIndex ?? h.end_index ?? 0,
            note: h.note || '',
            createdAt: h.createdAt ? new Date(h.createdAt) : new Date(),
          }));

          // Extract action payload from metadata (restored from MongoDB)
          const actionPayload = msg.metadata?.action_payload || msg.action;

          return {
            id: msg.id || msg.message_id || generateId(),
            role: msg.role || "user",
            content: msg.content || msg.text || "",
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            highlights: messageHighlights,
            action: actionPayload, // ✅ Restore confirmation state from database
          };
        });

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

          return {
            id: agent.agentId || agent.id || agent.agent_id || generateId(),
            messageId: agent.messageId || agent.message_id || '',
            sessionId: agent.sessionId || agent.session_id || sessionId,
            title: agent.title || "Mini Agent",
            snippet: agent.snippet || agent.selectedText || agent.selected_text || "",
            messages: agentMessages,
            createdAt: agent.createdAt ? new Date(agent.createdAt) : new Date(),
            hasConversation: agentMessages.length > 0,
          };
        });

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
          }));
          console.log(`✅ Added new chat to state`);
        }
      } else {
        set({ isLoadingChats: false });
        throw new Error(response.error || 'Failed to load session data');
      }
    } catch (error) {
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
  createSessionIfNeeded: async () => {
    const state = get();
    const current = state.chats.find((c) => c.id === state.currentChatId);
    if (!current || current.messages.length > 0) {
      return await get().createChat();
    }
    return current.id;
  },

  // Starts a fresh session only if the current one has messages
  startNewSession: async () => {
    const state = get();
    const current = state.chats.find((c) => c.id === state.currentChatId);
    if (!current || current.messages.length > 0) {
      return await get().createChat();
    }
    // If current chat exists and is empty, just reuse it
    return current.id;
  },

  setCurrentChat: (id) => {
    set({ currentChatId: id, activeMiniAgentId: null });

    // 🚀 PERFORMANCE: Use parallel fetching or single batch endpoint
    // We prefer loadSessionData which fetches everything in one round trip
    get().loadSessionData(id).catch(err => {
      console.warn("Fast load failed, falling back to granular fetch", err);
      // Fallback to parallel granular fetches if batch fails
      Promise.all([
        get().syncChatWithBackend(id),
        get().loadSessionMiniAgents(id),
        get().loadSessionHighlights(id)
      ]);
    });
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
          return {
            ...chat,
            messages: updatedMessages,
            messageCount: updatedMessages.length, // Update message count
            updatedAt: new Date(),
            title: chat.title,
          };
        }
        // Don't modify other chats
        return chat;
      });
      return { chats, isSendingMessage: true };
    });

    try {
      // Create a temporary AI message for streaming
      const aiTempId = generateId();
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
              // ⚡ VISUAL TRICK: clear title to trigger "thinking" cursor animation
              title: (chat.messages.length === 0 && ["New Chat", "Untitled"].includes(chat.title)) ? "" : chat.title,
            };
          }
          return chat;
        }),
        isSendingMessage: true,
        isStreaming: false
      }));

      // GPT-Style streaming: Append chunks using RAF for 60fps smoothness
      let rafId: number | null = null;
      let pendingChunk = '';
      let isFirstChunk = true;

      const scheduleUpdate = () => {
        if (rafId) return; // Already scheduled

        rafId = requestAnimationFrame(() => {
          rafId = null;

          if (pendingChunk) {
            const chunk = pendingChunk;
            pendingChunk = '';

            // CRITICAL: Append-only update (GPT-style)
            set(state => ({
              chats: state.chats.map(chat => {
                if (chat.id === chatId) {
                  const updatedMessages = chat.messages.map(m =>
                    m.id === aiTempId
                      ? { ...m, content: m.content + chunk } // APPEND ONLY
                      : m
                  );
                  return { ...chat, messages: updatedMessages };
                }
                return chat;
              }),
              isStreaming: true,
              isSendingMessage: false
            }));
          }
        });
      };

      // Stream AI response using streaming endpoint
      await chatAPI.sendMessageStream(
        chatId,
        message.content,
        // onChunk - GPT-style append-only streaming
        (chunk: string) => {
          // First chunk - immediately switch from thinking to streaming
          if (isFirstChunk) {
            isFirstChunk = false;
            set(state => ({
              ...state,
              isStreaming: true,
              isSendingMessage: false
            }));
          }

          // Accumulate chunk and schedule RAF update
          pendingChunk += chunk;
          scheduleUpdate();
        },
        // onComplete - finalize message with real ID from backend
        (messageId: string) => {
          // Cancel any pending RAF
          if (rafId) {
            cancelAnimationFrame(rafId);
            rafId = null;
          }

          // Flush any remaining content immediately
          if (pendingChunk) {
            const finalChunk = pendingChunk;
            pendingChunk = '';

            set(state => ({
              chats: state.chats.map(chat => {
                if (chat.id === chatId) {
                  const updatedMessages = chat.messages.map(m =>
                    m.id === aiTempId
                      ? { ...m, id: messageId, content: m.content + finalChunk }
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
                      ? { ...m, id: messageId }
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

  createTask: (title, chatId) => {
    const task: Task = {
      id: generateId(),
      title,
      completed: false,
      createdAt: new Date(),
      chatId,
    };
    set((state) => ({ tasks: [task, ...state.tasks] }));
    return task.id;
  },

  toggleTask: (id) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === id ? { ...task, completed: !task.completed } : task
      ),
    })),

  deleteTask: (id) =>
    set((state) => ({ tasks: state.tasks.filter((task) => task.id !== id) })),

  loadTasksFromBackend: async () => {
    try {
      const [pending, completed] = await Promise.all([
        chatAPI.getTasks("pending"),
        chatAPI.getTasks("completed"),
      ]);

      const mapTasks = (resp: any, completedFlag: boolean): Task[] => {
        if (resp.status !== 200 || !Array.isArray(resp.data)) return [];
        return resp.data.map((t: any) => {
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

      const resp = await chatAPI.confirmTask({
        description,
        due_date: formattedDueDate
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

        // Map messages from backend format
        const messages = (agentData.messages || []).map((msg: any) => ({
          id: msg.id || generateId(),
          role: msg.role || "user",
          content: msg.content || "",
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        }));

        const agent: MiniAgent = {
          id: agentData.agentId,
          messageId: agentData.messageId,
          selectedText: agentData.selectedText,
          messages,
          createdAt: agentData.createdAt ? new Date(agentData.createdAt) : new Date(),
          hasConversation: agentData.hasConversation || false,
        };

        // Check if agent already exists in state
        const existingAgentIndex = state.miniAgents.findIndex(a => a.id === agent.id);

        if (existingAgentIndex !== -1) {
          // Update existing agent (snippet may have changed)
          set((state) => ({
            miniAgents: state.miniAgents.map(a => a.id === agent.id ? agent : a),
            activeMiniAgentId: agent.id,
            chats: [...state.chats], // Trigger re-render
          }));
          console.log('📝 Updated existing Mini Agent with new snippet:', agent.id);
        } else {
          // Add new agent to state
          set((state) => ({
            miniAgents: [...state.miniAgents, agent],
            activeMiniAgentId: agent.id,
            chats: [...state.chats], // Trigger re-render
          }));
          console.log('✅ Mini Agent added to state:', agent.id);
        }

        return agent.id;
      } else {
        console.error('❌ Invalid response:', response);
        throw new Error("Failed to create mini-agent");
      }
    } catch (error) {
      console.error("❌ Failed to create mini-agent:", error);
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
        const miniAgents = response.data.miniAgents.map((agent: any) => ({
          id: agent.agentId,
          messageId: agent.messageId,
          selectedText: agent.selectedText,
          messages: (agent.messages || []).map((msg: any) => ({
            id: msg.id || generateId(),
            role: msg.role || "user",
            content: msg.content || "",
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          })),
          hasConversation: agent.hasConversation || false,
          createdAt: agent.createdAt ? new Date(agent.createdAt) : new Date(),
        }));

        set((state) => {
          // Merge with existing agents for other sessions
          const otherAgents = state.miniAgents.filter(a => a.sessionId !== sessionId);
          return {
            miniAgents: [...otherAgents, ...miniAgents],
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

    // 1. Update State Immediately
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

      // 2. Network Request in Background
      const response = await chatAPI.createHighlight({
        userId,
        sessionId: chatId,
        messageId,
        text: highlight.text,
        color: highlight.color,
        startIndex: highlight.startOffset,
        endIndex: highlight.endOffset,
        note: highlight.note
      });

      // 3. Reconcile / Confirm
      console.log('Highlight creation response:', response); // Debug log

      if ((response.status === 201 || response.status === 200) && (response.data?.highlight || response.data?.success)) {
        const payload = response.data;
        const realId = payload.highlightId || (payload.highlight ? payload.highlight.id : null) || (payload._id) || tempId;

        if (!realId && !payload.highlight) {
          console.warn("⚠️ Created highlight but no ID returned", payload);
          // Verify if we can fallback to tempId if success is true? 
          // Ideally we need the real ID. 
        }

        // Silently update the ID in the store so future deletes work
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
      } else {
        console.error('Invalid backend response structure:', response);
        throw new Error("Invalid backend response");
      }
    } catch (error) {
      console.error("❌ Failed to create highlight, rolling back:", error);

      // Notify user
      toast({
        title: "Failed to save highlight",
        description: "Your highlight could not be saved. Please check your connection.",
        variant: "destructive",
      });

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

  loadSessionHighlights: async (sessionId: string, force: boolean = false) => {
    // Check cache
    const lastSyncTime = get().lastSynced[`${sessionId}_highlights`] || 0;
    if (!force && Date.now() - lastSyncTime < 60000) {
      return;
    }

    try {
      // Check if highlights already loaded for this session (legacy check retained as secondary optimization)
      if (!force) {
        const existingChat = get().chats.find(c => c.id === sessionId);
        if (existingChat && existingChat.messages.some(m => m.highlights && m.highlights.length > 0)) {
          // Also set synced flag to prevent future checks for a while
          set(state => ({
            lastSynced: { ...state.lastSynced, [`${sessionId}_highlights`]: Date.now() }
          }));
          return;
        }
      }

      const response = await chatAPI.getSessionHighlights(sessionId);

      if (response.status === 200 && response.data?.highlights) {
        const highlights = response.data.highlights;

        // Group highlights by message ID (optimized with Map for O(1) lookups)
        const highlightsByMessage = new Map<string, Highlight[]>();
        highlights.forEach((h: any) => {
          if (!highlightsByMessage.has(h.messageId)) {
            highlightsByMessage.set(h.messageId, []);
          }
          highlightsByMessage.get(h.messageId)!.push({
            id: h.highlightId || h.id,
            text: h.text || '',
            color: h.color || '#FFD93D',
            // CRITICAL: Backend uses startIndex/endIndex, frontend uses startOffset/endOffset
            startOffset: h.startOffset ?? h.startIndex ?? 0,
            endOffset: h.endOffset ?? h.endIndex ?? 0,
            note: h.note || undefined,
          });
        });

        // Update messages with highlights (batch update for performance)
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === sessionId
              ? {
                ...chat,
                messages: chat.messages.map((msg) => ({
                  ...msg,
                  highlights: highlightsByMessage.get(msg.id) || [],
                })),
              }
              : chat
          ),
          lastSynced: { ...state.lastSynced, [`${sessionId}_highlights`]: Date.now() }
        }));
      }
    } catch (error) {
      console.error("Failed to load highlights:", error);
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
  }
}));
