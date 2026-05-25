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

export interface WatchItem {
  title: string;
  detail: string;
  urgency: Urgency;
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
  error?: string;
}

export interface NRLFixture {
  home: string;
  away: string;
  day: string;
  time: string;
  venue?: string;
  datetime_iso?: string;
}

export interface Digest {
  generated_at_utc: string;
  headline: string;
  weather: Weather;
  portfolio: { summary: string; movers: PortfolioMover[] };
  markets: { summary: string; indicators: MarketIndicator[] };
  politics: { summary: string; stories: NewsStory[] };
  ai: { summary: string; stories: NewsStory[] };
  sport: { summary: string; stories: NewsStory[] };
  nrl_draw: NRLFixture[];
  watch_today: WatchItem[];
}
