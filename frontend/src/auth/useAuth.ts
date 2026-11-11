import { useContext } from "react";

import { AuthContext } from "./auth-context";

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth yalnız AuthProvider içinde kullanılabilir.");
  }
  return value;
}
