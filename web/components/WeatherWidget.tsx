import type { Weather } from "@/lib/types";

export function WeatherWidget({ weather }: { weather: Weather }) {
  if (!weather || weather.error) return null;

  const temp = weather.temperature_c;
  const high = weather.high_c;
  const low = weather.low_c;
  const chance = weather.rain_chance_pct ?? 0;
  const mm = weather.rain_mm ?? 0;

  return (
    <div className="section-card p-4 mb-4 flex items-center gap-4">
      <div className="text-5xl leading-none select-none">{weather.icon ?? "🌡️"}</div>

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold tracking-tight">
            {temp != null ? `${Math.round(temp)}°` : "—"}
          </span>
          <span className="text-xs text-muted truncate">{weather.location}</span>
        </div>
        <div className="text-sm text-gray-300 mt-0.5 truncate">{weather.condition ?? ""}</div>
      </div>

      <div className="text-right text-[11px] leading-tight">
        <div className="text-muted">
          H {high != null ? `${Math.round(high)}°` : "—"} · L{" "}
          {low != null ? `${Math.round(low)}°` : "—"}
        </div>
        <div className="mt-1.5 text-gray-300">
          <span>💧 {chance}%</span>
          {mm > 0 && <span className="text-gray-400 ml-1.5">{mm}mm</span>}
        </div>
      </div>
    </div>
  );
}
