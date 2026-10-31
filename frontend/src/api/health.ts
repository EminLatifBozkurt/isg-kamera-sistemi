export type ServiceState = "ok";
export type ComponentState = "not_configured";

export interface HealthResponse {
  service: string;
  version: string;
  status: ServiceState;
  analysis: ComponentState;
  database: ComponentState;
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.service === "string" &&
    typeof candidate.version === "string" &&
    candidate.status === "ok" &&
    candidate.analysis === "not_configured" &&
    candidate.database === "not_configured"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Sunucu ${response.status} durum kodunu döndürdü.`);
  }

  const payload: unknown = await response.json();
  if (!isHealthResponse(payload)) {
    throw new Error("Sunucu beklenen çalışma durumu biçimini döndürmedi.");
  }
  return payload;
}
