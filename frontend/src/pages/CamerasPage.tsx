import { AddRounded, VideocamOffRounded } from "@mui/icons-material";
import { Alert, Button, Card, CardContent } from "@mui/material";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function CamerasPage() {
  return (
    <>
      <PageHeader
        eyebrow="KAYNAK YÖNETİMİ"
        title="Kameralar"
        description="Webcam, kayıtlı video ve ileride ağ kameralarını bölge kurallarıyla birlikte yönet."
        action={
          <Button variant="contained" startIcon={<AddRounded />} disabled>
            Kamera ekle
          </Button>
        }
      />
      <Alert severity="info" className="page-alert">
        Kamera ekleme ve bölge çizimi henüz uygulanmadı. Düğme hazırmış gibi davranmaması için devre dışı.
      </Alert>
      <Card>
        <CardContent>
          <EmptyState
            icon={<VideocamOffRounded />}
            title="Kamera kaynağı bulunmuyor"
            description="İlk olarak kayıtlı video ve bilgisayarın webcam'i eklenecek; gerçek iş yeri kamerası gerekmiyor."
          />
        </CardContent>
      </Card>
    </>
  );
}
