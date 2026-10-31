import { ArrowBackRounded, SearchOffRounded } from "@mui/icons-material";
import { Button, Card, CardContent } from "@mui/material";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";

export function NotFoundPage() {
  return (
    <Card>
      <CardContent>
        <EmptyState
          icon={<SearchOffRounded />}
          title="Sayfa bulunamadı"
          description="Aradığın sayfa taşınmış veya henüz oluşturulmamış olabilir."
        />
        <div className="not-found-action">
          <Button component={Link} to="/" startIcon={<ArrowBackRounded />} variant="contained">
            Genel bakışa dön
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
