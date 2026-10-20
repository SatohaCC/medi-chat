"use client";

import { useEffect, useSyncExternalStore } from "react";
import { backendBaseUrl } from "../../../shared/api/endpoints";
import { ActiveMedicineCatalog } from "../api/activeMedicineCatalog";

const catalog = new ActiveMedicineCatalog(
  (url, options) => fetch(url, { ...options, credentials: "include" }),
  backendBaseUrl(),
);
const initial = catalog.snapshot;
const read = () => catalog.snapshot;
const server = () => initial;
export function useActiveMedicines() {
  const snapshot = useSyncExternalStore(catalog.subscribe, read, server);
  useEffect(() => {
    const refresh = () => {
      void catalog.refresh();
    };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener("attachment-imported", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      window.removeEventListener("attachment-imported", refresh);
    };
  }, []);
  return snapshot;
}
