export type StrategyConfigInput = {
  name: string;
  enabled: boolean;
  weight: number;
  params: Record<string, unknown>;
};

export type RunRequest = {
  limit?: number;
  kline_days: number;
  output: { min_score: number };
  strategies: StrategyConfigInput[];
};

export type ResultItem = {
  rank: number;
  code: string;
  name: string;
  board: string;
  total_score: number;
  reasons: string;
};

export type RunStatus = {
  run_id: string;
  status: string;
  result_count: number;
};

export type HistoryItem = {
  run_id: string;
  created_at?: string;
  status?: string;
  result_count?: number;
  top_codes?: string[];
};
