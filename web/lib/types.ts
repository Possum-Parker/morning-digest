export interface PortfolioMover {
  ticker: string;
  name: string;
  change_pct: number;
  note: string;
}

export interface MarketIndicator {
  name: string;
  value: string;
  change_pct: number;
  note?: string;
}

export interface NewsStory {
  title: string;
  why_it_matters?: string;
  source?: string;
  link?: string;
  category?: string;
}

export type Urgency = "red" | "orange" | "green";
export type Action = "buy" | "hold" | "sell";

export interface WatchItem {
  title: string;
  detail: string;
  urgency: Urgency;
  action?: Action;
  ticker?: string;
}

export interface DayForecast {
  icon?: string;
  condition?: string;
  high_c?: number | null;
  low_c?: number | null;
  rain_chance_pct?: number | null;
  rain_mm?: number | null;
}

export interface Weather {
  location: string;
  icon?: string;
  condition?: string;
  temperature_c?: number | null;
  high_c?: number | null;
  low_c?: number | null;
  rain_chance_pct?: number | null;
  rain_mm?: number | null;
  tomorrow?: DayForecast;
  error?: string;
}

export interface NRLFixture {
  home: string;
  away: string;
  home_badge?: string;
  away_badge?: string;
  home_score?: number | null;
  away_score?: number | null;
  completed?: boolean;
  live_label?: string | null; // e.g. "1st Half", "Half Time", "2nd Half"
  day: string;
  time: string;
  venue?: string;
  datetime_iso?: string;
}

export interface PortfolioPosition {
  ticker: string;
  shares: number;
  currency: "AUD" | "USD" | string;
  current_price: number | null;
  current_value_native: number | null;
  current_value_aud: number | null;
  total_invested: number;
  total_invested_aud: number;
  pnl_native: number | null;
  pnl_aud: number | null;
  pnl_pct: number | null;
  day_change_pct: number | null;
}

export interface PortfolioTotals {
  positions: PortfolioPosition[];
  total_invested_aud: number;
  total_value_aud: number;
  total_pnl_aud: number;
  total_pnl_pct: number | null;
  aud_usd_rate: number;
}

export interface Digest {
  generated_at_utc: string;
  headline: string;
  weather: Weather;
  portfolio: { summary: string; movers: PortfolioMover[] };
  portfolio_totals?: PortfolioTotals;
  markets: { summary: string; indicators: MarketIndicator[] };
  politics: { summary: string; stories: NewsStory[] };
  ai: { summary: string; stories: NewsStory[] };
  sport: { summary: string; stories: NewsStory[] };
  nrl_round?: string;
  nrl_draw: NRLFixture[];
  nrl_byes?: string[];
  watch_today: WatchItem[];
}
