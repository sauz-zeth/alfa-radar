import { useCallback, useEffect, useState, type ReactNode } from "react";
import { RouterContext, type NavigateOptions } from "./context";

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((to: string, options?: NavigateOptions) => {
    if (to === window.location.pathname + window.location.search) return;
    if (options?.replace) window.history.replaceState(null, "", to);
    else window.history.pushState(null, "", to);
    setPath(new URL(to, window.location.href).pathname);
  }, []);

  return <RouterContext.Provider value={{ path, navigate }}>{children}</RouterContext.Provider>;
}
