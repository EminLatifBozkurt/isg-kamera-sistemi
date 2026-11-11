import { apiError, readCsrfToken } from "./http";

export type UserRole = "admin" | "isg";

export interface AuthUser {
  id: string;
  username: string;
  display_name: string;
  role: UserRole;
}

interface AuthResponse {
  user: AuthUser;
}

function isAuthUser(value: unknown): value is AuthUser {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.username === "string" &&
    typeof candidate.display_name === "string" &&
    (candidate.role === "admin" || candidate.role === "isg")
  );
}

function parseAuthResponse(value: unknown): AuthUser {
  if (typeof value !== "object" || value === null || !("user" in value)) {
    throw new Error("Sunucu beklenen oturum cevabını döndürmedi.");
  }
  const user = (value as AuthResponse).user;
  if (!isAuthUser(user)) {
    throw new Error("Sunucu beklenen kullanıcı bilgisini döndürmedi.");
  }
  return user;
}

export async function fetchCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  const response = await fetch("/api/v1/auth/me", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "Oturum bilgisi alınamadı.");
  }
  return parseAuthResponse((await response.json()) as unknown);
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw await apiError(response, "Giriş yapılamadı.");
  }
  return parseAuthResponse((await response.json()) as unknown);
}

export async function logout(): Promise<void> {
  const csrfToken = readCsrfToken();
  if (!csrfToken) {
    throw new Error("Çıkış doğrulama bilgisi bulunamadı. Sayfayı yenileyip tekrar deneyin.");
  }
  const response = await fetch("/api/v1/auth/logout", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrfToken },
  });
  if (!response.ok) {
    throw await apiError(response, "Çıkış yapılamadı.");
  }
}
