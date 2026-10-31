import { NotificationsNoneRounded, TuneRounded } from "@mui/icons-material";
import { Button, Card, CardContent } from "@mui/material";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function EventsPage() {
  return (
    <>
      <PageHeader
        eyebrow="İSG İNCELEME"
        title="Olaylar"
        description="Ekipman ihlali adaylarını kanıt görüntüsü, açıklama ve inceleme durumuyla takip et."
        action={
          <Button variant="outlined" startIcon={<TuneRounded />} disabled>
            Filtreler
          </Button>
        }
      />
      <Card>
        <CardContent>
          <EmptyState
            icon={<NotificationsNoneRounded />}
            title="İncelenecek olay yok"
            description="Olay üretimi henüz bağlı değil. Gelecekte yanlış alarm ve doğrulanmış ihlal burada ayrılacak."
          />
        </CardContent>
      </Card>
    </>
  );
}
