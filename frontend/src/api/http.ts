export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function detailFromPayload(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return null;
  }
  const detail = (payload as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : null;
}

export async function apiError(response: Response, fallback: string): Promise<ApiError> {
  let detail: string | null = null;
  try {
    detail = detailFromPayload((await response.json()) as unknown);
  } catch {
    // HTML veya boş hata cevabında kullanıcıya güvenli genel mesaj gösterilir.
  }
  return new ApiError(detail ?? fallback, response.status);
}

export function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

export function readCsrfToken(): string | null {
  // Yerel HTTP geliştirmede `csrf`, HTTPS kurulumunda __Host- önekli cookie kullanılır.
  return readCookie("__Host-csrf") ?? readCookie("csrf");
}
