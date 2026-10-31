import type { ReactNode } from "react";
import { Box, Card, CardContent, Chip, Skeleton, Typography } from "@mui/material";

type Tone = "success" | "warning" | "neutral" | "error";

interface StatusCardProps {
  title: string;
  value: string;
  detail: string;
  icon: ReactNode;
  tone: Tone;
  badge?: string;
  loading?: boolean;
}

export function StatusCard({
  title,
  value,
  detail,
  icon,
  tone,
  badge,
  loading = false,
}: StatusCardProps) {
  return (
    <Card className={`status-card status-card--${tone}`}>
      <CardContent>
        <Box className="status-card-head">
          <Box className="status-card-icon">{icon}</Box>
          {badge && <Chip size="small" label={badge} className="status-card-badge" />}
        </Box>
        <Typography className="status-card-label">{title}</Typography>
        {loading ? (
          <Skeleton width="55%" height={34} />
        ) : (
          <Typography className="status-card-value">{value}</Typography>
        )}
        <Typography className="status-card-detail">{detail}</Typography>
      </CardContent>
    </Card>
  );
}
