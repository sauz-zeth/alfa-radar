import type { User } from "../api";

const TOKEN_KEY = "token";
const USER_KEY = "auth.user";

export type Session = {
  token: string;
  user: User;
};

export function readSession(): Session | null {
  if (typeof localStorage === "undefined") return null;
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) {
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }
  try {
    return { token, user: JSON.parse(raw) as User };
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function writeSession(session: Session): void {
  localStorage.setItem(TOKEN_KEY, session.token);
  localStorage.setItem(USER_KEY, JSON.stringify(session.user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
