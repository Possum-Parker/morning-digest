import type {
  Action,
  MarketIndicator,
  NRLFixture,
  NewsStory,
  PortfolioMover,
  Urgency,
  WatchItem,
} from "@/lib/types";

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

const URGENCY_STYLES: Record<Urgency, { border: string; text: string; bg: string; label: string }> = {
  red:    { border: "border-l-negative", text: "text-negative", bg: "bg-negative/5", label: "Urgent" },
  orange: { border: "border-l-accent",   text: "text-accent",   bg: "bg-accent/5",   label: "Watch" },
  green:  { border: "border-l-positive", text: "text-positive", bg: "bg-positive/5", label: "FYI" },
};

const ACTION_STYLES: Record<Action, string> = {
  buy:  "bg-positive text-ink",
  hold: "bg-white/10 text-gray-200",
  sell: "bg-negative text-white",
};

function ActionBadge({ action, ticker }: { action: Action; ticker?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${ACTION_STYLES[action]}`}
    >
      <span>{action}</span>
      {ticker && <span className="font-mono opacity-90">{ticker}</span>}
    </span>
  );
}

export function WatchTodaySection({ items }: { items: WatchItem[] }) {
  if (!items?.length) return null;
  return (
    <section className="section-card p-5 mb-4">
      <h2 className="text-lg font-semibold mb-3">👀 Watch Today</h2>
      <ul className="space-y-2.5">
        {items.map((w, i) => {
          const styles = URGENCY_STYLES[w.urgency] ?? URGENCY_STYLES.green;
          return (
            <li
              key={i}
              className={`border-l-4 ${styles.border} ${styles.bg} pl-3 pr-2 py-2 rounded-r`}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] uppercase tracking-widest font-bold ${styles.text}`}>
                  {styles.label}
                </span>
                {w.action && <ActionBadge action={w.action} ticker={w.ticker} />}
              </div>
              <div className="text-sm font-semibold mt-0.5">{w.title}</div>
              <div className="text-sm text-gray-300 mt-0.5">{w.detail}</div>
            </li>
          );
        })}
      </ul>
      <div className="text-[10px] text-muted mt-3 leading-relaxed border-t border-white/5 pt-2">
        AI-generated suggestions based on news and price data. Not financial advice — do your own
        research before acting.
      </div>
    </section>
  );
}

/* ---------- NRL ---------- */

function TeamRow({
  name,
  badge,
  score,
  isWinner,
}: {
  name: string;
  badge?: string;
  score?: number | null;
  isWinner: boolean;
}) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      {badge ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={badge} alt="" className="w-5 h-5 shrink-0 object-contain" />
      ) : (
        <span className="w-5 h-5 shrink-0 rounded-full bg-white/10" />
      )}
      <span
        className={`text-sm truncate ${isWinner ? "font-semibold" : "font-medium"}`}
      >
        {name}
      </span>
      {score != null && (
        <span
          className={`ml-auto text-sm font-mono shrink-0 ${
            isWinner ? "font-bold text-positive" : "text-muted"
          }`}
        >
          {score}
        </span>
      )}
    </div>
  );
}

function NRLCard({ fixture }: { fixture: NRLFixture }) {
  const completed = Boolean(
    fixture.completed && fixture.home_score != null && fixture.away_score != null
  );
  const homeWins = completed && (fixture.home_score ?? 0) > (fixture.away_score ?? 0);
  const awayWins = completed && (fixture.away_score ?? 0) > (fixture.home_score ?? 0);

  return (
    <div className="border border-white/5 rounded-lg p-3 flex items-center justify-between gap-3">
      <div className="space-y-1.5 min-w-0 flex-1">
        <TeamRow
          name={fixture.home}
          badge={fixture.home_badge}
          score={completed ? fixture.home_score : null}
          isWinner={homeWins}
        />
        <TeamRow
          name={fixture.away}
          badge={fixture.away_badge}
          score={completed ? fixture.away_score : null}
          isWinner={awayWins}
        />
      </div>
      {!completed && (
        <div className="text-right text-xs shrink-0 self-center">
          <div className="text-gray-300 font-medium whitespace-nowrap">{fixture.day}</div>
          <div className="text-muted whitespace-nowrap">{fixture.time}</div>
        </div>
      )}
      {completed && (
        <div className="text-[10px] uppercase tracking-widest text-muted shrink-0 self-center">
          Full Time
        </div>
      )}
    </div>
  );
}

export function NRLDrawSection({ fixtures }: { fixtures: NRLFixture[] }) {
  return (
    <section className="section-card p-5 mb-4">
      <h2 className="text-lg font-semibold mb-3">🏉 NRL — Results & Fixtures</h2>
      {fixtures?.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {fixtures.map((f, i) => (
            <NRLCard key={i} fixture={f} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted py-3 leading-relaxed">
          No NRL fixtures available right now. This is usually a bye round
          (State of Origin or off-season) — the next round will show here as soon as data is available.
        </p>
      )}
    </section>
  );
}
