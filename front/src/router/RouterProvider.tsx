import { useCallback, useEffect, useState, type ReactNode } from "react";
import { RouterContext, type NavigateOptions } from "./context";

export function RouterProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(() => ({
    path: window.location.pathname,
    search: window.location.search,
  }));

  useEffect(() => {
    const onPopState = () =>
      setLocation({ path: window.location.pathname, search: window.location.search });
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((to: string, options?: NavigateOptions) => {
    const url = new URL(to, window.location.href);
    if (url.pathname + url.search === window.location.pathname + window.location.search) return;
    if (options?.replace) window.history.replaceState(null, "", to);
    else window.history.pushState(null, "", to);
    setLocation({ path: url.pathname, search: url.search });
  }, []);

  return (
    <RouterContext.Provider value={{ path: location.path, search: location.search, navigate }}>
      {children}
    </RouterContext.Provider>
  );
}
