"use client";

import { useCallback, useEffect, useState } from "react";

type NativeState = "default" | "granted" | "denied" | "unknown";

export function NotificationManager() {
  const [nativeState, setNativeState] = useState<NativeState>("unknown");
  const [optedIn, setOptedIn] = useState<boolean>(false);
  const [oneSignal, setOneSignal] = useState<any>(null);
  const [busy, setBusy] = useState(false);

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
        if (cancelled) return;

        setOneSignal(OneSignal);

        const readState = () => {
          try {
            const native = (OneSignal.Notifications?.permissionNative ?? "unknown") as NativeState;
            setNativeState(native);
            setOptedIn(!!OneSignal.User?.PushSubscription?.optedIn);
          } catch {
            // ignore — SDK may still be initialising
          }
        };
        readState();

        OneSignal.Notifications?.addEventListener?.("permissionChange", () => readState());
        OneSignal.User?.PushSubscription?.addEventListener?.("change", () => readState());
      } catch (err) {
        console.warn("OneSignal init failed:", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubscribe = useCallback(async () => {
    if (!oneSignal || busy) return;
    setBusy(true);
    try {
      await oneSignal.Notifications.requestPermission();
      await oneSignal.User.PushSubscription.optIn();
    } catch (err) {
      console.warn("Subscribe failed:", err);
    } finally {
      setBusy(false);
    }
  }, [oneSignal, busy]);

  if (!process.env.NEXT_PUBLIC_ONESIGNAL_APP_ID) return null;
  if (nativeState === "unknown") return null;
  if (optedIn && nativeState === "granted") return null;

  if (nativeState === "denied") {
    return (
      <div className="section-card p-3 mb-4 border-accent/40 text-sm">
        <div className="font-semibold text-accent mb-1">🔔 Notifications blocked</div>
        <div className="text-xs text-gray-300 leading-relaxed">
          Open iOS Settings → Morning Digest → Notifications → toggle Allow Notifications ON.
        </div>
      </div>
    );
  }

  return (
    <div className="section-card p-3 mb-4 flex items-center justify-between gap-3">
      <div className="text-sm min-w-0">
        <div className="font-semibold">🔔 Get morning notifications</div>
        <div className="text-xs text-gray-400 mt-0.5">A daily nudge when your digest is ready.</div>
      </div>
      <button
        onClick={handleSubscribe}
        disabled={busy}
        className="text-sm font-medium bg-accent text-ink px-3 py-1.5 rounded-md hover:opacity-90 disabled:opacity-50 shrink-0"
      >
        {busy ? "…" : "Enable"}
      </button>
    </div>
  );
}
