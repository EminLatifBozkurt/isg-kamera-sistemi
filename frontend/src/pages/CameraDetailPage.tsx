import { useEffect, useState } from "react";
import {
  ArrowBackRounded,
  ImageNotSupportedRounded,
  RefreshRounded,
  VideocamRounded,
  WarningAmberRounded,
} from "@mui/icons-material";
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Typography } from "@mui/material";
import { Link, useParams } from "react-router-dom";

import {
  cameraSourceDetail,
  cameraSourceLabel,
  fetchCamera,
  fetchPreviewStatus,
  previewImageUrl,
  type Camera,
  type CameraPreviewStatus,
} from "../api/cameras";
import { PageHeader } from "../components/PageHeader";
import { RuleEditor } from "../components/RuleEditor";

export function CameraDetailPage() {
  const { cameraId = "" } = useParams();
  const [camera, setCamera] = useState<Camera | null>(null);
  const [preview, setPreview] = useState<CameraPreviewStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      fetchCamera(cameraId, controller.signal),
      fetchPreviewStatus(cameraId, controller.signal),
    ])
      .then(([cameraResult, previewResult]) => {
        setCamera(cameraResult);
        setPreview(previewResult);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Kamera bilgisi alınamadı.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [cameraId]);

  useEffect(() => {
    const controller = new AbortController();
    const interval = window.setInterval(() => {
      void fetchPreviewStatus(cameraId, controller.signal)
        .then((value) => {
          setPreview(value);
          setImageFailed(false);
        })
        .catch(() => undefined);
    }, 2000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [cameraId]);

  const imageUrl =
    preview?.captured_at && preview.state !== "unavailable"
      ? previewImageUrl(cameraId, preview.captured_at)
      : null;

  return (
    <>
      <PageHeader
        eyebrow="KAMERA AYRINTISI"
        title={camera?.name ?? "Kamera"}
        description="Kamera kaynağını ve analiz sürecinin paylaştığı tek son-kare önizlemesini incele."
        action={
          <Button component={Link} to="/kameralar" variant="outlined" startIcon={<ArrowBackRounded />}>
            Kameralara dön
          </Button>
        }
      />

      {error && <Alert severity="error" className="page-alert">{error}</Alert>}
      <Alert severity="info" className="page-alert">
        Bu ekran yeni analiz veya GPU işlemi başlatmaz; çalışan analiz sürecinin paylaştığı son kareyi okur.
      </Alert>

      {loading ? (
        <Box className="detail-loading"><CircularProgress size={30} /></Box>
      ) : camera ? (
        <>
        <Box className="camera-detail-grid">
          <Card className="preview-card">
            <Box className="preview-stage">
              {imageUrl && !imageFailed ? (
                <img src={imageUrl} alt={`${camera.name} son önizleme karesi`} onError={() => setImageFailed(true)} />
              ) : (
                <Box className="preview-empty">
                  <ImageNotSupportedRounded />
                  <Typography>Henüz paylaşılmış önizleme karesi yok</Typography>
                  <Typography component="p">Kamera/video analizi başlayınca son kare burada görünecek.</Typography>
                </Box>
              )}
              {preview?.state === "live" && <Chip className="preview-state preview-state--live" label="CANLI" size="small" />}
              {preview?.state === "stale" && (
                <Chip
                  className="preview-state preview-state--stale"
                  icon={<WarningAmberRounded />}
                  label="GÖRÜNTÜ GÜNCEL DEĞİL"
                  size="small"
                />
              )}
            </Box>
            <CardContent className="preview-caption">
              <Box>
                <Typography className="section-kicker">ORTAK ÖNİZLEME</Typography>
                <Typography component="h2" variant="h2">Son analiz karesi</Typography>
              </Box>
              <Typography className="preview-time">
                {preview?.captured_at
                  ? new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "medium" }).format(new Date(preview.captured_at))
                  : "Kare bekleniyor"}
              </Typography>
            </CardContent>
          </Card>

          <Card className="camera-info-card">
            <CardContent>
              <Typography className="section-kicker">KAYNAK BİLGİSİ</Typography>
              <Box className="camera-info-icon"><VideocamRounded /></Box>
              <Typography component="h2" variant="h2">{cameraSourceLabel(camera.source_type)}</Typography>
              <Typography className="camera-source-detail">{cameraSourceDetail(camera)}</Typography>
              <Box className="camera-meta-list">
                <Box><span>Durum</span><strong>{camera.is_active ? "Etkin" : "Pasif"}</strong></Box>
                <Box><span>Önizleme</span><strong>{preview?.state === "live" ? "Güncel" : preview?.state === "stale" ? "Eski kare" : "Yok"}</strong></Box>
                <Box><span>Boyut</span><strong>{preview?.size_bytes ? `${Math.ceil(preview.size_bytes / 1024)} KB` : "—"}</strong></Box>
              </Box>
              <Button startIcon={<RefreshRounded />} variant="outlined" fullWidth onClick={() => window.location.reload()}>
                Bilgileri yenile
              </Button>
            </CardContent>
          </Card>
        </Box>
        <RuleEditor cameraId={cameraId} previewImageUrl={imageUrl} />
        </>
      ) : null}
    </>
  );
}
