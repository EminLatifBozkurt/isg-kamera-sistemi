import { createTheme } from "@mui/material/styles";

export const appTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#d97706",
      dark: "#92400e",
      light: "#fef3c7",
      contrastText: "#ffffff",
    },
    success: { main: "#16805c" },
    warning: { main: "#d97706" },
    error: { main: "#c2413b" },
    background: {
      default: "#f4f6f8",
      paper: "#ffffff",
    },
    text: {
      primary: "#172033",
      secondary: "#687386",
    },
    divider: "#e4e8ee",
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily: '"Segoe UI", "Helvetica Neue", Arial, sans-serif',
    h1: { fontSize: "2rem", lineHeight: 1.2, fontWeight: 750, letterSpacing: "-0.03em" },
    h2: { fontSize: "1.35rem", lineHeight: 1.3, fontWeight: 700, letterSpacing: "-0.015em" },
    h3: { fontSize: "1rem", lineHeight: 1.4, fontWeight: 700 },
    button: { fontWeight: 700, textTransform: "none" },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #e6e9ee",
          boxShadow: "0 8px 30px rgba(15, 23, 42, 0.045)",
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 10, minHeight: 40 } },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 700 } },
    },
  },
});
