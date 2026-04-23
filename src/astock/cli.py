"""astock 命令行入口。

用法示例：
    astock run                           # 全市场选股
    astock run --limit 200               # 仅评估前 200 只（调试）
    astock run -c config/my.yaml         # 使用自定义配置
    astock run --datasource akshare      # 覆盖数据源
    astock run --storage sqlite          # 覆盖存储后端
    astock run --output csv              # 输出 csv

    astock list-providers                # 查看可用数据源
    astock list-strategies               # 查看可用策略
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import typer
from rich.console import Console

from .config import load_settings
from .datasource import list_providers
from .engine import ScreeningEngine
from .output import format_results, save_results
from .storage import list_repositories
from .strategy import list_strategies

app = typer.Typer(
    name="astock",
    help="A 股选股系统（面向接口 + 可插拔数据源/存储/策略）",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )


@app.command()
def run(
    config: str = typer.Option(
        "config/default.yaml", "-c", "--config", help="YAML 配置文件路径"
    ),
    datasource: Optional[str] = typer.Option(
        None, "--datasource", help="覆盖 datasource.name，例如 akshare"
    ),
    storage: Optional[str] = typer.Option(
        None, "--storage", help="覆盖 storage.name，例如 sqlite"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", help="输出格式: console / csv / excel / json"
    ),
    top_n: Optional[int] = typer.Option(
        None, "--top-n", help="输出前 N 名，默认读取配置"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="仅评估前 N 只股票（调试用）"
    ),
    kline_days: int = typer.Option(
        120, "--kline-days", help="拉取最近多少日 K 线"
    ),
    save: bool = typer.Option(
        False, "--save", help="是否把结果另存为文件（路径来自配置 output.path）"
    ),
    log_level: str = typer.Option("INFO", "--log-level"),
):
    """执行选股流程。"""
    settings = load_settings(config)

    # CLI 覆盖配置
    if datasource:
        settings.datasource["name"] = datasource
    if storage:
        settings.storage["name"] = storage
    if output:
        settings.output["format"] = output
    if top_n is not None:
        settings.output["top_n"] = top_n

    log_file = settings.logging_cfg.get("file")
    _setup_logging(settings.logging_cfg.get("level", log_level), log_file)

    console.rule("[bold cyan]A 股选股系统 astock[/bold cyan]")
    console.print(f"数据源 : [yellow]{settings.datasource.get('name', 'akshare')}[/yellow]")
    console.print(f"存储层 : [yellow]{settings.storage.get('name', 'sqlite')}[/yellow]")
    console.print(
        "策略组 : "
        + ", ".join(
            f"[green]{s['name']}@w={s.get('weight', 1.0)}[/green]"
            for s in settings.strategies if s.get("enabled", True)
        )
    )
    console.rule()

    engine = ScreeningEngine(settings)
    results = engine.run(limit=limit, kline_days=kline_days)

    fmt = settings.output.get("format", "console")
    n = int(settings.output.get("top_n", 50))

    if fmt == "console":
        format_results(results, fmt="console", top_n=n)
    else:
        rendered = format_results(results, fmt=fmt, top_n=n)
        if rendered and fmt in ("csv", "json"):
            console.print(rendered)

    if save and fmt != "console":
        out_dir = settings.output.get("path", "./data/output")
        path = save_results(results, fmt=fmt, out_dir=out_dir, top_n=n)
        if path:
            console.print(f"[green]✓ 结果已保存: {path}[/green]")


@app.command("list-providers")
def cmd_list_providers():
    """列出所有已注册数据源。"""
    for name in list_providers():
        console.print(f"- [cyan]{name}[/cyan]")


@app.command("list-storages")
def cmd_list_storages():
    """列出所有已注册存储后端。"""
    for name in list_repositories():
        console.print(f"- [cyan]{name}[/cyan]")


@app.command("list-strategies")
def cmd_list_strategies():
    """列出所有已注册策略。"""
    for name in list_strategies():
        console.print(f"- [cyan]{name}[/cyan]")


def main():
    app()


if __name__ == "__main__":
    main()
