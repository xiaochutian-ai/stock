import type { ResultItem } from "../types/api";

type ResultsTableProps = {
  items: ResultItem[];
};

export function ResultsTable({ items }: ResultsTableProps) {
  return (
    <section>
      <h2>结果列表</h2>
      <table>
        <thead>
          <tr>
            <th>排名</th>
            <th>代码</th>
            <th>名称</th>
            <th>总分</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.code}>
              <td>{item.rank}</td>
              <td>{item.code}</td>
              <td>{item.name}</td>
              <td>{item.total_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
