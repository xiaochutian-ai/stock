import { useState } from "react";

import { ResultsTable } from "../components/ResultsTable";
import { StrategyConfigForm } from "../components/StrategyConfigForm";
import {
  createDefaultRunRequest,
  getWorkbenchState,
  submitRun,
} from "../store/useWorkbenchStore";

export function WorkbenchPage() {
  const [, forceRender] = useState(0);
  const state = getWorkbenchState();

  async function handleSubmit() {
    await submitRun(createDefaultRunRequest());
    forceRender((value) => value + 1);
  }

  return (
    <main>
      <StrategyConfigForm isSubmitting={state.isSubmitting} onSubmit={handleSubmit} />
      {state.error ? <p role="alert">{state.error}</p> : null}
      <ResultsTable items={state.results} />
    </main>
  );
}
