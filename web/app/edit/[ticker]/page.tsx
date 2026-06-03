"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

const TOKEN_STORAGE_KEY = "morning-digest-edit-token";

export default function EditHoldingPage() {
  const router = useRouter();
  const params = useParams();
  const search = useSearchParams();

  const ticker = decodeURIComponent(String(params.ticker ?? ""));
  const initialShares = search.get("shares") ?? "";
  const initialInvested = search.get("invested") ?? "";

  const [shares, setShares] = useState(initialShares);
  const [invested, setInvested] = useState(initialInvested);
  const [token, setToken] = useState("");
  const [hasToken, setHasToken] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (saved) {
      setToken(saved);
      setHasToken(true);
    }
  }, []);

  const currency = ticker.endsWith(".AX") ? "AUD" : "USD";
  const currencyPrefix = currency === "USD" ? "US$" : "$";

  async function callApi(method: "PUT" | "DELETE", body?: object) {
    if (!token) {
      setError("Enter your edit token first.");
      return null;
    }
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch(`/api/holdings/${encodeURIComponent(ticker)}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "x-edit-token": token,
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (res.status === 401) {
        setError("Token rejected. Double-check it and re-enter.");
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        setHasToken(false);
        return null;
      }
      if (!res.ok) {
        const text = await res.text();
        setError(`Save failed (${res.status}): ${text.slice(0, 160)}`);
        return null;
      }
      return await res.json();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    const sharesNum = parseFloat(shares);
    const investedNum = parseFloat(invested);
    if (!Number.isFinite(sharesNum) || sharesNum < 0) {
      setError("Shares must be a non-negative number (decimals like 0.173 are fine).");
      return;
    }
    if (!Number.isFinite(investedNum) || investedNum < 0) {
      setError("Total invested must be a non-negative number.");
      return;
    }
    const result = await callApi("PUT", { shares: sharesNum, total_invested: investedNum });
    if (result?.ok) {
      setSuccess("Saved! Next digest will use these numbers.");
      setTimeout(() => router.push("/"), 1200);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Remove ${ticker} from your holdings? This won't remove it from the portfolio config — just zero out the position.`)) {
      return;
    }
    const result = await callApi("DELETE");
    if (result?.ok) {
      setSuccess("Removed. Next digest will reflect the change.");
      setTimeout(() => router.push("/"), 1200);
    }
  }

  function saveToken() {
    if (!token.trim()) return;
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token.trim());
    setHasToken(true);
    setError(null);
  }

  function clearToken() {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken("");
    setHasToken(false);
  }

  return (
    <main className="max-w-md mx-auto px-4 pt-6 pb-12">
      <button
        onClick={() => router.push("/")}
        className="text-xs text-muted hover:text-gray-200 mb-4"
      >
        ← Back to digest
      </button>

      <header className="mb-6">
        <div className="text-xs uppercase tracking-widest text-muted">Edit holding</div>
        <h1 className="text-3xl font-semibold tracking-tight font-mono mt-1">{ticker}</h1>
        <div className="text-xs text-muted mt-1">{currency} denominated</div>
      </header>

      {!hasToken ? (
        <div className="section-card p-4 mb-4">
          <div className="text-sm font-semibold mb-2">🔐 Enter your edit token</div>
          <div className="text-xs text-muted leading-relaxed mb-3">
            Saved to this device only. You'll only enter it once.
          </div>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="EDIT_TOKEN"
            className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-sm font-mono"
          />
          <button
            onClick={saveToken}
            className="mt-2 w-full bg-accent text-ink font-semibold py-2 rounded-md text-sm"
          >
            Save token
          </button>
        </div>
      ) : (
        <>
          <div className="section-card p-4 mb-4 space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-widest text-muted mb-1">
                Shares owned
              </label>
              <input
                type="number"
                step="0.0001"
                inputMode="decimal"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-base font-mono"
              />
              <div className="text-[11px] text-muted mt-1">
                Fractional shares are fine — e.g. 0.173
              </div>
            </div>

            <div>
              <label className="block text-xs uppercase tracking-widest text-muted mb-1">
                Total invested ({currency})
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-sm">
                  {currencyPrefix}
                </span>
                <input
                  type="number"
                  step="0.01"
                  inputMode="decimal"
                  value={invested}
                  onChange={(e) => setInvested(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-md pl-10 pr-3 py-2 text-base font-mono"
                />
              </div>
              <div className="text-[11px] text-muted mt-1">
                Total {currency} you've put into this stock. Your broker shows this as "cost basis" or "invested".
              </div>
            </div>

            {error && (
              <div className="text-sm text-negative bg-negative/10 border border-negative/30 rounded-md p-2.5">
                {error}
              </div>
            )}
            {success && (
              <div className="text-sm text-positive bg-positive/10 border border-positive/30 rounded-md p-2.5">
                {success}
              </div>
            )}

            <button
              onClick={handleSave}
              disabled={busy}
              className="w-full bg-accent text-ink font-semibold py-2.5 rounded-md text-sm disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save"}
            </button>
          </div>

          <div className="section-card p-4">
            <button
              onClick={handleDelete}
              disabled={busy}
              className="w-full text-sm text-negative font-medium py-2 disabled:opacity-50"
            >
              Remove {ticker} from holdings
            </button>
          </div>

          <button
            onClick={clearToken}
            className="block mx-auto mt-6 text-[11px] text-muted hover:text-gray-200"
          >
            Forget token on this device
          </button>
        </>
      )}
    </main>
  );
}
