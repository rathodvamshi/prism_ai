/**
 * API Configuration and Utilities
 * Centralized API client with authentication, error handling, and type safety
 */

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  TIMEOUT: 30000,
} as const;

// Production check - warn if localhost is being used in production
if (import.meta.env.PROD && API_CONFIG.BASE_URL.includes('localhost')) {
  console.error('❌ PRODUCTION ERROR: API URL still pointing to localhost!');
  console.error('Set VITE_API_URL environment variable to your backend URL');
}

// Debug: Log configuration
console.log('API Configuration:', {
  VITE_API_URL: import.meta.env.VITE_API_URL,
  BASE_URL: API_CONFIG.BASE_URL,
  NODE_ENV: import.meta.env.NODE_ENV
});

// Types
export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  error?: string;
  status: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name?: string;
    verified?: boolean;
  };
  account_created?: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  name?: string;
}

export interface SignupResponse {
  message: string;
  email?: string;
  otp_required?: boolean;
  access_token?: string;
  token_type?: string;
  user?: any;
}

export interface OTPVerifyRequest {
  email: string;
  otp: string;
}

// Token Management
class TokenManager {
  private static readonly TOKEN_KEY = 'prism_auth_token';
  private static readonly USER_KEY = 'prism_user_data';

  static getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  static setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  static removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  static getUser() {
    const userData = localStorage.getItem(this.USER_KEY);
    return userData ? JSON.parse(userData) : null;
  }

  static setUser(user: any): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }
}

// API Client Class
class ApiClient {
  private baseURL: string;
  private timeout: number;

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
  }

  // Generic request method with error handling
  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    // Default headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
        credentials: 'include', // Always send cookies for session-based auth
      });

      clearTimeout(timeoutId);

      let data;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        return {
          status: response.status,
          error: data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      return {
        status: response.status,
        data,
      };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return {
          status: 408,
          error: 'Request timeout',
        };
      }

      return {
        status: 500,
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  // GET request
  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  // POST request
  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Authentication API
export class AuthAPI {
  private api = new ApiClient();

  // Login user
  async login(credentials: LoginRequest): Promise<ApiResponse<AuthResponse>> {
    const response = await this.api.post<AuthResponse>('/auth/login', credentials);
    return response;
  }

  // Register user
  async signup(userData: SignupRequest): Promise<ApiResponse<SignupResponse>> {
    console.log('🚀 Signup request:', userData);
    const result = await this.api.post('/auth/signup', userData);
    console.log('📥 Signup response:', result);
    return result;
  }

  // Verify OTP
  async verifyOTP(data: OTPVerifyRequest): Promise<ApiResponse<AuthResponse>> {
    const response = await this.api.post<AuthResponse>('/auth/verify-otp', data);
    return response;
  }

  // Forgot password
  async forgotPassword(email: string): Promise<ApiResponse<{ message: string }>> {
    return this.api.post('/auth/forgot-password', { email });
  }

  // Check email availability
  async checkEmail(email: string): Promise<ApiResponse<{ available: boolean }>> {
    return this.api.get(`/auth/check-email?email=${encodeURIComponent(email)}`);
  }

  // Logout
  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
  }

  // Get current user
  getCurrentUser() {
    return null;
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return false;
  }

  // Refresh token if needed
  async refreshToken(): Promise<ApiResponse<AuthResponse>> {
    // With session-based auth, refresh is handled server-side via session expiry.
    return { status: 200 };
  }

  // Session-based "me" endpoint
  async me(): Promise<ApiResponse<any>> {
    return this.api.get('/auth/me');
  }
}

// Chat API
export class ChatAPI {
  private api = new ApiClient();

  // Helper method to get auth headers
  private getAuthHeaders(): HeadersInit {
    // Session-based auth uses HTTP-only cookies; no Authorization header needed.
    return {};
  }

  // Send message with comprehensive response handling
  async sendMessage(chatId: string, message: string): Promise<ApiResponse<any>> {
    try {
      const response = await this.api.post('/chat/message', { 
        chatId, // Changed from chat_id
        message, 
      });
      
      // Log response for debugging
      console.log('💬 Chat response:', response);
      
      return response;
    } catch (error) {
      console.error('❌ Chat error:', error);
      return {
        status: 500,
        error: error instanceof Error ? error.message : 'Failed to send message'
      };
    }
  }

  // Send message with streaming support
  async sendMessageStream(
    chatId: string,
    message: string,
    onChunk: (chunk: string) => void,
    onComplete: (messageId: string) => void,
    onError: (error: string) => void,
    onAction?: (action: any) => void,
    onStatus?: (status: string) => void,
  ): Promise<void> {
    const url = `${API_CONFIG.BASE_URL}/chat/message/stream`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ chatId, message }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let messageId = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        // Decode the chunk
        buffer += decoder.decode(value, { stream: true });
        
        // Process complete SSE events (blocks ending with \n\n)
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete block in buffer

        for (const eventBlock of events) {
          const lines = eventBlock.split('\n').filter(Boolean);
          let eventType = 'token';
          let dataRaw = '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              // Accumulate data lines (strip "data:" prefix)
              dataRaw += (dataRaw ? '\n' : '') + line.slice(5).trim();
            }
          }

          try {
            if (eventType === 'start') {
              const data = JSON.parse(dataRaw || '{}');
              messageId = data.message_id || messageId;
            } else if (eventType === 'action') {
              if (onAction && dataRaw) {
                const actionData = JSON.parse(dataRaw);
                onAction(actionData);
              }
            } else if (eventType === 'status') {
              if (onStatus && dataRaw) {
                const statusData = JSON.parse(dataRaw);
                const step = typeof statusData.step === 'string' ? statusData.step : undefined;
                onStatus(step || '');
              }
            } else if (eventType === 'token') {
              // Raw token text
              if (dataRaw) {
                onChunk(dataRaw);
              }
            } else if (eventType === 'done') {
              // Done event can include usage, but frontend only needs completion
              onComplete(messageId);
              return;
            } else if (eventType === 'error') {
              const data = dataRaw ? JSON.parse(dataRaw) : {};
              throw new Error(data.message || 'Streaming error');
            }
          } catch (parseError) {
            console.error('Failed to parse SSE event:', parseError, eventBlock);
          }
        }
      }
      
      // If we exit the loop without seeing 'done', still call complete
      onComplete(messageId);
      
    } catch (error) {
      console.error('Streaming error:', error);
      onError(error instanceof Error ? error.message : 'Streaming error');
    }
  }

  // Get chat history
  async getChatHistory(chatId?: string, limit: number = 50): Promise<ApiResponse<any>> {
    if (!chatId) {
      // If no chatId is provided, return an empty list or handle as needed.
      // This prevents calling the endpoint with a malformed URL.
      return Promise.resolve({ status: 200, data: { messages: [] } });
    }
    const endpoint = `/chat/${chatId}/history`; // Corrected endpoint
    return this.api.get(endpoint);
  }

  // Get all user chats
  async getUserChats(): Promise<ApiResponse<any>> {
    return this.api.get('/chat/chats');
  }

  // Tasks API
  async confirmTask(description: string, dueDate?: string): Promise<ApiResponse<any>> {
    return this.api.post('/tasks/confirm', {
      description,
      due_date: dueDate || null,
    });
  }

  async getTasks(status?: 'pending' | 'completed'): Promise<ApiResponse<any>> {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return this.api.get(`/tasks${qs}`);
  }

  // Create new chat session
  // Mini Agent API Methods
  async createMiniAgent(
    messageId: string,
    sessionId: string,
    selectedText: string,
    userPrompt?: string
  ): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agent/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
        body: JSON.stringify({
          messageId,
          sessionId,
          selectedText,
          userPrompt: userPrompt || '',
        }),
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to create mini-agent',
      };
    }
  }

  async getMiniAgent(agentId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agent/${agentId}`, {
        method: 'GET',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to fetch mini-agent',
      };
    }
  }

  async sendMiniAgentMessage(
    agentId: string,
    content: string
  ): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agent/${agentId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
        body: JSON.stringify({ content }),
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to send mini-agent message',
      };
    }
  }

  async deleteMiniAgent(agentId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agent/${agentId}`, {
        method: 'DELETE',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to delete mini-agent',
      };
    }
  }

  async updateMiniAgentSnippet(agentId: string, selectedText: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agent/${agentId}/snippet`, {
        method: 'PATCH',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ selectedText }),
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to update snippet',
      };
    }
  }

  async getSessionMiniAgents(sessionId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/mini-agents/session/${sessionId}`, {
        method: 'GET',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to fetch session mini-agents',
      };
    }
  }

  async createNewChat(title?: string): Promise<ApiResponse<any>> {
    return this.api.post('/chat/new', { title });
  }

  // Delete chat
  async deleteChat(chatId: string): Promise<ApiResponse<any>> {
    return this.api.delete(`/chat/${chatId}`);
  }

  // Rename chat (MongoDB is source of truth)
  async renameChat(chatId: string, title: string): Promise<ApiResponse<any>> {
    return this.api.put(`/chat/${chatId}/rename`, { title });
  }

  // Pin/unpin chat (MongoDB is source of truth)
  async pinChat(chatId: string, isPinned: boolean): Promise<ApiResponse<any>> {
    return this.api.put(`/chat/${chatId}/pin`, { isPinned });
  }

  // Save/unsave chat (MongoDB is source of truth)
  async saveChat(chatId: string, isSaved: boolean): Promise<ApiResponse<any>> {
    return this.api.put(`/chat/${chatId}/save`, { isSaved });
  }

  // Get user memory summary
  async getMemorySummary(): Promise<ApiResponse<any>> {
    return this.api.get('/chat/memory-summary');
  }

  // Clear user memory (with confirmation)
  async clearMemory(): Promise<ApiResponse<any>> {
    return this.api.post('/chat/clear-memory');
  }

  // Highlight Management
  async createHighlight(
    sessionId: string,
    messageId: string,
    text: string,
    color: string,
    startIndex: number,
    endIndex: number,
    note?: string
  ): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/highlights`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
        body: JSON.stringify({
          sessionId,
          messageId,
          text,
          color,
          startIndex,
          endIndex,
          note: note || undefined,
        }),
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to create highlight',
      };
    }
  }

  async getSessionHighlights(sessionId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/highlights/${sessionId}`, {
        method: 'GET',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to fetch highlights',
      };
    }
  }

  async deleteHighlight(highlightId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/highlights/${highlightId}`, {
        method: 'DELETE',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to delete highlight',
      };
    }
  }

  async updateHighlightNote(highlightId: string, note: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/highlights/${highlightId}/note`, {
        method: 'PATCH',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ note }),
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to update highlight note',
      };
    }
  }

  // Batch load session data (messages + highlights + mini agents)
  async loadSessionData(sessionId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/chat/sessions/${sessionId}`, {
        method: 'GET',
        headers: {
          ...this.getAuthHeaders(),
        },
        credentials: 'include',
      });

      const data = await response.json();
      return {
        status: response.status,
        data,
      };
    } catch (error: any) {
      return {
        status: 500,
        error: error.message || 'Failed to load session data',
      };
    }
  }

}

// User API
export class UserAPI {
  private api = new ApiClient();

  // Get user profile
  async getProfile(): Promise<ApiResponse<any>> {
    return this.api.get('/user/profile');
  }

  // Update user profile
  async updateProfile(data: any): Promise<ApiResponse<any>> {
    return this.api.put('/user/profile', data);
  }

  // Get user statistics
  async getStats(): Promise<ApiResponse<any>> {
    return this.api.get('/user/stats');
  }
}

// Health API
export class HealthAPI {
  private api = new ApiClient();

  // Health check
  async check(): Promise<ApiResponse<any>> {
    return this.api.get('/health');
  }
}

// Export API instances
export const authAPI = new AuthAPI();
export const chatAPI = new ChatAPI();
export const userAPI = new UserAPI();
export const healthAPI = new HealthAPI();

// Export token manager for external use
export { TokenManager };