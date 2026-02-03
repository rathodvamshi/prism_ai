import { create } from "zustand";
import { Theme, applyTheme } from "../lib/theme";

const THEME_KEY = "theme";

// Simple localStorage helpers for theme only
const getStoredTheme = (): Theme => {
  try {
    const stored = localStorage.getItem(THEME_KEY) as Theme;
    return stored === "dark" || stored === "light" || stored === "black" ? stored : "light";
  } catch {
    return "light";
  }
};

const setStoredTheme = (theme: Theme) => {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {}
};

// Apply theme immediately when module loads (before any component renders)
const initialTheme = getStoredTheme();
applyTheme(initialTheme);

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initialTheme,
  setTheme: (theme) => {
    applyTheme(theme);
    setStoredTheme(theme);
    set({ theme });
  },
}));