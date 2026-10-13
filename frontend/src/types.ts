export interface HomeAssistant {
  language: string;
  locale?: { language: string };
  connection: {
    sendMessagePromise<T>(message: Record<string, unknown>): Promise<T>;
  };
}

export interface ElektriakenConfig {
  type: "custom:elektriaken-card";
  title?: string;
  resolution?: 15 | 60;
  duration_minutes?: number;
  duration_presets?: number[];
  include_vat?: boolean;
}

export interface PricePoint {
  start: string;
  end: string;
  price: number;
  raw_eur_mwh: number;
  day: "today" | "tomorrow";
}

export interface PriceResponse {
  resolution: 15 | 60;
  duration_minutes: number;
  include_vat: boolean;
  vat_rate: number;
  currency: string;
  points: PricePoint[];
  best_window: null | {
    start: string;
    end: string;
    duration_minutes: number;
    average_price: number;
    savings_vs_now: number | null;
  };
  tomorrow_available: boolean;
  updated_at: string | null;
}

