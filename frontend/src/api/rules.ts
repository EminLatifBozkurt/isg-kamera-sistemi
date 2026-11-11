import { ApiError, apiError, readCsrfToken } from "./http";

export type EquipmentCode = "helmet" | "vest" | "goggles" | "gloves" | "boots";

export interface EquipmentDefinition {
  code: EquipmentCode;
  display_name: string;
  model_class: string | null;
  is_model_supported: boolean;
}

export interface NormalizedPoint {
  x: number;
  y: number;
}

export interface ZoneRule {
  id: string;
  name: string;
  polygon: NormalizedPoint[];
  required_equipment: EquipmentCode[];
}

export interface RuleDefinition {
  required_equipment: EquipmentCode[];
  zones: ZoneRule[];
}

export interface RuleVersion {
  id: string;
  camera_id: string;
  version_number: number;
  valid_from: string;
  valid_until: string | null;
  definition: RuleDefinition;
  definition_hash: string;
  created_by: string | null;
  created_at: string;
}

const EQUIPMENT_CODES = new Set<EquipmentCode>(["helmet", "vest", "goggles", "gloves", "boots"]);

function isEquipmentCode(value: unknown): value is EquipmentCode {
  return typeof value === "string" && EQUIPMENT_CODES.has(value as EquipmentCode);
}

function isPoint(value: unknown): value is NormalizedPoint {
  if (typeof value !== "object" || value === null) return false;
  const point = value as Record<string, unknown>;
  return (
    typeof point.x === "number" &&
    Number.isFinite(point.x) &&
    point.x >= 0 &&
    point.x <= 1 &&
    typeof point.y === "number" &&
    Number.isFinite(point.y) &&
    point.y >= 0 &&
    point.y <= 1
  );
}

function isZone(value: unknown): value is ZoneRule {
  if (typeof value !== "object" || value === null) return false;
  const zone = value as Record<string, unknown>;
  return (
    typeof zone.id === "string" &&
    typeof zone.name === "string" &&
    Array.isArray(zone.polygon) &&
    zone.polygon.every(isPoint) &&
    Array.isArray(zone.required_equipment) &&
    zone.required_equipment.every(isEquipmentCode)
  );
}

function parseDefinition(value: unknown): RuleDefinition {
  if (typeof value !== "object" || value === null) throw new Error("Kural tanımı okunamadı.");
  const definition = value as Record<string, unknown>;
  if (
    !Array.isArray(definition.required_equipment) ||
    !definition.required_equipment.every(isEquipmentCode) ||
    !Array.isArray(definition.zones) ||
    !definition.zones.every(isZone)
  ) {
    throw new Error("Sunucu beklenen kural tanımını döndürmedi.");
  }
  return {
    required_equipment: [...definition.required_equipment],
    zones: definition.zones.map((zone) => ({
      ...zone,
      polygon: zone.polygon.map((point) => ({ ...point })),
      required_equipment: [...zone.required_equipment],
    })),
  };
}

function parseRuleVersion(value: unknown): RuleVersion {
  if (typeof value !== "object" || value === null) throw new Error("Kural sürümü okunamadı.");
  const rule = value as Record<string, unknown>;
  if (
    typeof rule.id !== "string" ||
    typeof rule.camera_id !== "string" ||
    typeof rule.version_number !== "number" ||
    typeof rule.valid_from !== "string" ||
    !(typeof rule.valid_until === "string" || rule.valid_until === null) ||
    typeof rule.definition_hash !== "string" ||
    !(typeof rule.created_by === "string" || rule.created_by === null) ||
    typeof rule.created_at !== "string"
  ) {
    throw new Error("Sunucu beklenen kural sürümünü döndürmedi.");
  }
  return {
    id: rule.id,
    camera_id: rule.camera_id,
    version_number: rule.version_number,
    valid_from: rule.valid_from,
    valid_until: rule.valid_until,
    definition: parseDefinition(rule.definition),
    definition_hash: rule.definition_hash,
    created_by: rule.created_by,
    created_at: rule.created_at,
  };
}

export async function fetchEquipment(signal?: AbortSignal): Promise<EquipmentDefinition[]> {
  const response = await fetch("/api/v1/equipment", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw await apiError(response, "Ekipman listesi alınamadı.");
  const payload = (await response.json()) as unknown;
  if (!Array.isArray(payload)) throw new Error("Sunucu beklenen ekipman listesini döndürmedi.");
  return payload.map((item) => {
    if (typeof item !== "object" || item === null) throw new Error("Ekipman kaydı okunamadı.");
    const equipment = item as Record<string, unknown>;
    if (
      !isEquipmentCode(equipment.code) ||
      typeof equipment.display_name !== "string" ||
      !(typeof equipment.model_class === "string" || equipment.model_class === null) ||
      typeof equipment.is_model_supported !== "boolean"
    ) {
      throw new Error("Sunucu beklenen ekipman kaydını döndürmedi.");
    }
    return equipment as unknown as EquipmentDefinition;
  });
}

export async function fetchCurrentRule(cameraId: string, signal?: AbortSignal): Promise<RuleVersion | null> {
  const response = await fetch(`/api/v1/cameras/${encodeURIComponent(cameraId)}/rules/current`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal,
  });
  if (response.status === 404) return null;
  if (!response.ok) throw await apiError(response, "Etkin kamera kuralı alınamadı.");
  return parseRuleVersion((await response.json()) as unknown);
}

export async function createRuleVersion(cameraId: string, definition: RuleDefinition): Promise<RuleVersion> {
  const csrfToken = readCsrfToken();
  if (!csrfToken) throw new Error("Kuralı kaydetmek için oturum doğrulama bilgisi bulunamadı.");
  const response = await fetch(`/api/v1/cameras/${encodeURIComponent(cameraId)}/rules`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(definition),
  });
  if (!response.ok) {
    const error = await apiError(response, "Kamera kuralı kaydedilemedi.");
    if (error instanceof ApiError && error.status === 409) {
      throw new ApiError("Bu kural zaten etkin; herhangi bir değişiklik yapılmadı.", 409);
    }
    throw error;
  }
  return parseRuleVersion((await response.json()) as unknown);
}
