const THEME_KEY = "rate-limiter-theme";

export function getStoredTheme() {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "dark" || stored === "light") {
    return stored;
  }
  return null;
}

export function getPreferredTheme() {
  const stored = getStoredTheme();
  if (stored) {
    return stored;
  }
  if (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    return "dark";
  }
  return "light";
}

export function applyTheme(theme) {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.setAttribute("data-theme", theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", theme === "dark" ? "#0c1222" : "#1d4ed8");
  }
}

export function setTheme(theme) {
  applyTheme(theme);
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(THEME_KEY, theme);
  }
}

export function initTheme() {
  applyTheme(getPreferredTheme());
}
