import { useCallback, useEffect, useRef, useState } from "react";

/** Minimal hash router: "#/optimisations/abc" → { path: "/optimisations/abc", parts: ["optimisations", "abc"] } */
export function useHashRoute() {
  const read = () => {
    const h = window.location.hash.replace(/^#/, "") || "/overview";
    return { path: h, parts: h.split("/").filter(Boolean) };
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const navigate = useCallback((path: string) => {
    window.location.hash = path;
  }, []);
  return { ...route, navigate };
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], intervalMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const reload = useCallback(async () => {
    try {
      const d = await fnRef.current();
      setData(d);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    setLoading(true);
    void reload();
    if (intervalMs) {
      const id = window.setInterval(() => void reload(), intervalMs);
      return () => window.clearInterval(id);
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs]);
  return { data, error, loading, reload, setData };
}

export function useLocalStorage(key: string, initial: string) {
  const [value, setValue] = useState<string>(() => {
    try {
      return window.localStorage.getItem(key) ?? initial;
    } catch {
      return initial;
    }
  });
  const set = useCallback(
    (v: string) => {
      setValue(v);
      try {
        window.localStorage.setItem(key, v);
      } catch {
        /* ignore */
      }
    },
    [key],
  );
  return [value, set] as const;
}

export type Theme = "system" | "light" | "dark";

/** Theme preference: follows the OS by default; an explicit choice is stored and applied via data-theme. */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      const t = window.localStorage.getItem("greencode.theme");
      return t === "light" || t === "dark" ? t : "system";
    } catch {
      return "system";
    }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      if (theme === "system") window.localStorage.removeItem("greencode.theme");
      else window.localStorage.setItem("greencode.theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);
  const prefersDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const effective: "light" | "dark" = theme === "system" ? (prefersDark ? "dark" : "light") : theme;
  const toggle = useCallback(() => setThemeState(effective === "dark" ? "light" : "dark"), [effective]);
  return { theme, effective, toggle };
}

/** Keeps the browser tab title in step with the current page (also read out by screen readers on navigation). */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · GreenCode` : "GreenCode";
  }, [title]);
}
