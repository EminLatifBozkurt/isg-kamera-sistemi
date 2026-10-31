import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
  return (
    <Box className="page-header">
      <Box>
        <Typography className="page-eyebrow">{eyebrow}</Typography>
        <Typography component="h1" variant="h1">
          {title}
        </Typography>
        <Typography className="page-description">{description}</Typography>
      </Box>
      {action && <Box className="page-header-action">{action}</Box>}
    </Box>
  );
}
