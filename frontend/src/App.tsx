import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { RequireAuth } from "./auth/RequireAuth";
import { CamerasPage } from "./pages/CamerasPage";
import { CameraDetailPage } from "./pages/CameraDetailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { EventsPage } from "./pages/EventsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { LoginPage } from "./pages/LoginPage";

export default function App() {
  return (
    <Routes>
      <Route path="giris" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="kameralar" element={<CamerasPage />} />
          <Route path="kameralar/:cameraId" element={<CameraDetailPage />} />
          <Route path="olaylar" element={<EventsPage />} />
          <Route path="calisanlar" element={<EmployeesPage />} />
          <Route path="panel" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
