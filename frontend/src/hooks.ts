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
