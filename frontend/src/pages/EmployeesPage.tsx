import { PersonAddAltRounded, GroupsRounded } from "@mui/icons-material";
import { Button, Card, CardContent } from "@mui/material";

import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";

export function EmployeesPage() {
  return (
    <>
      <PageHeader
        eyebrow="ÇALIŞAN KAYITLARI"
        title="Çalışanlar"
        description="İSG görevlisinin doğruladığı olayları çalışan profilleri ve geçmiş kayıtlarla ilişkilendir."
        action={
          <Button variant="contained" startIcon={<PersonAddAltRounded />} disabled>
            Çalışan ekle
          </Button>
        }
      />
      <Card>
        <CardContent>
          <EmptyState
            icon={<GroupsRounded />}
            title="Çalışan kaydı bulunmuyor"
            description="Veritabanı bağlandıktan sonra çalışan numarası, profil bilgileri ve doğrulanmış olay geçmişi burada olacak."
          />
        </CardContent>
      </Card>
    </>
  );
}
