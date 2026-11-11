import { apiError } from "./http";

export type CameraSourceType = "webcam" | "recorded_video" | "rtsp";
export type PreviewState = "live" | "stale" | "unavailable";

export interface Camera {
  id: string;
  name: string;
  source_type: CameraSourceType;
  source_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CameraPreviewStatus {
  camera_id: string;
  state: PreviewState;
  captured_at: string | null;
  age_seconds: number | null;
  size_bytes: number | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCamera(value: unknown): value is Camera {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    (value.source_type === "webcam" ||
      value.source_type === "recorded_video" ||
      value.source_type === "rtsp") &&
    isRecord(value.source_config) &&
    typeof value.is_active === "boolean" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

function isPreviewStatus(value: unknown): value is CameraPreviewStatus {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.camera_id === "string" &&
    (value.state === "live" || value.state === "stale" || value.state === "unavailable") &&
    (typeof value.captured_at === "string" || value.captured_at === null) &&
    (typeof value.age_seconds === "number" || value.age_seconds === null) &&
    (typeof value.size_bytes === "number" || value.size_bytes === null)
  );
}

export async function fetchCameras(signal?: AbortSignal): Promise<Camera[]> {
  const response = await fetch("/api/v1/cameras?include_inactive=true", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "Kamera listesi alınamadı.");
  }
  const payload: unknown = await response.json();
  if (!Array.isArray(payload) || !payload.every(isCamera)) {
    throw new Error("Sunucu beklenen kamera listesi biçimini döndürmedi.");
  }
  return payload;
}

export async function fetchCamera(cameraId: string, signal?: AbortSignal): Promise<Camera> {
  const response = await fetch(`/api/v1/cameras/${encodeURIComponent(cameraId)}`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "Kamera bilgisi alınamadı.");
  }
  const payload: unknown = await response.json();
  if (!isCamera(payload)) {
    throw new Error("Sunucu beklenen kamera bilgisi biçimini döndürmedi.");
  }
  return payload;
}

export async function fetchPreviewStatus(
  cameraId: string,
  signal?: AbortSignal,
): Promise<CameraPreviewStatus> {
  const response = await fetch(
    `/api/v1/cameras/${encodeURIComponent(cameraId)}/preview/status`,
    {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      signal,
    },
  );
  if (!response.ok) {
    throw await apiError(response, "Kamera önizleme durumu alınamadı.");
  }
  const payload: unknown = await response.json();
  if (!isPreviewStatus(payload)) {
    throw new Error("Sunucu beklenen önizleme durumu biçimini döndürmedi.");
  }
  return payload;
}

export function previewImageUrl(cameraId: string, capturedAt: string): string {
  return `/api/v1/cameras/${encodeURIComponent(cameraId)}/preview?v=${encodeURIComponent(capturedAt)}`;
}

export function cameraSourceLabel(sourceType: CameraSourceType): string {
  if (sourceType === "webcam") return "Webcam";
  if (sourceType === "recorded_video") return "Kayıtlı video";
  return "Ağ kamerası";
}

export function cameraSourceDetail(camera: Camera): string {
  if (camera.source_type === "webcam") {
    const index = camera.source_config.device_index;
    return `Cihaz ${typeof index === "number" ? index : 0}`;
  }
  if (camera.source_type === "recorded_video") {
    const path = camera.source_config.relative_path;
    return typeof path === "string" ? path : "Video yolu belirtilmemiş";
  }
  return "RTSP henüz etkin değil";
}
