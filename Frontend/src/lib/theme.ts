export type Theme = "light" | "dark";

export function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const body = document.body;
  if (theme === "dark") {
    root.classList.add("dark");
    body.classList.add("dark");
  } else {
    root.classList.remove("dark");
    body.classList.remove("dark");
  }
}

export function initTheme(): Theme {
  const theme: Theme = "light"; // Default to light theme
  if (typeof document !== "undefined") {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
      document.body.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
      document.body.classList.remove("dark");
    }
  }
  return theme;
}
