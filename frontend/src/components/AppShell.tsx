import { useState } from "react";
import {
  Alert,
  AppBar,
  Avatar,
  Box,
  Button,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  Snackbar,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  DashboardRounded,
  GroupsRounded,
  HealthAndSafetyRounded,
  LogoutRounded,
  MenuRounded,
  NotificationsActiveRounded,
  VideocamRounded,
} from "@mui/icons-material";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/useAuth";

const drawerWidth = 264;

const navigation = [
  { label: "Genel Bakış", path: "/", icon: <DashboardRounded /> },
  { label: "Kameralar", path: "/kameralar", icon: <VideocamRounded /> },
  { label: "Olaylar", path: "/olaylar", icon: <NotificationsActiveRounded /> },
  { label: "Çalışanlar", path: "/calisanlar", icon: <GroupsRounded /> },
];

function pageTitle(pathname: string) {
  return navigation.find((item) => item.path === pathname)?.label ?? "İSG Kontrol Merkezi";
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Box className="sidebar-content">
      <Box className="brand-block">
        <Box className="brand-mark" aria-hidden="true">
          <HealthAndSafetyRounded />
        </Box>
        <Box>
          <Typography className="brand-title">İSG Kontrol</Typography>
          <Typography className="brand-subtitle">Güvenlik merkezi</Typography>
        </Box>
      </Box>

      <Typography className="menu-label">YÖNETİM</Typography>
      <List className="navigation-list" disablePadding>
        {navigation.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            end={item.path === "/"}
            onClick={onNavigate}
            className="navigation-item"
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>

      <Box className="sidebar-footnote">
        <Box className="sidebar-footnote-dot" />
        <Box>
          <Typography className="sidebar-footnote-title">Geliştirme ortamı</Typography>
          <Typography className="sidebar-footnote-text">Yerel ağ sürümü · 0.1.0</Typography>
        </Box>
      </Box>
    </Box>
  );
}

export function AppShell() {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const location = useLocation();
  const { user, logout } = useAuth();

  async function handleLogout() {
    setLoggingOut(true);
    setLogoutError(null);
    try {
      await logout();
    } catch (reason) {
      setLogoutError(reason instanceof Error ? reason.message : "Çıkış yapılamadı.");
    } finally {
      setLoggingOut(false);
    }
  }

  const today = new Intl.DateTimeFormat("tr-TR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());

  return (
    <Box className="app-shell">
      <AppBar
        position="fixed"
        color="inherit"
        className="topbar"
        sx={{ ml: { md: `${drawerWidth}px` }, width: { md: `calc(100% - ${drawerWidth}px)` } }}
      >
        <Toolbar className="topbar-toolbar">
          {!isDesktop && (
            <Tooltip title="Menüyü aç">
              <IconButton onClick={() => setMobileOpen(true)} edge="start" aria-label="Menüyü aç">
                <MenuRounded />
              </IconButton>
            </Tooltip>
          )}
          <Box>
            <Typography className="topbar-page-title">{pageTitle(location.pathname)}</Typography>
            <Typography className="topbar-date">{today}</Typography>
          </Box>
          <Box className="environment-pill">
            <span />
            Yerel sistem
          </Box>
          <Box className="user-summary">
            <Avatar className="user-avatar">{user?.display_name.charAt(0).toLocaleUpperCase("tr-TR")}</Avatar>
            <Box className="user-copy">
              <Typography className="user-name">{user?.display_name}</Typography>
              <Typography className="user-role">
                {user?.role === "admin" ? "Sistem yöneticisi" : "İSG görevlisi"}
              </Typography>
            </Box>
            <Tooltip title="Güvenli çıkış">
              <Button
                color="inherit"
                size="small"
                startIcon={<LogoutRounded />}
                onClick={() => void handleLogout()}
                disabled={loggingOut}
                className="logout-button"
              >
                Çıkış
              </Button>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" aria-label="Ana menü">
        <Drawer
          variant="permanent"
          open
          className="desktop-drawer"
          slotProps={{ paper: { sx: { width: drawerWidth } } }}
        >
          <SidebarContent />
        </Drawer>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          slotProps={{ paper: { sx: { width: drawerWidth } } }}
          className="mobile-drawer"
        >
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </Drawer>
      </Box>

      <Box component="main" className="main-content" sx={{ ml: { md: `${drawerWidth}px` } }}>
        <Toolbar />
        <Box className="page-container">
          <Outlet />
        </Box>
      </Box>
      <Snackbar
        open={logoutError !== null}
        autoHideDuration={5000}
        onClose={() => setLogoutError(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="error" onClose={() => setLogoutError(null)}>
          {logoutError}
        </Alert>
      </Snackbar>
    </Box>
  );
}
