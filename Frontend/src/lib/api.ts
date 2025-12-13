/**
 * API Configuration and Utilities
 * Centralized API client with authentication, error handling, and type safety
 */

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  TIMEOUT: 30000,
} as const;

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
    const token = TokenManager.getToken();

    // Default headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
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
    
    if (response.data && response.status === 200) {
      TokenManager.setToken(response.data.access_token);
      TokenManager.setUser(response.data.user);
    }
    
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
    
    if (response.data && response.status === 200) {
      TokenManager.setToken(response.data.access_token);
      TokenManager.setUser(response.data.user);
    }
    
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
    TokenManager.removeToken();
  }

  // Get current user
  getCurrentUser() {
    return TokenManager.getUser();
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return !!TokenManager.getToken();
  }

  // Refresh token if needed
  async refreshToken(): Promise<ApiResponse<AuthResponse>> {
    return this.api.post<AuthResponse>('/auth/refresh');
  }
}

// Chat API
export class ChatAPI {
  private api = new ApiClient();

  // Helper method to get auth headers
  private getAuthHeaders(): HeadersInit {
    const token = TokenManager.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
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
    onError: (error: string) => void
  ): Promise<void> {
    const url = `${API_CONFIG.BASE_URL}/chat/message/stream`;
    const token = TokenManager.getToken();

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
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
        
        // Process complete SSE messages (lines ending with \n\n)
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
              
              if (data.type === 'start') {
                messageId = data.message_id;
              } else if (data.type === 'chunk') {
                onChunk(data.content);
              } else if (data.type === 'done') {
                onComplete(messageId);
                return;
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (parseError) {
              console.error('Failed to parse SSE data:', parseError);
            }
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