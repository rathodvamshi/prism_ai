import { create } from "zustand";
import { userAPI } from "@/lib/api";

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
      const result = await userAPI.getProfile();
      if (result.status !== 200 || !result.data) {
        throw new Error(result.error || "Failed to load profile");
      }
      const data = result.data;
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
      const result = await userAPI.updateProfile(updates);
      if (result.status !== 200 || !result.data) {
        throw new Error(result.error || "Failed to save profile");
      }
      const data = result.data;
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