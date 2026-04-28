import { useEffect, useState } from "react";

import { HistoryList } from "../components/HistoryList";
import { getWorkbenchState, loadHistory } from "../store/useWorkbenchStore";

export function HistoryPage() {
  const [, forceRender] = useState(0);
  const state = getWorkbenchState();

  useEffect(() => {
    loadHistory().finally(() => {
      forceRender((value) => value + 1);
    });
  }, []);

  return (
    <main>
      <h1>运行历史</h1>
      {state.error ? <p role="alert">{state.error}</p> : null}
      <HistoryList items={state.historyItems} />
    </main>
  );
}
