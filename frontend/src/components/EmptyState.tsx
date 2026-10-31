import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <Box className="empty-state">
      <Box className="empty-state-icon">{icon}</Box>
      <Typography component="h2" variant="h2">
        {title}
      </Typography>
      <Typography>{description}</Typography>
    </Box>
  );
}
