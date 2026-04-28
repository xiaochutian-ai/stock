/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />

import { render, screen } from "@testing-library/react";

import { WorkbenchPage } from "../pages/WorkbenchPage";

test("renders run form and result table regions", () => {
  render(<WorkbenchPage />);

  expect(screen.getByRole("heading", { name: "选股工作台" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始选股" })).toBeInTheDocument();
  expect(screen.getByText("结果列表")).toBeInTheDocument();
});
