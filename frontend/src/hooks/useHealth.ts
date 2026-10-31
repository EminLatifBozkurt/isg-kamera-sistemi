import { useCallback, useEffect, useState } from "react";

import { fetchHealth, type HealthResponse } from "../api/health";

export type HealthRequestState = "loading" | "ready" | "error";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Bilinmeyen bağlantı hatası.";
}

export function useHealth() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [state, setState] = useState<HealthRequestState>("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setState("loading");
    setError(null);
    try {
      const health = await fetchHealth();
      setData(health);
      setState("ready");
    } catch (requestError) {
      setData(null);
      setState("error");
      setError(errorMessage(requestError));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => {
        setData(health);
        setState("ready");
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") {
          return;
        }
        setData(null);
        setState("error");
        setError(errorMessage(requestError));
      });
    return () => controller.abort();
  }, []);

  return { data, state, error, refresh };
}
