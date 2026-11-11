import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchCurrentUser,
  login as requestLogin,
  logout as requestLogout,
  type AuthUser,
} from "../api/auth";
import { ApiError } from "../api/http";
import { AuthContext, type AuthContextValue, type AuthState } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkSession = useCallback(async (signal?: AbortSignal) => {
    setState("checking");
    setError(null);
    try {
      const currentUser = await fetchCurrentUser(signal);
      setUser(currentUser);
      setState("authenticated");
    } catch (reason) {
      if (signal?.aborted) {
        return;
      }
      setUser(null);
      if (reason instanceof ApiError && reason.status === 401) {
        setState("anonymous");
        return;
      }
      setState("unavailable");
      setError(reason instanceof Error ? reason.message : "Sunucuya ulaşılamadı.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void fetchCurrentUser(controller.signal)
      .then((currentUser) => {
        if (controller.signal.aborted) {
          return;
        }
        setUser(currentUser);
        setError(null);
        setState("authenticated");
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setUser(null);
        if (reason instanceof ApiError && reason.status === 401) {
          setState("anonymous");
          return;
        }
        setState("unavailable");
        setError(reason instanceof Error ? reason.message : "Sunucuya ulaşılamadı.");
      });
    return () => controller.abort();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const authenticatedUser = await requestLogin(username, password);
    setUser(authenticatedUser);
    setError(null);
    setState("authenticated");
  }, []);

  const logout = useCallback(async () => {
    await requestLogout();
    setUser(null);
    setError(null);
    setState("anonymous");
  }, []);

  const retry = useCallback(async () => {
    await checkSession();
  }, [checkSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ state, user, error, login, logout, retry }),
    [error, login, logout, retry, state, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
