import { useEffect, useMemo, useState, type MouseEvent } from "react";
import {
  AddRounded,
  DeleteOutlineRounded,
  EditRounded,
  LayersRounded,
  SaveRounded,
  UndoRounded,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  TextField,
  Typography,
} from "@mui/material";

import {
  createRuleVersion,
  fetchCurrentRule,
  fetchEquipment,
  type EquipmentCode,
  type EquipmentDefinition,
  type NormalizedPoint,
  type RuleDefinition,
  type RuleVersion,
  type ZoneRule,
} from "../api/rules";
import { normalizePointer, polygonError } from "../rules/geometry";

interface RuleEditorProps {
  cameraId: string;
  previewImageUrl: string | null;
}

interface ZoneDraft {
  editingId: string | null;
  name: string;
  polygon: NormalizedPoint[];
  requiredEquipment: EquipmentCode[];
}

const EMPTY_DEFINITION: RuleDefinition = { required_equipment: [], zones: [] };
const EMPTY_DRAFT: ZoneDraft = { editingId: null, name: "", polygon: [], requiredEquipment: [] };

function copyDefinition(definition: RuleDefinition): RuleDefinition {
  return {
    required_equipment: [...definition.required_equipment],
    zones: definition.zones.map((zone) => ({
      ...zone,
      polygon: zone.polygon.map((point) => ({ ...point })),
      required_equipment: [...zone.required_equipment],
    })),
  };
}

function zoneId(name: string, existingIds: Set<string>): string {
  const base = name
    .toLocaleLowerCase("tr-TR")
    .replaceAll("ı", "i")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 54) || "bolge";
  let candidate = base;
  let suffix = 2;
  while (existingIds.has(candidate)) {
    candidate = `${base.slice(0, 58)}-${suffix}`;
    suffix += 1;
  }
  return candidate;
}

function toggleCode(values: EquipmentCode[], code: EquipmentCode): EquipmentCode[] {
  return values.includes(code) ? values.filter((value) => value !== code) : [...values, code];
}

function svgPoints(points: NormalizedPoint[]): string {
  return points.map((point) => `${point.x * 1000},${point.y * 562.5}`).join(" ");
}

export function RuleEditor({ cameraId, previewImageUrl }: RuleEditorProps) {
  const [equipment, setEquipment] = useState<EquipmentDefinition[]>([]);
  const [currentRule, setCurrentRule] = useState<RuleVersion | null>(null);
  const [definition, setDefinition] = useState<RuleDefinition>(copyDefinition(EMPTY_DEFINITION));
  const [draft, setDraft] = useState<ZoneDraft>({ ...EMPTY_DRAFT });
  const [imageRatio, setImageRatio] = useState(16 / 9);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([fetchEquipment(controller.signal), fetchCurrentRule(cameraId, controller.signal)])
      .then(([equipmentResult, ruleResult]) => {
        setEquipment(equipmentResult);
        setCurrentRule(ruleResult);
        setDefinition(copyDefinition(ruleResult?.definition ?? EMPTY_DEFINITION));
        setDraft({ ...EMPTY_DRAFT });
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Kamera kuralları alınamadı.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [cameraId]);

  const draftError = useMemo(() => polygonError(draft.polygon), [draft.polygon]);

  function addPoint(event: MouseEvent<SVGSVGElement>) {
    if (draft.polygon.length >= 50) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const point = normalizePointer(event.clientX, event.clientY, rect);
    setDraft((value) => ({ ...value, polygon: [...value.polygon, point] }));
    setSuccess(null);
  }

  function editZone(zone: ZoneRule) {
    setDraft({
      editingId: zone.id,
      name: zone.name,
      polygon: zone.polygon.map((point) => ({ ...point })),
      requiredEquipment: [...zone.required_equipment],
    });
    setError(null);
    setSuccess(null);
  }

  function applyZone() {
    const name = " ".concat(draft.name).trim().replace(/\s+/g, " ");
    const shapeError = polygonError(draft.polygon);
    if (name.length < 2) {
      setError("Bölge adı en az 2 karakter olmalıdır.");
      return;
    }
    if (shapeError) {
      setError(shapeError);
      return;
    }
    if (draft.requiredEquipment.length === 0) {
      setError("Bölge için en az bir zorunlu ekipman seçin.");
      return;
    }
    setDefinition((value) => {
      const existingIds = new Set(value.zones.filter((zone) => zone.id !== draft.editingId).map((zone) => zone.id));
      const id = draft.editingId ?? zoneId(name, existingIds);
      const zone: ZoneRule = {
        id,
        name,
        polygon: draft.polygon.map((point) => ({ ...point })),
        required_equipment: [...draft.requiredEquipment],
      };
      return {
        ...value,
        zones: draft.editingId
          ? value.zones.map((item) => (item.id === draft.editingId ? zone : item))
          : [...value.zones, zone],
      };
    });
    setDraft({ ...EMPTY_DRAFT });
    setError(null);
    setSuccess("Bölge taslağa uygulandı. Kalıcı olması için kural sürümünü kaydedin.");
  }

  function removeZone(id: string) {
    setDefinition((value) => ({ ...value, zones: value.zones.filter((zone) => zone.id !== id) }));
    if (draft.editingId === id) setDraft({ ...EMPTY_DRAFT });
    setSuccess("Bölge taslaktan kaldırıldı. Değişikliği kaydetmeyi unutmayın.");
  }

  async function saveRule() {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const saved = await createRuleVersion(cameraId, definition);
      setCurrentRule(saved);
      setDefinition(copyDefinition(saved.definition));
      setDraft({ ...EMPTY_DRAFT });
      setSuccess(`Kural sürümü ${saved.version_number} kaydedildi ve hemen etkinleştirildi.`);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Kamera kuralı kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <Box className="rule-loading"><CircularProgress size={28} /><Typography>Kurallar yükleniyor…</Typography></Box>;
  }

  return (
    <Card className="rule-editor-card">
      <CardContent>
        <Box className="rule-editor-heading">
          <Box>
            <Typography className="section-kicker">KAMERA VE BÖLGE KURALLARI</Typography>
            <Typography component="h2" variant="h2">Tehlikeli alanları tanımla</Typography>
            <Typography component="p">
              Görüntüye sırayla tıklayarak kapalı alan çiz; o alanda zorunlu olacak ekipmanları seç.
            </Typography>
          </Box>
          <Chip
            icon={<LayersRounded />}
            label={currentRule ? `ETKİN SÜRÜM ${currentRule.version_number}` : "İLK KURAL HAZIRLANIYOR"}
            color={currentRule ? "success" : "warning"}
            variant="outlined"
          />
        </Box>

        {error && <Alert severity="error" className="rule-alert">{error}</Alert>}
        {success && <Alert severity="success" className="rule-alert">{success}</Alert>}

        <Box className="rule-editor-grid">
          <Box>
            <Box className="rule-drawing-stage" style={{ aspectRatio: imageRatio }}>
              {previewImageUrl ? (
                <img
                  src={previewImageUrl}
                  alt="Bölge kuralı çizim karesi"
                  draggable={false}
                  onLoad={(event) => {
                    const image = event.currentTarget;
                    if (image.naturalWidth > 0 && image.naturalHeight > 0) {
                      setImageRatio(image.naturalWidth / image.naturalHeight);
                    }
                  }}
                />
              ) : (
                <Box className="rule-no-image">Önizleme yok — 16:9 örnek alan üzerinde çizim yapabilirsiniz.</Box>
              )}
              <svg
                viewBox="0 0 1000 562.5"
                preserveAspectRatio="none"
                aria-label="Tehlikeli bölge çizim alanı"
                onClick={addPoint}
              >
                {definition.zones
                  .filter((zone) => zone.id !== draft.editingId)
                  .map((zone) => (
                    <polygon key={zone.id} points={svgPoints(zone.polygon)} className="saved-zone" />
                  ))}
                {draft.polygon.length >= 2 && (
                  <polyline points={svgPoints(draft.polygon)} className="draft-zone-line" />
                )}
                {draft.polygon.length >= 3 && (
                  <polygon points={svgPoints(draft.polygon)} className="draft-zone-fill" />
                )}
                {draft.polygon.map((point, index) => (
                  <circle key={`${point.x}-${point.y}-${index}`} cx={point.x * 1000} cy={point.y * 562.5} r="7" />
                ))}
              </svg>
              <Chip className="point-counter" label={`${draft.polygon.length} NOKTA`} size="small" />
            </Box>
            <Box className="drawing-toolbar">
              <Typography>{draftError ?? "Şekil geçerli. Bölgeyi taslağa uygulayabilirsiniz."}</Typography>
              <Box>
                <Button
                  size="small"
                  startIcon={<UndoRounded />}
                  disabled={draft.polygon.length === 0}
                  onClick={() => setDraft((value) => ({ ...value, polygon: value.polygon.slice(0, -1) }))}
                >
                  Son noktayı geri al
                </Button>
                <Button
                  size="small"
                  color="inherit"
                  disabled={draft.polygon.length === 0}
                  onClick={() => setDraft((value) => ({ ...value, polygon: [] }))}
                >
                  Çizimi temizle
                </Button>
              </Box>
            </Box>
          </Box>

          <Box className="rule-controls">
            <Box className="rule-section">
              <Typography component="h3">Kameranın genel şartları</Typography>
              <Typography component="p">Görüntünün her yerinde zorunlu ekipmanlar. Ofis kamerasında boş bırakılabilir.</Typography>
              <Box className="equipment-options">
                {equipment.map((item) => (
                  <FormControlLabel
                    key={item.code}
                    control={
                      <Checkbox
                        checked={definition.required_equipment.includes(item.code)}
                        onChange={() =>
                          setDefinition((value) => ({
                            ...value,
                            required_equipment: toggleCode(value.required_equipment, item.code),
                          }))
                        }
                      />
                    }
                    label={item.display_name}
                  />
                ))}
              </Box>
            </Box>

            <Box className="rule-section">
              <Typography component="h3">{draft.editingId ? "Bölgeyi düzenle" : "Yeni bölge"}</Typography>
              <TextField
                label="Bölge adı"
                placeholder="Örn. Pres makinesi çevresi"
                size="small"
                fullWidth
                value={draft.name}
                onChange={(event) => setDraft((value) => ({ ...value, name: event.target.value }))}
              />
              <Typography component="p" className="equipment-label">Bu bölgede ek olarak zorunlu:</Typography>
              <Box className="equipment-options">
                {equipment.map((item) => (
                  <FormControlLabel
                    key={item.code}
                    control={
                      <Checkbox
                        checked={draft.requiredEquipment.includes(item.code)}
                        onChange={() =>
                          setDraft((value) => ({
                            ...value,
                            requiredEquipment: toggleCode(value.requiredEquipment, item.code),
                          }))
                        }
                      />
                    }
                    label={item.display_name}
                  />
                ))}
              </Box>
              <Box className="zone-form-actions">
                {draft.editingId && (
                  <Button color="inherit" onClick={() => setDraft({ ...EMPTY_DRAFT })}>Vazgeç</Button>
                )}
                <Button variant="outlined" startIcon={draft.editingId ? <EditRounded /> : <AddRounded />} onClick={applyZone}>
                  {draft.editingId ? "Bölgeyi güncelle" : "Bölgeyi ekle"}
                </Button>
              </Box>
            </Box>
          </Box>
        </Box>

        <Box className="zone-list-section">
          <Box className="zone-list-heading">
            <Box>
              <Typography component="h3">Tanımlı bölgeler</Typography>
              <Typography component="p">Yeşil alanlar taslaktaki kayıtlı bölgeleri gösterir.</Typography>
            </Box>
            <Button variant="contained" startIcon={<SaveRounded />} disabled={saving} onClick={() => void saveRule()}>
              {saving ? "Kaydediliyor…" : "Yeni kural sürümünü kaydet"}
            </Button>
          </Box>
          {definition.zones.length === 0 ? (
            <Typography className="zone-list-empty">Henüz özel bölge yok. Yalnız kamera genel şartları kaydedilebilir.</Typography>
          ) : (
            <Box className="zone-list">
              {definition.zones.map((zone) => (
                <Box key={zone.id} className="zone-list-item">
                  <Box>
                    <Typography component="strong">{zone.name}</Typography>
                    <Typography component="span">
                      {zone.polygon.length} nokta · {zone.required_equipment.map((code) => equipment.find((item) => item.code === code)?.display_name ?? code).join(", ")}
                    </Typography>
                  </Box>
                  <Box>
                    <Button size="small" startIcon={<EditRounded />} onClick={() => editZone(zone)}>Düzenle</Button>
                    <Button size="small" color="error" startIcon={<DeleteOutlineRounded />} onClick={() => removeZone(zone.id)}>Kaldır</Button>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
