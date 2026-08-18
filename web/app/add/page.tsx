"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const TOKEN_STORAGE_KEY = "morning-digest-edit-token";

type Exchange = "ASX" | "NASDAQ" | "NYSE";

// Build the yfinance/holdings key from a raw ticker + exchange.
// ASX listings use a ".AX" suffix; US listings use the bare symbol.
function buildKey(rawTicker: string, exchange: Exchange): string {
  const t = rawTicker.trim().toUpperCase().replace(/\.AX$/, "");
  return exchange === "ASX" ? `${t}.AX` : t;
}

export default function AddHoldingPage() {
  const router = useRouter();

  const [ticker, setTicker] = useState("");
  const [exchange, setExchange] = useState<Exchange>("ASX");
  const [name, setName] = useState("");
  const [shares, setShares] = useState("");
  const [invested, setInvested] = useState("");

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

  const currency = exchange === "ASX" ? "AUD" : "USD";
  const currencyPrefix = currency === "USD" ? "US$" : "$";
  const previewKey = ticker ? buildKey(ticker, exchange) : "";

  function saveToken() {
    if (!token.trim()) return;
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token.trim());
    setHasToken(true);
    setError(null);
  }

  async function handleAdd() {
    setError(null);
    setSuccess(null);

    if (!ticker.trim()) {
      setError("Enter a ticker symbol (e.g. WBC, AAPL).");
      return;
    }
    const sharesNum = parseFloat(shares);
    const investedNum = parseFloat(invested);
    if (!Number.isFinite(sharesNum) || sharesNum <= 0) {
      setError("Shares must be a positive number (decimals like 0.173 are fine).");
      return;
    }
    if (!Number.isFinite(investedNum) || investedNum < 0) {
      setError("Total invested must be a non-negative number.");
      return;
    }

    const key = buildKey(ticker, exchange);
    setBusy(true);
    try {
      const res = await fetch(`/api/holdings/${encodeURIComponent(key)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "x-edit-token": token,
        },
        body: JSON.stringify({
          shares: sharesNum,
          total_invested: investedNum,
          name: name.trim() || key,
          exchange,
        }),
      });
      if (res.status === 401) {
        setError("Token rejected. Re-enter your edit token.");
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        setHasToken(false);
        return;
      }
      if (!res.ok) {
        const text = await res.text();
        setError(`Add failed (${res.status}): ${text.slice(0, 160)}`);
        return;
      }
      setSuccess(`Added ${key}! It'll appear in the next digest.`);
      setTimeout(() => router.push("/"), 1400);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
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
        <div className="text-xs uppercase tracking-widest text-muted">Add a holding</div>
        <h1 className="text-2xl font-semibold tracking-tight mt-1">New share</h1>
        <div className="text-xs text-muted mt-1">
          Enter what you bought — it writes to your holdings and shows up in the next digest.
        </div>
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
        <div className="section-card p-4 mb-4 space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-widest text-muted mb-1">
              Ticker symbol
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="e.g. WBC, AAPL, NVDA"
              autoCapitalize="characters"
              className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-base font-mono uppercase"
            />
            {previewKey && (
              <div className="text-[11px] text-muted mt-1">
                Will be tracked as <span className="font-mono text-gray-300">{previewKey}</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs uppercase tracking-widest text-muted mb-1">
              Exchange
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(["ASX", "NASDAQ", "NYSE"] as Exchange[]).map((ex) => (
                <button
                  key={ex}
                  onClick={() => setExchange(ex)}
                  className={`text-sm font-medium py-2 rounded-md border transition ${
                    exchange === ex
                      ? "bg-accent text-ink border-accent"
                      : "bg-white/5 border-white/10 text-gray-300"
                  }`}
                >
                  {ex}
                </button>
              ))}
            </div>
            <div className="text-[11px] text-muted mt-1">
              {exchange === "ASX" ? "Australian — priced in AUD" : "US — priced in USD"}
            </div>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-widest text-muted mb-1">
              Company name <span className="normal-case text-muted">(optional)</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Westpac Banking Corp"
              className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-base"
            />
          </div>

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
              placeholder="0.173"
              className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-base font-mono"
            />
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
                placeholder="50.00"
                className="w-full bg-white/5 border border-white/10 rounded-md pl-10 pr-3 py-2 text-base font-mono"
              />
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
            onClick={handleAdd}
            disabled={busy}
            className="w-full bg-accent text-ink font-semibold py-2.5 rounded-md text-sm disabled:opacity-50"
          >
            {busy ? "Adding…" : "Add holding"}
          </button>
        </div>
      )}
    </main>
  );
}
