"use client";

import { useEffect } from "react";

export function OneSignalInit() {
  useEffect(() => {
    const appId = process.env.NEXT_PUBLIC_ONESIGNAL_APP_ID;
    if (!appId) return;
    if (typeof window === "undefined") return;

    let cancelled = false;
    (async () => {
      try {
        const OneSignal = (await import("react-onesignal")).default;
        if (cancelled) return;
        await OneSignal.init({
          appId,
          allowLocalhostAsSecureOrigin: true,
          serviceWorkerParam: { scope: "/" },
          serviceWorkerPath: "/OneSignalSDKWorker.js",
        });
      } catch (err) {
        console.warn("OneSignal init failed:", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
