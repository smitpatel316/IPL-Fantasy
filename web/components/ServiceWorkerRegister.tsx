"use client";

import { useEffect } from "react";

/** Registers /sw.js once, browser-only (client component + feature check,
 *  so SSR never touches navigator.serviceWorker). */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* Offline support is a bonus, not a blocker. */
    });
  }, []);
  return null;
}
