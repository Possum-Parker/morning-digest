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

export interface WatchItem {
  title: string;
  detail: string;
}

export interface Digest {
  generated_at_utc: string;
  headline: string;
  portfolio: { summary: string; movers: PortfolioMover[] };
  markets: { summary: string; indicators: MarketIndicator[] };
  politics: { summary: string; stories: NewsStory[] };
  ai: { summary: string; stories: NewsStory[] };
  sport: { summary: string; stories: NewsStory[] };
  watch_today: WatchItem[];
}
