/// <reference types="vitest/globals" />

import { afterEach, describe, expect, it, vi } from "vitest";

import { createRun, fetchHistoryList, fetchRunResults } from "../api/client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses relative /api paths", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({}),
    }));
    vi.stubGlobal("fetch", fetchMock);

    await createRun({
      kline_days: 120,
      output: { min_score: 0.1 },
      strategies: [],
    });
    await fetchRunResults("run-1");
    await fetchHistoryList();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/runs",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/runs/run-1/results");
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/history");
  });
});
