"use client";

import { useEffect } from "react";

/** Registers public/sw.js (app-shell cache only; no offline sync). Skipped in dev. */
export function SwRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  return null;
}
