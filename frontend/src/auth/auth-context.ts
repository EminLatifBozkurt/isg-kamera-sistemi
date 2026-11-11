import { createContext } from "react";

import type { AuthUser } from "../api/auth";

export type AuthState = "checking" | "authenticated" | "anonymous" | "unavailable";

export interface AuthContextValue {
  state: AuthState;
  user: AuthUser | null;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
