import { type FormEvent, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  TextField,
  Typography,
} from "@mui/material";
import { HealthAndSafetyRounded, LoginRounded, RefreshRounded } from "@mui/icons-material";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/http";
import { useAuth } from "../auth/useAuth";

interface LoginLocationState {
  from?: { pathname?: string };
}

export function LoginPage() {
  const { state, error: sessionError, login, retry } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  if (state === "authenticated") {
    return <Navigate to="/" replace />;
  }

  const destination = (location.state as LoginLocationState | null)?.from?.pathname ?? "/";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await login(username.trim(), password);
      navigate(destination, { replace: true });
    } catch (reason) {
      setFormError(
        reason instanceof ApiError && reason.status === 401
          ? "Kullanıcı adı veya parola hatalı."
          : reason instanceof Error
            ? reason.message
            : "Giriş yapılamadı.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <Box className="login-intro">
        <Box className="login-brand-mark" aria-hidden="true">
          <HealthAndSafetyRounded />
        </Box>
        <Typography className="login-eyebrow">YEREL İSG KONTROL MERKEZİ</Typography>
        <Typography component="h1" className="login-title">
          Güvenlik olaylarını tek merkezden inceleyin.
        </Typography>
        <Typography className="login-description">
          Kamera kuralları, koruyucu ekipman bildirimleri ve çalışan olay geçmişi yalnız yetkili
          İSG kullanıcılarına açıktır.
        </Typography>
        <Box className="login-security-note">
          <span />
          Oturum bilgileri şirketin yerel sisteminde saklanır.
        </Box>
      </Box>

      <Card className="login-card" elevation={0}>
        <CardContent className="login-card-content">
          <Typography className="login-form-kicker">YETKİLİ ERİŞİM</Typography>
          <Typography component="h2" variant="h2">
            Hesabınızla giriş yapın
          </Typography>
          <Typography className="login-form-description">
            Sistem yöneticinizin oluşturduğu kullanıcı adı ve parolayı kullanın.
          </Typography>

          {state === "unavailable" && (
            <Alert
              severity="error"
              className="login-alert"
              action={
                <Button color="inherit" size="small" startIcon={<RefreshRounded />} onClick={() => void retry()}>
                  Yeniden dene
                </Button>
              }
            >
              Sunucuya ulaşılamadı.{sessionError ? ` ${sessionError}` : ""}
            </Alert>
          )}
          {formError && (
            <Alert severity="error" className="login-alert">
              {formError}
            </Alert>
          )}

          <Box component="form" className="login-form" onSubmit={(event) => void handleSubmit(event)}>
            <TextField
              label="Kullanıcı adı"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              fullWidth
              disabled={submitting || state === "checking"}
            />
            <TextField
              label="Parola"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              fullWidth
              disabled={submitting || state === "checking"}
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              startIcon={submitting ? <CircularProgress color="inherit" size={18} /> : <LoginRounded />}
              disabled={submitting || state === "checking" || state === "unavailable"}
              fullWidth
            >
              {submitting ? "Giriş yapılıyor…" : "Giriş yap"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </main>
  );
}
