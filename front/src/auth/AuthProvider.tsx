import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useApi, useQueryClient, type User } from "../api";
import { clearSession, readSession, writeSession, type Session } from "./session";

export type AuthStatus = "loading" | "anonymous" | "authenticated";

export type AuthContextValue = {
  status: AuthStatus;
  session: Session | null;
  user: User | null;
  signIn: (login: string, password: string) => Promise<{ onboardingCompleted: boolean }>;
  signUp: (login: string, password: string) => Promise<void>;
  signOut: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [session, setSession] = useState<Session | null>(() => readSession());
  const [status, setStatus] = useState<AuthStatus>(() => (readSession() ? "loading" : "anonymous"));

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    api.auth
      .me()
      .then((response) => {
        if (cancelled) return;
        const next = { token: response.access_token, user: response.user };
        writeSession(next);
        setSession(next);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        clearSession();
        setSession(null);
        setStatus("anonymous");
      });
    return () => {
      cancelled = true;
    };
    // Проверяем сохранённую сессию один раз при старте.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  useEffect(() => {
    const onStorage = () => {
      const next = readSession();
      setSession(next);
      setStatus(next ? "authenticated" : "anonymous");
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const signIn = useCallback(
    async (login: string, password: string) => {
      const response = await api.auth.login({ login, password });
      const next = { token: response.access_token, user: response.user };
      queryClient.clear();
      writeSession(next);
      setSession(next);
      setStatus("authenticated");
      return { onboardingCompleted: response.onboarding.completed };
    },
    [api, queryClient],
  );

  const signUp = useCallback(
    async (login: string, password: string) => {
      const response = await api.auth.register({ login, password });
      const next = { token: response.access_token, user: response.user };
      queryClient.clear();
      writeSession(next);
      setSession(next);
      setStatus("authenticated");
    },
    [api, queryClient],
  );

  const signOut = useCallback(() => {
    clearSession();
    queryClient.clear();
    setSession(null);
    setStatus("anonymous");
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, session, user: session?.user ?? null, signIn, signUp, signOut }),
    [session, signIn, signOut, signUp, status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
