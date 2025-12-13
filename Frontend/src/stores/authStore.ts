/**
 * Authentication Store
 * Manages user authentication state using Zustand
 */

import { create } from 'zustand';
import { authAPI, TokenManager } from '@/lib/api';

interface User {
  id: string;
  email: string;
  name?: string;
  verified?: boolean;
  created_at?: string;
  last_login?: string;
  profile?: any;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  showAccountCreatedAnimation: boolean;
  
  // Actions
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (email: string, password: string, name?: string) => Promise<{ success: boolean; error?: string }>;
  verifyOTP: (email: string, otp: string) => Promise<{ success: boolean; error?: string; accountCreated?: boolean }>;
  forgotPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  checkAuth: () => void;
  clearError: () => void;
  hideAccountAnimation: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  showAccountCreatedAnimation: false,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authAPI.login({ email, password });
      
      if (response.error) {
        set({ error: response.error, isLoading: false });
        return { success: false, error: response.error };
      }
      
      if (response.data) {
        set({ 
          user: response.data.user, 
          isAuthenticated: true, 
          isLoading: false,
          error: null 
        });
        return { success: true };
      }
      
      return { success: false, error: 'Unknown error occurred' };
    } catch (error) {
      const errorMsg = 'Network error. Please check your connection.';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  signup: async (email: string, password: string, name?: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authAPI.signup({ email, password, name });
      
      if (response.error) {
        set({ error: response.error, isLoading: false });
        return { success: false, error: response.error };
      }
      
      // Check if OTP is required
      if (response.data && (response.data as any).otp_required) {
        set({ isLoading: false });
        return { success: true, requiresOTP: true, message: response.data.message };
      }
      
      set({ isLoading: false, error: null });
      return { success: true };
    } catch (error) {
      const errorMsg = 'Network error. Please check your connection.';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  verifyOTP: async (email: string, otp: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authAPI.verifyOTP({ email, otp });
      
      if (response.error) {
        set({ error: response.error, isLoading: false });
        return { success: false, error: response.error };
      }
      
      if (response.data) {
        const accountCreated = response.data.account_created === true;
        
        set({ 
          user: response.data.user, 
          isAuthenticated: true, 
          isLoading: false,
          error: null,
          showAccountCreatedAnimation: accountCreated
        });
        return { success: true, accountCreated };
      }
      
      return { success: false, error: 'Unknown error occurred' };
    } catch (error) {
      const errorMsg = 'Network error. Please check your connection.';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  forgotPassword: async (email: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authAPI.forgotPassword(email);
      
      if (response.error) {
        set({ error: response.error, isLoading: false });
        return { success: false, error: response.error };
      }
      
      set({ isLoading: false, error: null });
      return { success: true };
    } catch (error) {
      const errorMsg = 'Network error. Please check your connection.';
      set({ error: errorMsg, isLoading: false });
      return { success: false, error: errorMsg };
    }
  },

  logout: () => {
    authAPI.logout();
    set({ 
      user: null, 
      isAuthenticated: false, 
      error: null 
    });
  },

  checkAuth: () => {
    const isAuth = authAPI.isAuthenticated();
    const user = authAPI.getCurrentUser();
    
    set({ 
      isAuthenticated: isAuth, 
      user: isAuth ? user : null 
    });
  },

  clearError: () => {
    set({ error: null });
  },

  hideAccountAnimation: () => {
    set({ showAccountCreatedAnimation: false });
  },
}));