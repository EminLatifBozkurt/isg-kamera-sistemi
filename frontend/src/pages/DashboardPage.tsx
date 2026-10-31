import {
  CheckCircleRounded,
  CloudDoneRounded,
  MemoryRounded,
  NotificationsNoneRounded,
  RefreshRounded,
  StorageRounded,
  VideocamOffRounded,
} from "@mui/icons-material";
import { Alert, Box, Button, Card, CardContent, Chip, Typography } from "@mui/material";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { StatusCard } from "../components/StatusCard";
import { useHealth } from "../hooks/useHealth";

const milestones = [
  { title: "Sunucu ve iş kuralları", detail: "FastAPI, health ve ekipman kural testleri", done: true },
  { title: "GPU çalışma ortamı", detail: "PyTorch CUDA ve RTX 3050 Ti doğrulandı", done: true },
  { title: "İlk model deneyi", detail: "Genel YOLO ile tek görüntü çıkarımı", done: true },
  { title: "İSG web paneli", detail: "React yönlendirmesi ve gerçek health bağlantısı hazır", done: true },
  { title: "Kamera yönetimi", detail: "Video ve webcam kaynak akışı sıradaki uygulama adımı", done: false },
];

export function DashboardPage() {
  const { data, state, error, refresh } = useHealth();
  const loading = state === "loading";
  const backendReady = state === "ready" && data?.status === "ok";

  return (
    <>
      <PageHeader
        eyebrow="SİSTEM ÖZETİ"
        title="Güvenlik merkezi"
        description="Kamera, analiz ve olay bileşenlerinin gerçek çalışma durumunu tek ekrandan izle."
        action={
          <Button
            variant="outlined"
            startIcon={<RefreshRounded />}
            onClick={() => void refresh()}
            disabled={loading}
          >
            Durumu yenile
          </Button>
        }
      />

      {state === "error" && (
        <Alert severity="error" className="dashboard-alert">
          FastAPI sunucusuna ulaşılamadı. Sunucunun 127.0.0.1:8000 adresinde çalıştığını kontrol et.
          {error ? ` Ayrıntı: ${error}` : ""}
        </Alert>
      )}

      <Box className="status-grid">
        <StatusCard
          title="Uygulama sunucusu"
          value={backendReady ? "Çalışıyor" : state === "error" ? "Bağlantı yok" : "Kontrol ediliyor"}
          detail={data ? `${data.service} · v${data.version}` : "FastAPI çalışma durumu"}
          badge={backendReady ? "CANLI" : undefined}
          icon={<CloudDoneRounded />}
          tone={backendReady ? "success" : state === "error" ? "error" : "neutral"}
          loading={loading}
        />
        <StatusCard
          title="Analiz motoru"
          value={data?.analysis === "not_configured" ? "Bağlı değil" : "Bekleniyor"}
          detail="PPE modeli henüz API sürecine bağlanmadı"
          badge="PLANLI"
          icon={<MemoryRounded />}
          tone="warning"
          loading={loading}
        />
        <StatusCard
          title="Veritabanı"
          value={data?.database === "not_configured" ? "Bağlı değil" : "Bekleniyor"}
          detail="PostgreSQL sonraki uygulama aşamasında"
          badge="PLANLI"
          icon={<StorageRounded />}
          tone="warning"
          loading={loading}
        />
        <StatusCard
          title="Kamera kaynakları"
          value="0"
          detail="Henüz webcam veya video kaynağı eklenmedi"
          icon={<VideocamOffRounded />}
          tone="neutral"
        />
      </Box>

      <Box className="dashboard-lower-grid">
        <Card className="progress-card">
          <CardContent>
            <Box className="section-heading-row">
              <Box>
                <Typography className="section-kicker">PROJE DURUMU</Typography>
                <Typography component="h2" variant="h2">
                  Geliştirme adımları
                </Typography>
              </Box>
              <Chip label="V1 + V2 hazır" size="small" className="stage-chip" />
            </Box>
            <Box className="milestone-list">
              {milestones.map((milestone) => (
                <Box className="milestone" key={milestone.title}>
                  <Box className={milestone.done ? "milestone-icon done" : "milestone-icon current"}>
                    {milestone.done ? <CheckCircleRounded /> : <span />}
                  </Box>
                  <Box>
                    <Typography className="milestone-title">{milestone.title}</Typography>
                    <Typography className="milestone-detail">{milestone.detail}</Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>

        <Card className="events-card">
          <CardContent>
            <Box className="section-heading-row">
              <Box>
                <Typography className="section-kicker">OLAY AKIŞI</Typography>
                <Typography component="h2" variant="h2">
                  Son bildirimler
                </Typography>
              </Box>
              <Chip label="0 olay" size="small" variant="outlined" />
            </Box>
            <EmptyState
              icon={<NotificationsNoneRounded />}
              title="Henüz olay kaydı yok"
              description="Veritabanı ve kamera analizi bağlandığında inceleme bekleyen bildirimler burada görünecek."
            />
          </CardContent>
        </Card>
      </Box>
    </>
  );
}
