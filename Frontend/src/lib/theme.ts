export type Theme = "light" | "dark" | "black";

export function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const body = document.body;
  
  // Remove all theme classes first
  root.classList.remove("dark", "black");
  body.classList.remove("dark", "black");
  
  if (theme === "dark") {
    root.classList.add("dark");
    body.classList.add("dark");
  } else if (theme === "black") {
    root.classList.add("dark", "black");
    body.classList.add("dark", "black");
  }
  // light theme = no classes added
}

export function initTheme(): Theme {
  const theme: Theme = "light"; // Default to light theme
  if (typeof document !== "undefined") {
    applyTheme(theme);
  }
  return theme;
}
