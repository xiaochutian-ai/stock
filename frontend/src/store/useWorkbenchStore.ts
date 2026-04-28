import { createRun, fetchHistoryList, fetchRunResults } from "../api/client";
import type { HistoryItem, ResultItem, RunRequest, RunStatus } from "../types/api";

type WorkbenchState = {
  runStatus: RunStatus | null;
  results: ResultItem[];
  historyItems: HistoryItem[];
  error: string | null;
  isSubmitting: boolean;
};

const state: WorkbenchState = {
  runStatus: null,
  results: [],
  historyItems: [],
  error: null,
  isSubmitting: false,
};

export function getWorkbenchState(): WorkbenchState {
  return state;
}

export function createDefaultRunRequest(): RunRequest {
  return {
    kline_days: 120,
    output: { min_score: 0.1 },
    strategies: [
      { name: "technical", enabled: true, weight: 0.4, params: { ma_bull: true } },
      { name: "fundamental", enabled: true, weight: 0.3, params: { pe_max: 50 } },
      {
        name: "money_flow",
        enabled: true,
        weight: 0.3,
        params: { main_inflow_days: 3, min_inflow_amount: 1000000 },
      },
    ],
  };
}

export async function submitRun(payload: RunRequest): Promise<void> {
  state.isSubmitting = true;
  state.error = null;
  try {
    state.runStatus = await createRun(payload);
    const resultPayload = await fetchRunResults(state.runStatus.run_id);
    state.results = resultPayload.items;
  } catch (error) {
    state.error = error instanceof Error ? error.message : "运行失败";
  } finally {
    state.isSubmitting = false;
  }
}

export async function loadHistory(): Promise<void> {
  state.error = null;
  try {
    const payload = await fetchHistoryList();
    state.historyItems = payload.items;
  } catch (error) {
    state.error = error instanceof Error ? error.message : "加载历史失败";
  }
}
