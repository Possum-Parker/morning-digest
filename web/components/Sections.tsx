import type { MarketIndicator, NewsStory, PortfolioMover, WatchItem } from "@/lib/types";

function ChangePill({ pct }: { pct: number }) {
  const positive = pct >= 0;
  return (
    <span
      className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
        positive ? "bg-positive/15 text-positive" : "bg-negative/15 text-negative"
      }`}
    >
      {positive ? "+" : ""}
      {pct.toFixed(2)}%
    </span>
  );
}

export function PortfolioSection({
  summary,
  movers,
}: {
  summary: string;
  movers: PortfolioMover[];
}) {
  return (
    <section className="section-card p-5 mb-4">
      <h2 className="text-lg font-semibold mb-2">📈 Your Portfolio</h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">{summary}</p>
      <ul className="space-y-3">
        {movers.map((m) => (
          <li key={m.ticker} className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold">{m.ticker}</span>
                <span className="text-xs text-muted truncate">{m.name}</span>
              </div>
              <div className="text-sm text-gray-300 mt-0.5">{m.note}</div>
            </div>
            <ChangePill pct={m.change_pct} />
          </li>
        ))}
      </ul>
    </section>
  );
}

export function MarketsSection({
  summary,
  indicators,
}: {
  summary: string;
  indicators: MarketIndicator[];
}) {
  return (
    <section className="section-card p-5 mb-4">
      <h2 className="text-lg font-semibold mb-2">🌏 Markets & Commodities</h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">{summary}</p>
      <div className="grid grid-cols-2 gap-3">
        {indicators.map((i) => (
          <div key={i.name} className="border border-white/5 rounded-xl p-3">
            <div className="text-xs text-muted">{i.name}</div>
            <div className="flex items-center justify-between mt-1">
              <div className="font-mono text-sm">{i.value}</div>
              <ChangePill pct={i.change_pct} />
            </div>
            {i.note && <div className="text-xs text-gray-400 mt-1">{i.note}</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

export function StoriesSection({
  icon,
  title,
  summary,
  stories,
}: {
  icon: string;
  title: string;
  summary: string;
  stories: NewsStory[];
}) {
  return (
    <section className="section-card p-5 mb-4">
      <h2 className="text-lg font-semibold mb-2">
        {icon} {title}
      </h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">{summary}</p>
      <ul className="space-y-3">
        {stories.map((s, idx) => (
          <li key={idx}>
            {s.link ? (
              <a
                href={s.link}
                target="_blank"
                rel="noreferrer"
                className="block hover:opacity-80 transition"
              >
                <div className="text-sm font-medium leading-snug">{s.title}</div>
                {s.why_it_matters && (
                  <div className="text-xs text-gray-400 mt-0.5">{s.why_it_matters}</div>
                )}
                <div className="text-[11px] text-muted mt-0.5">
                  {s.category ? `${s.category} · ` : ""}
                  {s.source}
                </div>
              </a>
            ) : (
              <>
                <div className="text-sm font-medium leading-snug">{s.title}</div>
                {s.why_it_matters && (
                  <div className="text-xs text-gray-400 mt-0.5">{s.why_it_matters}</div>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function WatchTodaySection({ items }: { items: WatchItem[] }) {
  if (!items?.length) return null;
  return (
    <section className="section-card p-5 mb-4 border-accent/40">
      <h2 className="text-lg font-semibold mb-3">👀 Watch Today</h2>
      <ul className="space-y-3">
        {items.map((w, i) => (
          <li key={i}>
            <div className="text-sm font-semibold text-accent">{w.title}</div>
            <div className="text-sm text-gray-300 mt-0.5">{w.detail}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
