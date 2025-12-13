import { create } from "zustand";
import { Chat, Message, MiniAgent, MiniAgentMessage, Task, Highlight } from "@/types/chat";
import { chatAPI } from "@/lib/api";

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

  // Actions
  createChat: () => Promise<string>;
  setCurrentChat: (id: string) => void;
  addMessage: (chatId: string, message: Omit<Message, "id" | "timestamp">) => Promise<void>;
  deleteChat: (id:string) => Promise<void>;
  renameChat: (id: string, title: string) => Promise<void>;
  pinChat: (id: string, isPinned: boolean) => Promise<void>;
  saveChat: (id: string, isSaved: boolean) => Promise<void>;

  createTask: (title: string, chatId?: string) => string;
  toggleTask: (id: string) => void;
  deleteTask: (id: string) => void;
  
  createMiniAgent: (messageId: string, selectedText: string, userPrompt?: string) => Promise<string>;
  fetchMiniAgent: (agentId: string) => Promise<void>;
  addMiniAgentMessage: (agentId: string, content: string) => Promise<void>;
  deleteMiniAgent: (id: string) => Promise<void>;
  updateMiniAgentSnippet: (agentId: string, selectedText: string) => Promise<void>;
  setActiveMiniAgent: (id: string | null) => Promise<void>;
  loadSessionMiniAgents: (sessionId: string) => Promise<void>;
  
  addHighlight: (chatId: string, messageId: string, highlight: Omit<Highlight, "id">) => Promise<void>;
  removeHighlight: (chatId: string, messageId: string, predicate: (h: Highlight) => boolean) => Promise<void>;
  updateHighlightNote: (chatId: string, messageId: string, highlightId: string, note: string) => Promise<void>;
  loadSessionHighlights: (sessionId: string) => Promise<void>;
  
  toggleSidebar: () => void;
  setActiveTab: (tab: "history" | "tasks") => void;
  // Session helpers
  isSessionEmpty: () => boolean;
  createSessionIfNeeded: () => Promise<string>;
  startNewSession: () => Promise<string | null>;
  hydrateFromStorage: () => void;
  
  // Backend synchronization
  loadChatsFromBackend: () => Promise<void>;
  syncChatWithBackend: (chatId: string) => Promise<void>;

  // Local highlight ranges (hex colors) per chat
  addRangeHighlight: (chatId: string, msgId: string, start: number, end: number, colorHex: string) => void;
  removeRangeHighlight: (chatId: string, msgId: string, start: number, end: number) => void;
  getMessageRangeHighlights: (chatId: string, msgId: string) => Array<{ msgId: string; range: [number, number]; color: string }>; 
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

  // Load chats from backend - MongoDB is the single source of truth
  loadChatsFromBackend: async () => {
    set({ isLoadingChats: true });
    try {
      console.log('🔄 Loading chats from backend...');
      const response = await chatAPI.getUserChats();
      console.log('📥 Backend response:', response);
      
      if (response.status === 200 && response.data?.chats) {
        console.log(`✅ Loaded ${response.data.chats.length} chats from MongoDB`);
        // Map backend chats - use MongoDB data as source of truth
        const backendChats = response.data.chats.map((chat: any) => {
          // Handle date parsing - support ISO strings and Date objects
          let createdAt: Date;
          let updatedAt: Date;
          
          try {
            createdAt = chat.created_at instanceof Date 
              ? chat.created_at 
              : new Date(chat.created_at);
            
            updatedAt = chat.updated_at instanceof Date
              ? chat.updated_at
              : new Date(chat.updated_at || chat.created_at);
            
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
          id: chat.chat_id,
            title: chat.title || `Chat from ${createdAt.toLocaleDateString()}`,
            messages: [], // Will be loaded when session is opened
          miniAgents: [],
            createdAt,
            updatedAt,
            isPinned: chat.isPinned || false,  // From MongoDB - preserves rename
            isSaved: chat.isSaved || false,    // From MongoDB
            messageCount: chat.message_count || 0,  // Store message count from MongoDB
          };
        });
        
        // Remove duplicates by chat ID - MongoDB is source of truth
        const uniqueChats = backendChats.reduce((acc: Chat[], chat: Chat) => {
          if (!acc.find(c => c.id === chat.id)) {
            acc.push(chat);
          }
          return acc;
        }, []);
        
        // Replace all chats with backend data (no merging - MongoDB is source of truth)
        set({ chats: uniqueChats });
        console.log(`✅ Set ${uniqueChats.length} unique chats in state`);
        
        // Set current chat to most recent (no localStorage dependency)
        if (uniqueChats.length > 0) {
          // Sort by pinned first, then by updatedAt
          const sortedChats = [...uniqueChats].sort((a: Chat, b: Chat) => {
            if (a.isPinned && !b.isPinned) return -1;
            if (!a.isPinned && b.isPinned) return 1;
            return b.updatedAt.getTime() - a.updatedAt.getTime();
          });
          const mostRecentChat = sortedChats[0];
          console.log(`✅ Setting current chat to: ${mostRecentChat.id} (${mostRecentChat.title})`);
          set({ currentChatId: mostRecentChat.id });
          // Load messages for the current chat
          get().syncChatWithBackend(mostRecentChat.id);
        } else {
          console.log('ℹ️ No chats found in MongoDB');
        }
      } else {
        console.warn('⚠️ Invalid response from backend:', response);
      }
    } catch (error) {
      console.error('❌ Failed to load chats from backend:', error);
      // Set empty array on error to prevent stale data
      set({ chats: [], currentChatId: null });
    } finally {
      set({ isLoadingChats: false });
    }
  },

  // Sync specific chat with backend - fetches ALL conversation messages
  syncChatWithBackend: async (chatId: string) => {
    try {
      const response = await chatAPI.getChatHistory(chatId);
      if (response.status === 200 && response.data?.messages) {
        // Map messages - handle different formats
        // Backend stores: { id, role, content, timestamp }
        const messages = response.data.messages.map((msg: any) => ({
          id: msg.id || msg.message_id || generateId(),
          role: msg.role || "user", // Must be "user" or "assistant"
          content: msg.content || msg.text || msg.message || msg.response || "",
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          highlights: msg.highlights || [],
        }));

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
          title: response.data.title || "New Chat",
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
    // No localStorage - currentChatId is managed in state only
    // Always fetch full conversation when opening a session
    get().syncChatWithBackend(id);
    // Load mini-agents for this session
    get().loadSessionMiniAgents(id);
    // Load highlights for this session
    get().loadSessionHighlights(id);
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
              title:
                chat.messages.length === 0 && message.role === "user"
                  ? message.content.slice(0, 30) + (message.content.length > 30 ? "..." : "")
                  : chat.title,
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
            };
          }
          return chat;
        })
      }));

      // Stream AI response using streaming endpoint
      await chatAPI.sendMessageStream(
        chatId,
        message.content,
        // onChunk - update AI message content as chunks arrive
        (chunk: string) => {
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                const updatedMessages = chat.messages.map(m => 
                  m.id === aiTempId 
                    ? { ...m, content: m.content + chunk }
                    : m
                );
                return { ...chat, messages: updatedMessages };
              }
              return chat;
            }),
            isStreaming: true, // Set streaming to true on first chunk
            isSendingMessage: false // Stop showing "thinking" when streaming starts
          }));
        },
        // onComplete - finalize message with real ID from backend
        (messageId: string) => {
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
            isStreaming: false // Stop streaming indicator
          }));
        },
        // onError - handle streaming errors
        (error: string) => {
          console.error("Streaming error:", error);
          // Remove the AI message on error
          set(state => ({
            chats: state.chats.map(chat => {
              if (chat.id === chatId) {
                const updatedMessages = chat.messages.filter(m => m.id !== aiTempId);
                return { ...chat, messages: updatedMessages };
              }
              return chat;
            }),
            isSendingMessage: false,
            isStreaming: false
          }));
          throw new Error(error);
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

  createMiniAgent: async (messageId, selectedText, userPrompt?: string) => {
    try {
      const state = get();
      const currentChat = state.chats.find(c => c.id === state.currentChatId);
      
      if (!currentChat) {
        throw new Error("No active chat session");
      }
      
      console.log('🤖 Creating/Getting Mini Agent for message:', messageId);
      
      // Call backend - it will return existing agent or create new one
      const response = await chatAPI.createMiniAgent(
        messageId,
        currentChat.id,
        selectedText,
        userPrompt
      );
      
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
      
      set((state) => ({
        miniAgents: state.miniAgents.map((agent) =>
          agent.id === agentId
            ? { ...agent, messages: [...agent.messages, userMessage] }
            : agent
        ),
      }));
      
      // Call backend - this stores in database and generates AI response
      const response = await chatAPI.sendMiniAgentMessage(agentId, content);
      
      if (response.status === 200 && response.data) {
        console.log('✅ Mini Agent response received from database');
        
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
        
        // Update state with confirmed messages from database
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
        }));
        
        console.log('✅ Mini Agent messages updated in state and database');
      } else {
        // Error: Remove optimistic message and restore state
        console.error('❌ Failed to send message, removing optimistic update');
        set((state) => ({
          miniAgents: state.miniAgents.map((agent) =>
            agent.id === agentId
              ? { ...agent, messages: agent.messages.filter(m => m.id !== userMessage.id) }
              : agent
          ),
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

  loadSessionMiniAgents: async (sessionId: string) => {
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
        
        // Replace mini-agents for this session
        set({ miniAgents });
      }
    } catch (error) {
      console.error("❌ Failed to load session mini-agents:", error);
    }
  },

  addHighlight: async (chatId: string, messageId: string, highlight: Omit<Highlight, "id">) => {
    try {
      const response = await chatAPI.createHighlight(
        chatId,
        messageId,
        highlight.text,
        highlight.color,
        highlight.startOffset,
        highlight.endOffset,
        highlight.note
      );

      if (response.status === 201 && response.data?.highlight) {
        const newHighlight: Highlight = {
          id: response.data.highlightId,
          text: response.data.highlight.text,
          color: response.data.highlight.color, // Use actual HEX color from response
          startOffset: response.data.highlight.startIndex,
          endOffset: response.data.highlight.endIndex,
          note: response.data.highlight.note || undefined,
        };

        // Update local state
        set((state) => ({
          chats: state.chats.map((chat) =>
            chat.id === chatId
              ? {
                  ...chat,
                  messages: chat.messages.map((msg) =>
                    msg.id === messageId
                      ? { ...msg, highlights: [...(msg.highlights || []), newHighlight] }
                      : msg
                  ),
                }
              : chat
          ),
        }));
      }
    } catch (error) {
      console.error("❌ Failed to create highlight:", error);
    }
  },

  removeHighlight: async (chatId: string, messageId: string, predicate: (h: Highlight) => boolean) => {
    try {
      const state = get();
      const chat = state.chats.find((c) => c.id === chatId);
      const message = chat?.messages.find((m) => m.id === messageId);
      const highlightToRemove = message?.highlights?.find(predicate);

      if (highlightToRemove?.id) {
        await chatAPI.deleteHighlight(highlightToRemove.id);

        // Update local state
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
      }
    } catch (error) {
      console.error("❌ Failed to remove highlight:", error);
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

  loadSessionHighlights: async (sessionId: string) => {
    try {
      // Check if highlights already loaded for this session
      const existingChat = get().chats.find(c => c.id === sessionId);
      if (existingChat && existingChat.messages.some(m => m.highlights && m.highlights.length > 0)) {
        console.log('⚡ Highlights already loaded for session, skipping fetch');
        return;
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
            id: h.highlightId,
            text: h.text,
            color: h.color as "yellow" | "green" | "blue" | "pink",
            startOffset: h.startIndex,
            endOffset: h.endIndex,
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
        }));
        
        console.log(`✅ Loaded ${highlights.length} highlights for session ${sessionId}`);
      }
    } catch (error) {
      console.error("❌ Failed to load highlights:", error);
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
}));
