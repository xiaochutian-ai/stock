"""SQLite 存储实现（基于 SQLAlchemy）。

切换 MySQL/Postgres 时只需修改 options.url，例如：
- sqlite:///./data/astock.db
- mysql+pymysql://user:pass@host:3306/db
- postgresql+psycopg://user:pass@host:5432/db

后续也可以独立实现 mysql_repo.py 以使用后端特有的 upsert/批量插入优化。
"""

from __future__ import annotations

import logging
import os
from datetime import date as _date
from typing import List, Optional

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from ..models import Board, Financial, KLine, MoneyFlow, Stock
from .base import Repository
from .registry import register_repository
from .schema import Base, FinancialORM, KLineORM, MoneyFlowORM, StockORM

logger = logging.getLogger(__name__)


@register_repository("sqlite")
class SQLiteRepository(Repository):
    """SQLite / SQLAlchemy Repository 实现。"""

    def __init__(self, options: Optional[dict] = None):
        super().__init__(options)
        url = self.options.get("url", "sqlite:///./data/astock.db")
        echo = bool(self.options.get("echo", False))

        # 若是 SQLite，确保目录存在
        if url.startswith("sqlite:///"):
            db_path = url.replace("sqlite:///", "", 1)
            os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)

        self._engine = create_engine(url, echo=echo, future=True)
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)

    # ---------------- 生命周期 ----------------
    def init_schema(self) -> None:
        Base.metadata.create_all(self._engine)
        logger.info("SQLite schema initialized at %s", self._engine.url)

    def close(self) -> None:
        self._engine.dispose()

    # ---------------- Stock ----------------
    def upsert_stocks(self, stocks: List[Stock]) -> int:
        if not stocks:
            return 0
        rows = [
            {
                "code": s.code,
                "name": s.name,
                "board": s.board.value,
                "list_date": s.list_date,
                "is_st": s.is_st,
                "industry": s.industry,
            }
            for s in stocks
        ]
        with self._Session() as sess:
            self._bulk_upsert(sess, StockORM, rows, pk=["code"])
            sess.commit()
        return len(rows)

    def list_stocks(self) -> List[Stock]:
        with self._Session() as sess:
            rows = sess.execute(select(StockORM)).scalars().all()
        result: List[Stock] = []
        for r in rows:
            try:
                board = Board(r.board)
            except ValueError:
                board = Board.MAIN_BOARD
            result.append(
                Stock(
                    code=r.code,
                    name=r.name,
                    board=board,
                    list_date=r.list_date,
                    is_st=bool(r.is_st),
                    industry=r.industry,
                )
            )
        return result

    # ---------------- KLine ----------------
    def upsert_kline(self, kline: KLine) -> int:
        if kline.df is None or kline.df.empty:
            return 0
        df = kline.df.reset_index()
        # reset_index 后的列名可能是 "date" 或 "index"
        if "date" not in df.columns:
            df = df.rename(columns={df.columns[0]: "date"})

        rows = []
        for _, r in df.iterrows():
            d = r["date"]
            if isinstance(d, pd.Timestamp):
                d = d.date()
            rows.append(
                {
                    "code": kline.code,
                    "trade_date": d,
                    "open": float(r.get("open", 0) or 0),
                    "high": float(r.get("high", 0) or 0),
                    "low": float(r.get("low", 0) or 0),
                    "close": float(r.get("close", 0) or 0),
                    "volume": float(r.get("volume", 0) or 0),
                    "amount": float(r.get("amount", 0) or 0),
                    "pct_change": float(r.get("pct_change", 0) or 0),
                    "turnover_rate": float(r.get("turnover_rate", 0) or 0),
                }
            )
        with self._Session() as sess:
            self._bulk_upsert(sess, KLineORM, rows, pk=["code", "trade_date"])
            sess.commit()
        return len(rows)

    def get_kline(self, code: str) -> Optional[KLine]:
        with self._Session() as sess:
            stmt = (
                select(KLineORM)
                .where(KLineORM.code == code)
                .order_by(KLineORM.trade_date.asc())
            )
            rows = sess.execute(stmt).scalars().all()
        if not rows:
            return None
        df = pd.DataFrame(
            [
                {
                    "date": r.trade_date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "amount": r.amount,
                    "pct_change": r.pct_change,
                    "turnover_rate": r.turnover_rate,
                }
                for r in rows
            ]
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return KLine(code=code, df=df)

    # ---------------- Financial ----------------
    def upsert_financials(self, financials: List[Financial]) -> int:
        if not financials:
            return 0
        rows = [
            {
                "code": f.code,
                "report_date": f.report_date,
                "pe_ttm": f.pe_ttm,
                "pb": f.pb,
                "ps_ttm": f.ps_ttm,
                "dv_ratio": f.dv_ratio,
                "roe": f.roe,
                "gross_margin": f.gross_margin,
                "net_margin": f.net_margin,
                "revenue_yoy": f.revenue_yoy,
                "net_profit_yoy": f.net_profit_yoy,
                "total_market_cap": f.total_market_cap,
                "float_market_cap": f.float_market_cap,
            }
            for f in financials
        ]
        with self._Session() as sess:
            self._bulk_upsert(sess, FinancialORM, rows, pk=["code"])
            sess.commit()
        return len(rows)

    def get_financial(self, code: str) -> Optional[Financial]:
        with self._Session() as sess:
            r = sess.execute(
                select(FinancialORM).where(FinancialORM.code == code)
            ).scalar_one_or_none()
        if r is None:
            return None
        return Financial(
            code=r.code,
            report_date=r.report_date,
            pe_ttm=r.pe_ttm,
            pb=r.pb,
            ps_ttm=r.ps_ttm,
            dv_ratio=r.dv_ratio,
            roe=r.roe,
            gross_margin=r.gross_margin,
            net_margin=r.net_margin,
            revenue_yoy=r.revenue_yoy,
            net_profit_yoy=r.net_profit_yoy,
            total_market_cap=r.total_market_cap,
            float_market_cap=r.float_market_cap,
        )

    # ---------------- MoneyFlow ----------------
    def upsert_money_flows(self, flows: List[MoneyFlow]) -> int:
        if not flows:
            return 0
        rows = [
            {
                "code": f.code,
                "trade_date": f.trade_date,
                "main_net_inflow": f.main_net_inflow,
                "super_large_net": f.super_large_net,
                "large_net": f.large_net,
                "medium_net": f.medium_net,
                "small_net": f.small_net,
                "north_bound_hold": f.north_bound_hold,
            }
            for f in flows
        ]
        with self._Session() as sess:
            self._bulk_upsert(sess, MoneyFlowORM, rows, pk=["code", "trade_date"])
            sess.commit()
        return len(rows)

    def get_money_flows(self, code: str, days: int = 5) -> List[MoneyFlow]:
        with self._Session() as sess:
            stmt = (
                select(MoneyFlowORM)
                .where(MoneyFlowORM.code == code)
                .order_by(MoneyFlowORM.trade_date.desc())
                .limit(days)
            )
            rows = sess.execute(stmt).scalars().all()
        rows = list(reversed(rows))
        return [
            MoneyFlow(
                code=r.code,
                trade_date=r.trade_date if isinstance(r.trade_date, _date) else _date.today(),
                main_net_inflow=r.main_net_inflow or 0.0,
                super_large_net=r.super_large_net or 0.0,
                large_net=r.large_net or 0.0,
                medium_net=r.medium_net or 0.0,
                small_net=r.small_net or 0.0,
                north_bound_hold=r.north_bound_hold,
            )
            for r in rows
        ]

    # ---------------- 通用 ----------------
    # SQLite 单条 SQL 默认最多支持 32766 个绑定参数。
    # 预留一些余量，按 800 行一批插入（单行最多 ~15 个字段）。
    _BATCH_SIZE = 800

    def _bulk_upsert(self, sess: Session, orm_cls, rows: List[dict], pk: List[str]) -> None:
        """跨方言的 upsert：SQLite 用 ON CONFLICT，其它方言退化为 merge。

        为避免 SQLite 参数上限（32766），一律分批执行。
        """
        if not rows:
            return
        dialect = self._engine.dialect.name
        batch = self._BATCH_SIZE
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            if dialect == "sqlite":
                stmt = sqlite_insert(orm_cls).values(chunk)
                update_cols = {c.name: stmt.excluded[c.name]
                               for c in orm_cls.__table__.columns
                               if c.name not in pk}
                if update_cols:
                    stmt = stmt.on_conflict_do_update(index_elements=pk, set_=update_cols)
                else:
                    stmt = stmt.on_conflict_do_nothing(index_elements=pk)
                sess.execute(stmt)
            else:
                for r in chunk:
                    sess.merge(orm_cls(**r))
