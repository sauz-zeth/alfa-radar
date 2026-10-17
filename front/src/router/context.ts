import { createContext } from "react";

export type NavigateOptions = { replace?: boolean };

export type RouterContextValue = {
  path: string;
  navigate: (to: string, options?: NavigateOptions) => void;
};

export const RouterContext = createContext<RouterContextValue | null>(null);
