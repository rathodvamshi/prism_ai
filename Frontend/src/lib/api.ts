import axios from 'axios';
import { createMetadataFilter } from './streamUtils';

export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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
            const detail = error.response.data?.detail;
            // Handle nested error object: { detail: { error: "CODE", message: "..." } }
            const errorMessage = typeof detail === 'object'
                ? detail.message || detail.error || 'An error occurred'
                : detail || error.response.data?.message || 'An error occurred';
            return {
                error: errorMessage,
                status: error.response.status,
                data: error.response.data
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
    updateHighlightNote: (highlightId: string, note: string) => handleRequest(api.patch(`/chat/highlights/${highlightId}/note`, { note })),
    updateHighlightColor: (highlightId: string, color: string) => handleRequest(api.patch(`/api/highlights/${highlightId}/color`, { color })),


    resumeMessageStream: async (
        chatId: string,
        generationId: string,
        onChunk: (chunk: string) => void,
        onComplete: (msgId: string) => void,
        onError: (err: string) => void
    ) => {
        const RETRY_DELAY = 1000;
        const MAX_RETRIES = 3;

        try {
            // 1. Resume Stream directly (Skip Generate)
            console.log(`🔄 Resuming stream for generation ${generationId}`);
            const response = await fetch(`${API_URL}/api/streaming/chat/${chatId}/stream/${generationId}`, {
                method: 'GET',
                headers: {
                    'Accept': 'text/event-stream',
                },
                credentials: 'include',
            });

            if (!response.ok) {
                // If 404, it might be already finalized/cleaned.
                if (response.status === 404) {
                    console.log("Generation not found during resume, checking finalization...");
                    // Try to finalize to check if it's done
                    const finRes = await fetch(`${API_URL}/api/streaming/chat/${chatId}/finalize/${generationId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ final_content: "" }), // Content might be missing if we reconnect late, but backend handles this
                    });
                    if (finRes.ok) {
                        const finData = await finRes.json();
                        onComplete(finData.message_id || finData.generation_id);
                        return;
                    }
                }
                throw new Error(`Resume stream error: ${response.status}`);
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            if (!reader) throw new Error('No reader available');

            let buffer = '';
            let currentEvent = 'message';
            let accumulatedContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine) continue;

                    if (trimmedLine.startsWith('event: ')) {
                        currentEvent = trimmedLine.slice(7).trim();
                    } else if (trimmedLine.startsWith('data: ')) {
                        const data = trimmedLine.slice(6);
                        try {
                            if (currentEvent === 'chunk') {
                                const parsed = JSON.parse(data);
                                if (parsed.content) {
                                    onChunk(parsed.content);
                                    accumulatedContent += parsed.content;
                                }
                            } else if (currentEvent === 'error') {
                                const parsed = JSON.parse(data);
                                throw new Error(parsed.error || "Stream error");
                            } else if (currentEvent === 'cancelled') {
                                return;
                            } else if (currentEvent === 'done' || currentEvent === 'completed') {
                                // Stream complete
                            }
                        } catch (e: any) {
                        }
                    }
                }
            }

            // 2. Finalize (Idempotent)
            // Even if we missed chunks, we call finalize to ensure DB is consistent
            // If we don't have full content, backend might rely on its own state or we accept partial loss for now
            // But since finalize is idempotent, it's safe.
            try {
                const finRes = await fetch(`${API_URL}/api/streaming/chat/${chatId}/finalize/${generationId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        final_content: accumulatedContent || undefined,
                        metadata: {}
                    }),
                });

                if (finRes.ok) {
                    const finData = await finRes.json();
                    onComplete(finData.message_id || finData.generation_id);
                } else {
                    onComplete('restored-' + generationId);
                }
            } catch (e) {
                onComplete('restored-' + generationId);
            }

        } catch (error: any) {
            console.error("Resume failed:", error);
            onError(error.message);
        }
    },

    checkActiveGeneration: (chatId: string) => handleRequest(api.get(`/api/streaming/chat/${chatId}/active`)),

    sendMessageStream: async (
        chatId: string,
        content: string,
        onChunk: (chunk: string) => void,
        onComplete: (msgId: string, metadata?: { key_source?: string; model?: string; usage?: any }) => void,
        onError: (err: string) => void,
        onAction?: (action: any) => void,
        onStatus?: (status: string) => void,
        onTitle?: (title: string) => void,
        onStart?: (messageId: string) => void
    ) => {
        const MAX_RETRIES = 2;
        const RETRY_DELAY = 1000; // 1 second

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                // 1. Create Generation Job
                const genRes = await fetch(`${API_URL}/api/streaming/chat/${chatId}/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ prompt: content, temperature: 0.7 }),
                });

                if (!genRes.ok) {
                    // Handle 409 Conflict - generation in progress
                    if (genRes.status === 409) {
                        const errorData = await genRes.json().catch(() => ({}));
                        const errorMsg = errorData.detail?.message || errorData.detail ||
                            "A generation is already in progress. Please wait.";

                        // For 409, try to get active generation and wait a bit before retrying
                        if (attempt < MAX_RETRIES) {
                            // Check if there's an active generation we can wait for
                            try {
                                const activeRes = await fetch(`${API_URL}/api/streaming/chat/${chatId}/active`, {
                                    method: 'GET',
                                    credentials: 'include',
                                });

                                if (activeRes.ok) {
                                    const activeData = await activeRes.json();
                                    if (activeData.active_generation) {
                                        // Wait a bit longer and retry
                                        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * 2 * (attempt + 1)));
                                        continue;
                                    }
                                }
                            } catch (e) {
                                // Ignore errors checking active generation
                            }
                        }

                        // Don't retry on 409 if we've exhausted retries
                        throw new Error(errorMsg);
                    }

                    // Handle 402 - Free limit exceeded
                    if (genRes.status === 402) {
                        const errorData = await genRes.json().catch(() => ({}));
                        const errorCode = errorData.detail?.error || "FREE_LIMIT_EXCEEDED";
                        const errorMsg = errorData.detail?.message ||
                            "You've used all your free AI requests. Please add your own API key to continue.";

                        // Throw special error that the UI can recognize
                        const error = new Error(errorMsg);
                        (error as any).code = errorCode;
                        throw error;
                    }

                    // For other errors, retry if we have attempts left
                    if (attempt < MAX_RETRIES && genRes.status >= 500) {
                        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)));
                        continue;
                    }

                    const errorText = await genRes.text().catch(() => `HTTP ${genRes.status}`);
                    throw new Error(`Failed to start generation: ${errorText}`);
                }

                const { generation_id } = await genRes.json();

                // 2. Stream Response
                const response = await fetch(`${API_URL}/api/streaming/chat/${chatId}/stream/${generation_id}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'text/event-stream',
                    },
                    credentials: 'include',
                });

                if (!response.ok) {
                    if (attempt < MAX_RETRIES && response.status >= 500) {
                        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)));
                        continue;
                    }
                    throw new Error(`Stream error: ${response.status}`);
                }

                const reader = response.body?.getReader();
                const decoder = new TextDecoder();
                if (!reader) throw new Error('No reader available');

                let buffer = '';
                let currentEvent = 'message';
                let accumulatedContent = '';
                let actionBuffer = ''; // Buffer for partial ACTION tags

                // 🛡️ Metadata filter (uses shared utility)
                const filterMetadata = createMetadataFilter();

                // 🎬 ACTION tag extractor (extracts MEDIA_PLAY before filtering)
                const extractActions = (text: string): string => {
                    // Buffer partial ACTION tags across chunks
                    const combined = actionBuffer + text;
                    actionBuffer = '';

                    // Extract complete ACTION:MEDIA_PLAY tags
                    const actionRegex = /<!--ACTION:MEDIA_PLAY:(.*?)-->/g;
                    let match;
                    while ((match = actionRegex.exec(combined)) !== null) {
                        try {
                            const payload = JSON.parse(match[1]);
                            console.log('🎬 Extracted MEDIA_PLAY action:', payload);
                            if (onAction) {
                                onAction({ type: 'media_play', payload });
                            }
                        } catch (e) {
                            console.error('❌ Failed to parse MEDIA_PLAY action:', e);
                        }
                    }

                    // Check for partial ACTION tag at end
                    const partialMatch = combined.match(/<!--ACTION:[^>]*$/);
                    if (partialMatch) {
                        actionBuffer = partialMatch[0];
                        return combined.slice(0, -partialMatch[0].length);
                    }

                    return combined;
                };

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (!trimmedLine) continue;

                        if (trimmedLine.startsWith('event: ')) {
                            currentEvent = trimmedLine.slice(7).trim();
                        } else if (trimmedLine.startsWith('data: ')) {
                            const data = trimmedLine.slice(6);
                            try {
                                if (currentEvent === 'chunk') {
                                    const parsed = JSON.parse(data);
                                    if (parsed.content) {
                                        // 🎬 Extract actions BEFORE filtering metadata
                                        const withActionsExtracted = extractActions(parsed.content);
                                        // 🛡️ Filter metadata using robust handler
                                        const cleanContent = filterMetadata(withActionsExtracted);
                                        if (cleanContent) {
                                            onChunk(cleanContent);
                                        }
                                        // Always accumulate original for DB
                                        accumulatedContent += parsed.content;
                                    }
                                } else if (currentEvent === 'title' && onTitle) {
                                    const parsed = JSON.parse(data);
                                    if (parsed.title) {
                                        onTitle(parsed.title);
                                    }
                                } else if (currentEvent === 'error') {
                                    const parsed = JSON.parse(data);
                                    throw new Error(parsed.error || "Stream error");
                                } else if (currentEvent === 'cancelled') {
                                    // Handled gracefully
                                    return;
                                } else if (currentEvent === 'done') {
                                    // Stream complete
                                }
                            } catch (e: any) {
                                // Ignore parse errors for incomplete JSON
                            }
                        }
                    }
                }

                // 3. Finalize and Persist (with retry logic)
                let finalizeSuccess = false;
                let finalizeAttempts = 0;
                const MAX_FINALIZE_RETRIES = 2;

                while (!finalizeSuccess && finalizeAttempts <= MAX_FINALIZE_RETRIES) {
                    try {
                        const finRes = await fetch(`${API_URL}/api/streaming/chat/${chatId}/finalize/${generation_id}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify({
                                final_content: accumulatedContent,
                                metadata: {} // Add empty metadata to match backend expectation
                            }),
                        });

                        if (finRes.ok) {
                            const finData = await finRes.json();
                            // Handle idempotent responses which may not return a new message_id
                            const completedId = finData.message_id || finData.generation_id || ('finalized-' + generation_id);

                            // 🆕 Pass key source and model info to onComplete
                            onComplete(completedId, {
                                key_source: finData.key_source || 'platform',
                                model: finData.model || 'llama-3.1-8b-instant',
                                usage: finData.usage
                            });
                            finalizeSuccess = true;
                            return; // Success - exit retry loop
                        } else {
                            // Try to parse error details
                            let errorDetail = `HTTP ${finRes.status}`;
                            try {
                                const errorData = await finRes.json();
                                errorDetail = errorData.detail?.message || errorData.detail || errorDetail;
                            } catch {
                                // Ignore JSON parse errors
                            }

                            // Retry on 500 errors
                            if (finRes.status >= 500 && finalizeAttempts < MAX_FINALIZE_RETRIES) {
                                finalizeAttempts++;
                                await new Promise(resolve => setTimeout(resolve, 500 * finalizeAttempts));
                                continue;
                            }

                            // If finalize fails after retries, we still show the message but it may not be saved
                            console.error("Finalization failed:", errorDetail);
                            onComplete('unsaved-' + Date.now());
                            return; // Exit retry loop even on finalize failure
                        }
                    } catch (finalizeError: any) {
                        if (finalizeAttempts < MAX_FINALIZE_RETRIES) {
                            finalizeAttempts++;
                            await new Promise(resolve => setTimeout(resolve, 500 * finalizeAttempts));
                            continue;
                        }
                        console.error("Finalization error:", finalizeError);
                        onComplete('unsaved-' + Date.now());
                        return;
                    }
                }

            } catch (error: any) {
                // If this is the last attempt or a non-retryable error, call onError
                if (attempt >= MAX_RETRIES || error.message?.includes('already in progress')) {
                    onError(error.message || 'Failed to send message');
                    return;
                }
                // Otherwise, continue to next retry
                await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)));
            }
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

export const apiKeysAPI = {
    // Get usage stats (free requests used, limit, has_personal_keys, etc.)
    getUsage: () => handleRequest(api.get('/api-keys/usage')),

    // Get full dashboard (usage + keys + messages)
    getDashboard: () => handleRequest(api.get('/api-keys/dashboard')),

    // Get list of user's API keys (masked)
    getKeys: () => handleRequest(api.get('/api-keys/keys')),

    // Validate an API key before saving
    validateKey: (apiKey: string, provider: string = 'groq', model: string = 'llama-3.1-8b-instant') =>
        handleRequest(api.post('/api-keys/validate', { api_key: apiKey, provider, model })),

    // Add a new API key
    addKey: (apiKey: string, provider: string = 'groq', model: string = 'llama-3.1-8b-instant', label?: string, priority?: number) =>
        handleRequest(api.post('/api-keys/keys', { api_key: apiKey, provider, model, label, priority })),

    // Activate a key (set as active)
    activateKey: (keyId: string) =>
        handleRequest(api.put(`/api-keys/keys/${keyId}/activate`)),

    // Delete a key
    deleteKey: (keyId: string) =>
        handleRequest(api.delete(`/api-keys/keys/${keyId}`)),

    // Reorder keys by priority
    reorderKeys: (keyIds: string[]) =>
        handleRequest(api.put('/api-keys/keys/reorder', { key_ids: keyIds })),

    // Health check a single key
    healthCheckKey: (keyId: string) =>
        handleRequest(api.post(`/api-keys/keys/${keyId}/health-check`)),

    // Health check all keys
    healthCheckAll: () =>
        handleRequest(api.post('/api-keys/keys/health-check-all')),

    // Update key label
    updateKeyLabel: (keyId: string, label: string) =>
        handleRequest(api.put(`/api-keys/keys/${keyId}/label`, null, { params: { label } })),

    // Get supported providers and models
    getProviders: () => handleRequest(api.get('/api-keys/providers')),
};

export const mediaAPI = {
    getLibrary: (limit: number = 50, category?: string, favoritesOnly: boolean = false) =>
        handleRequest(api.get('/api/media/library', { params: { limit, category, favorites_only: favoritesOnly } })),
    searchLibrary: (query: string) =>
        handleRequest(api.get('/api/media/library/search', { params: { q: query } })),
    toggleFavorite: (videoId: string) =>
        handleRequest(api.post('/api/media/library/favorite', { video_id: videoId })),
    getStats: () =>
        handleRequest(api.get('/api/media/library/stats')),
    deleteMedia: (videoId: string) =>
        handleRequest(api.delete('/api/media/library', { params: { video_id: videoId } })),
};

export const healthAPI = {
    check: () => handleRequest(api.get('/health')),
};

export const adminAPI = {
    getStats: () => handleRequest(api.get('/admin/stats')),
    getSystemHealth: () => handleRequest(api.get('/admin/system-health')),
    getUsers: (params: { skip?: number; limit?: number; search?: string }) =>
        handleRequest(api.get('/admin/users', { params })),
    getUserDetails: (userId: string) => handleRequest(api.get(`/admin/users/${userId}/details`)),
    performUserAction: (userId: string, action: string, reason?: string) =>
        handleRequest(api.post(`/admin/users/${userId}/action`, { action, reason })),
    impersonateUser: (userId: string) => handleRequest(api.post(`/admin/users/${userId}/impersonate`)),
    getSessions: (params: { skip?: number; limit?: number }) =>
        handleRequest(api.get('/admin/sessions', { params })),
    getSessionTranscript: (sessionId: string) =>
        handleRequest(api.get(`/admin/sessions/${sessionId}/transcript`)),
    broadcast: (data: { title: string; message: string; priority: string }) =>
        handleRequest(api.post('/admin/broadcast', data)),
};
