import { create } from "zustand";

interface Profile {
  name: string;
  email: string;
  bio: string;
  avatarUrl: string;
  location: string;
  website: string;
  interests: string[];
  hobbies: string[];
}

interface ProfileStats {
  member_since?: string;
  last_login?: string;
  verified?: boolean;
  total_tasks?: number;
  total_sessions?: number;
}

interface ProfileState {
  profile: Profile;
  stats: ProfileStats;
  isLoading: boolean;
  isSaving: boolean;
  
  updateProfile: (updates: Partial<Profile>) => void;
  setAvatarUrl: (url: string) => void;
  setLoading: (loading: boolean) => void;
  setSaving: (saving: boolean) => void;
  loadProfileFromBackend: () => Promise<void>;
  saveProfileToBackend: (updates: Partial<Profile>) => Promise<void>;
  resetProfile: () => void;
}

export const useProfileStore = create<ProfileState>((set, get) => ({
  profile: {
    name: "",
    email: "",
    bio: "",
    avatarUrl: "",
    location: "",
    website: "",
    interests: [],
    hobbies: [],
  },
  stats: {},
  isLoading: false,
  isSaving: false,
  
  updateProfile: (updates) =>
    set((state) => ({
      profile: { ...state.profile, ...updates },
    })),
  
  setAvatarUrl: (url) =>
    set((state) => ({
      profile: { ...state.profile, avatarUrl: url },
    })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  setSaving: (saving) => set({ isSaving: saving }),
  
  loadProfileFromBackend: async () => {
    set({ isLoading: true });
    try {
      const token = localStorage.getItem('prism_auth_token');
      if (!token) throw new Error('Not authenticated');
      
      const response = await fetch('http://127.0.0.1:8000/users/profile', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (!response.ok) throw new Error('Failed to load profile');
      
      const data = await response.json();
      set({
        profile: data.profile,
        stats: data.stats,
        isLoading: false,
      });
    } catch (error) {
      console.error('Error loading profile:', error);
      set({ isLoading: false });
    }
  },
  
  saveProfileToBackend: async (updates) => {
    set({ isSaving: true });
    try {
      const token = localStorage.getItem('prism_auth_token');
      if (!token) throw new Error('Not authenticated');
      
      const response = await fetch('http://127.0.0.1:8000/users/profile', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) throw new Error('Failed to save profile');
      
      const data = await response.json();
      set((state) => ({
        profile: { ...state.profile, ...data.profile },
        isSaving: false,
      }));
      
      return data;
    } catch (error) {
      console.error('Error saving profile:', error);
      set({ isSaving: false });
      throw error;
    }
  },
  
  resetProfile: () =>
    set({
      profile: {
        name: "",
        email: "",
        bio: "",
        avatarUrl: "",
        location: "",
        website: "",
        interests: [],
        hobbies: [],
      },
      stats: {},
    }),
}));