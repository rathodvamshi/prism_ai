import axios from 'axios';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for consistent error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Return a consistent error object instead of throwing
        if (error.response) {
            return {
                error: error.response.data.detail || error.response.data.message || 'An error occurred',
                status: error.response.status,
                data: null
            };
        }
        return {
            error: error.message || 'Network error',
            status: 500,
            data: null
        };
    }
);

const handleRequest = async (request: Promise<any>) => {
    try {
        const response = await request;
        // If the interceptor caught an error, it returns { error, status, data }
        if (response.error) return response;

        return {
            data: response.data,
            status: response.status,
            error: null
        };
    } catch (error: any) {
        return {
            data: null,
            status: 500,
            error: error.message || 'Unexpected error'
        };
    }
};

export const authAPI = {
    // Using cookie-based session login to be compatible with get_current_user_from_session
    login: (data: any) => handleRequest(api.post('/auth/login', data)),
    signup: (data: any) => handleRequest(api.post('/auth/signup', data)),
    verifyOTP: (data: any) => handleRequest(api.post('/auth/verify-otp', data)),
    forgotPassword: (email: string) => handleRequest(api.post('/auth/forgot-password', { email })),
    logout: () => handleRequest(api.post('/auth/logout')),
    me: () => handleRequest(api.get('/auth/me')),
};

export const chatAPI = {
    getUserChats: (limit: number = 20, skip: number = 0) => handleRequest(api.get('/chat/chats', { params: { limit, skip } })),
    getChatHistory: (chatId: string) => handleRequest(api.get(`/chat/${chatId}/history`)),
    loadSessionData: (sessionId: string) => handleRequest(api.get(`/chat/${sessionId}/data`)),
    createNewChat: () => handleRequest(api.post('/chat/new', {})),
    deleteChat: (id: string) => handleRequest(api.delete(`/chat/${id}`)),
    renameChat: (id: string, title: string) => handleRequest(api.put(`/chat/${id}/rename`, { title })),
    pinChat: (id: string, isPinned: boolean) => handleRequest(api.put(`/chat/${id}/pin`, { isPinned })),
    saveChat: (id: string, isSaved: boolean) => handleRequest(api.put(`/chat/${id}/save`, { isSaved })),

    // Task API
    getTasks: (status?: string) => handleRequest(api.get('/tasks', { params: { status } })),
    confirmTask: (data: any) => handleRequest(api.post('/tasks/confirm', data)),
    updateTask: (data: any) => handleRequest(api.post('/tasks/update', data)),
    cancelTask: (data: any) => handleRequest(api.post('/tasks/cancel', data)),

    // Mini Agent API
    createMiniAgent: (data: any) => handleRequest(api.post('/api/mini-agents', data)),
    getMiniAgent: (agentId: string) => handleRequest(api.get(`/api/mini-agents/thread/${agentId}`)), // Assuming a specific endpoint or we'll add it
    sendMiniAgentMessage: (agentId: string, content: string) => handleRequest(api.post(`/api/mini-agents/${agentId}/messages`, { text: content })),
    deleteMiniAgent: (agentId: string) => handleRequest(api.delete(`/api/mini-agents/${agentId}`)),
    updateMiniAgentSnippet: (agentId: string, selectedText: string) => handleRequest(api.put(`/api/mini-agents/${agentId}/snippet`, { selectedText })),
    getSessionMiniAgents: (sessionId: string) => handleRequest(api.get(`/api/mini-agents/${sessionId}`)),

    // Highlights API
    createHighlight: (data: any) => handleRequest(api.post('/api/highlights', data)),
    deleteHighlight: (highlightId: string) => handleRequest(api.delete(`/api/highlights/${highlightId}`)),
    updateHighlightNote: (highlightId: string, note: string) => handleRequest(api.put(`/api/highlights/${highlightId}/note`, { note })),
    getSessionHighlights: (sessionId: string) => handleRequest(api.get(`/api/highlights/${sessionId}`)),

    sendMessageStream: async (
        chatId: string,
        content: string,
        onChunk: (chunk: string) => void,
        onComplete: (msgId: string) => void,
        onError: (err: string) => void,
        onAction?: (action: any) => void,
        onStatus?: (status: string) => void,
        onTitle?: (title: string) => void
    ) => {
        try {
            const response = await fetch(`${API_URL}/chat/message/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include', // Critical for cookie-based auth
                body: JSON.stringify({ chatId, message: content }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error('No reader available');

            let buffer = '';
            let currentEvent = 'message'; // Default event type
            let messageId = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Process all complete lines
                buffer = lines.pop() || ''; // Keep the last incomplete line in buffer

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine) continue; // Skip empty lines

                    if (trimmedLine.startsWith('event: ')) {
                        currentEvent = trimmedLine.slice(7).trim();
                    } else if (trimmedLine.startsWith('data: ')) {
                        const data = trimmedLine.slice(6);

                        try {
                            if (currentEvent === 'start') {
                                const parsed = JSON.parse(data);
                                if (parsed.message_id) {
                                    messageId = parsed.message_id;
                                }
                            } else if (currentEvent === 'token') {
                                // Token event usually contains raw text
                                onChunk(data);
                            } else if (currentEvent === 'action') {
                                if (onAction) {
                                    onAction(JSON.parse(data));
                                }
                            } else if (currentEvent === 'status') {
                                if (onStatus) {
                                    const statusData = JSON.parse(data);
                                    onStatus(statusData.message || statusData.step);
                                }
                            } else if (currentEvent === 'title') {
                                if (onTitle) {
                                    const parsed = JSON.parse(data);
                                    onTitle(parsed.title);
                                }
                            } else if (currentEvent === 'done') {
                                // Stream finished
                            } else {
                                // Default/Fallback
                                try {
                                    const parsed = JSON.parse(data);
                                    // Handle generic JSON if needed
                                } catch {
                                    onChunk(data);
                                }
                            }
                        } catch (e) {
                            console.warn('Error parsing SSE data:', e);
                            // Fallback: if it's a token event but failed JSON parse, just send it
                            if (currentEvent === 'token') {
                                onChunk(data);
                            }
                        }
                    }
                }
            }

            // Call onComplete with the captured messageId
            onComplete(messageId || 'msg-' + Date.now());

        } catch (error: any) {
            onError(error.message);
        }
    }
};

export const userAPI = {
    getProfile: () => handleRequest(api.get('/users/profile')),
    updateProfile: (data: any) => handleRequest(api.put('/users/profile', data)),
    getStats: () => handleRequest(api.get('/users/stats')),
    deleteAccount: (confirmation: string) => handleRequest(api.delete('/users/account', { data: { confirm_delete: confirmation } })),
    clearMemories: (confirmation: string) => handleRequest(api.delete('/users/memory', { data: { confirm_clear: confirmation } })),
    getMemoryStats: () => handleRequest(api.get('/users/memory/stats')),
};

export const healthAPI = {
    check: () => handleRequest(api.get('/health')),
};
