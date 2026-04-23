"""输出格式化。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

import pandas as pd
from rich.console import Console
from rich.table import Table


def _results_to_df(results: List[dict]) -> pd.DataFrame:
    return pd.DataFrame(results)


def format_results(results: List[dict], fmt: str = "console", top_n: int = 50) -> str:
    """渲染结果到控制台，并返回字符串（非 console 时）。"""
    if not results:
        Console().print("[yellow]⚠ 没有选出符合条件的股票[/yellow]")
        return ""

    df = _results_to_df(results).head(top_n)

    if fmt == "console":
        console = Console()
        table = Table(title=f"A 股选股结果 Top {len(df)}", show_lines=False)
        columns = ["rank", "code", "name", "board", "total_score"] + [
            c for c in df.columns
            if c not in {"rank", "code", "name", "board", "total_score", "reasons"}
        ]
        for col in columns:
            if col not in df.columns:
                continue
            table.add_column(col, overflow="fold")
        for _, row in df.iterrows():
            table.add_row(*[_fmt_cell(row.get(c)) for c in columns if c in df.columns])
        console.print(table)
        return ""

    if fmt == "json":
        return json.dumps(results[:top_n], ensure_ascii=False, indent=2, default=str)

    if fmt == "csv":
        return df.to_csv(index=False)

    if fmt == "excel":
        return df.to_excel  # caller 自行写文件

    raise ValueError(f"Unsupported format: {fmt}")


def _fmt_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def save_results(results: List[dict], fmt: str, out_dir: str, top_n: int = 50) -> str:
    """写入文件，返回文件路径。"""
    if not results:
        return ""
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = _results_to_df(results).head(top_n)

    if fmt == "csv":
        path = os.path.join(out_dir, f"astock_{ts}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt == "excel":
        path = os.path.join(out_dir, f"astock_{ts}.xlsx")
        df.to_excel(path, index=False)
    elif fmt == "json":
        path = os.path.join(out_dir, f"astock_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results[:top_n], f, ensure_ascii=False, indent=2, default=str)
    else:
        raise ValueError(f"save_results 不支持的格式: {fmt}")
    return path
