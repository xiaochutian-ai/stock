import type { HistoryItem, ResultItem, RunRequest, RunStatus } from "../types/api";

const API_BASE = "/api";

export async function createRun(payload: RunRequest): Promise<RunStatus> {
  const response = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("创建运行失败");
  }
  return response.json();
}

export async function fetchRunResults(runId: string): Promise<{ items: ResultItem[] }> {
  const response = await fetch(`${API_BASE}/runs/${runId}/results`);
  if (!response.ok) {
    throw new Error("加载结果失败");
  }
  return response.json();
}

export async function fetchHistoryList(): Promise<{ items: HistoryItem[] }> {
  const response = await fetch(`${API_BASE}/history`);
  if (!response.ok) {
    throw new Error("加载历史失败");
  }
  return response.json();
}
