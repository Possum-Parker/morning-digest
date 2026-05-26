import type { DayForecast, Weather } from "@/lib/types";

function TomorrowRow({ forecast }: { forecast: DayForecast }) {
  const high = forecast.high_c;
  const low = forecast.low_c;
  const chance = forecast.rain_chance_pct ?? 0;
  const mm = forecast.rain_mm ?? 0;
  return (
    <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-3">
      <div className="text-3xl leading-none select-none">{forecast.icon ?? "🌡️"}</div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] uppercase tracking-widest text-muted">Tomorrow</div>
        <div className="text-sm text-gray-200 truncate">{forecast.condition ?? ""}</div>
      </div>
      <div className="text-right text-[11px] leading-tight">
        <div className="text-muted">
          H {high != null ? `${Math.round(high)}°` : "—"} · L{" "}
          {low != null ? `${Math.round(low)}°` : "—"}
        </div>
        <div className="mt-1 text-gray-300">
          <span>💧 {chance}%</span>
          {mm > 0 && <span className="text-gray-400 ml-1.5">{mm}mm</span>}
        </div>
      </div>
    </div>
  );
}

export function WeatherWidget({ weather }: { weather: Weather }) {
  if (!weather || weather.error) return null;

  const temp = weather.temperature_c;
  const high = weather.high_c;
  const low = weather.low_c;
  const chance = weather.rain_chance_pct ?? 0;
  const mm = weather.rain_mm ?? 0;

  return (
    <div className="section-card p-4 mb-4">
      <div className="flex items-center gap-4">
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

      {weather.tomorrow && <TomorrowRow forecast={weather.tomorrow} />}
    </div>
  );
}
