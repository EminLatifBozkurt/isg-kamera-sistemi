import { useEffect, useState } from "react";
import { ArrowForwardRounded, RefreshRounded, VideocamOffRounded, VideocamRounded } from "@mui/icons-material";
import { Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import { cameraSourceDetail, cameraSourceLabel, fetchCameras, type Camera } from "../api/cameras";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void fetchCameras(controller.signal)
      .then((value) => {
        setCameras(value);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Kameralar alınamadı.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  return (
    <>
      <PageHeader
        eyebrow="KAYNAK YÖNETİMİ"
        title="Kameralar"
        description="Webcam, kayıtlı video ve ileride ağ kameralarını bölge kurallarıyla birlikte yönet."
        action={
          <Button variant="outlined" startIcon={<RefreshRounded />} onClick={() => { setLoading(true); setReloadKey((value) => value + 1); }} disabled={loading}>
            Listeyi yenile
          </Button>
        }
      />
      {error && <Alert severity="error" className="page-alert">{error}</Alert>}
      {loading ? (
        <Box className="detail-loading"><CircularProgress size={30} /></Box>
      ) : cameras.length === 0 ? (
        <Card>
          <CardContent>
          <EmptyState
            icon={<VideocamOffRounded />}
            title="Kamera kaynağı bulunmuyor"
            description="API'de henüz kamera kaydı yok. İlk kamera yönetim akışında webcam veya kayıtlı video eklenebilir."
          />
          </CardContent>
        </Card>
      ) : (
        <Box className="camera-grid">
          {cameras.map((camera) => (
            <Card key={camera.id} className={`camera-card${camera.is_active ? "" : " camera-card--inactive"}`}>
              <CardActionArea component={Link} to={`/kameralar/${camera.id}`} className="camera-card-action">
                <CardContent>
                  <Box className="camera-card-head">
                    <Box className="camera-card-icon"><VideocamRounded /></Box>
                    <Chip label={camera.is_active ? "ETKİN" : "PASİF"} size="small" color={camera.is_active ? "success" : "default"} />
                  </Box>
                  <Typography component="h2" variant="h2">{camera.name}</Typography>
                  <Typography className="camera-card-type">{cameraSourceLabel(camera.source_type)}</Typography>
                  <Typography className="camera-card-detail">{cameraSourceDetail(camera)}</Typography>
                  <Box className="camera-card-link">Ayrıntıyı aç <ArrowForwardRounded /></Box>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Box>
      )}
    </>
  );
}
