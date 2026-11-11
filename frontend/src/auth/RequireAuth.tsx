import { CircularProgress, Typography } from "@mui/material";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./useAuth";

export function RequireAuth() {
  const { state } = useAuth();
  const location = useLocation();

  if (state === "checking") {
    return (
      <main className="auth-loading" aria-live="polite">
        <CircularProgress size={30} />
        <Typography>Oturum kontrol ediliyor…</Typography>
      </main>
    );
  }
  if (state !== "authenticated") {
    return <Navigate to="/giris" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
