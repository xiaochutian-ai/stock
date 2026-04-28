/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />

import { render, screen } from "@testing-library/react";

import { HistoryPage } from "../pages/HistoryPage";

test("renders history page shell", () => {
  render(<HistoryPage />);

  expect(screen.getByRole("heading", { name: "运行历史" })).toBeInTheDocument();
  expect(screen.getByText("暂无历史记录")).toBeInTheDocument();
});
