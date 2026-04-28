import type { HistoryItem } from "../types/api";

type HistoryListProps = {
  items: HistoryItem[];
};

export function HistoryList({ items }: HistoryListProps) {
  if (items.length === 0) {
    return <p>暂无历史记录</p>;
  }

  return (
    <ul>
      {items.map((item) => (
        <li key={item.run_id}>
          <span>{item.run_id}</span>
        </li>
      ))}
    </ul>
  );
}
