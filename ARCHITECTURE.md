# astock Architecture

> 本文档只负责解释代码架构、模块边界和不变量，不承担完整文档导航职责。
> 仓库总入口见 `AGENTS.md`，人类阅读入口见 `README.md`。

## Bird's Eye View

astock 是一个面向 A 股市场的选股系统，核心诉求是**可插拔**：数据源、存储后端、选股策略三者均通过抽象接口 + 注册表模式解耦，切换任一实现不需要修改其他层的代码。

```text
┌─────────────────────────────────────────────────────────┐
│                    CLI (typer)                          │
│                    src/astock/cli.py                    │
└────────────────────────┬────────────────────────────────┘
                         │ load Settings
                         ▼
┌─────────────────────────────────────────────────────────┐
│             ScreeningEngine (engine/screener.py)        │
│   ① prepare_universe  ② batch financials               │
│   ③ per-stock kline/money_flow  ④ strategies.evaluate  │
│   ⑤ weighted score + rank       ⑥ output               │
└──────┬──────────────────┬──────────────────┬────────────┘
       │ depends on       │ depends on       │ depends on
       ▼                  ▼                  ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  DataProvider  │ │   Repository   │ │    Strategy    │
│   (abstract)   │ │   (abstract)   │ │   (abstract)   │
├────────────────┤ ├────────────────┤ ├────────────────┤
│ akshare  (✓)   │ │ sqlite   (✓)   │ │ technical  (✓) │
│ tushare  (todo)│ │ mysql    (cfg) │ │ fundamental(✓) │
│ baostock (todo)│ │ postgres (cfg) │ │ money_flow (✓) │
└────────────────┘ └────────────────┘ └────────────────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                         │ produce / consume
                         ▼
              ┌────────────────────────┐
              │   DTO Models           │
              │   models/              │
              │   Stock / Quote /      │
              │   KLine / Financial /  │
              │   MoneyFlow            │
              └────────────────────────┘
```

**核心设计模式**：依赖倒置（DIP）+ 注册表（Registry）+ 工厂（Factory）+ 插件化（Plugin）。

## Code Map

本节简要介绍各重要目录的职责。
请特别关注 **Architecture Invariant** 部分——它们描述了代码中**刻意不存在**的东西。

### `src/astock/models/` — 领域 DTO

纯数据类（`@dataclass`），跨层传递使用。无任何框架耦合、无行为方法（只允许轻量属性计算如 `Stock.symbol`、`KLine.latest`）。

- `stock.py` — `Stock` 基础信息 + `Board` 板块枚举
- `quote.py` — `Quote` 单日行情快照 + `KLine` 时间序列（内部用 DataFrame）
- `financial.py` — `Financial` 财务指标（PE/PB/ROE/营收同比/市值）
- `money_flow.py` — `MoneyFlow` 单日资金流向（主力/超大/大/中/小单）

**Architecture Invariant:**
- DTO 不依赖任何外部 I/O（数据源、存储、网络）
- DTO 不包含业务判断（"是否牛股"由策略层决定）
- DTO 字段变更是**破坏性变更**，需同步升级所有使用者

### `src/astock/datasource/` — 数据源抽象层

`DataProvider` 抽象接口 + 多种实现 + 注册表。详见 [`datasource/AGENTS.md`](src/astock/datasource/AGENTS.md)。

- `base.py` — `DataProvider` 抽象接口
- `registry.py` — `@register_provider` 装饰器 + `get_provider` 工厂
- `akshare_provider.py` — akshare 实现（默认）

**Architecture Invariant:**
- `engine/` 和 `strategy/` 只依赖 `DataProvider` 抽象类，不 import 任何具体 provider
- 数据源层**不直接写数据库**（写入由引擎调用 `Repository`）
- 数据源层**不做策略判断**（只拉取与格式化，返回 DTO）
- 具体 provider 的第三方库（akshare / tushare）使用**延迟 import**，未安装时不影响其他 provider

### `src/astock/storage/` — 存储抽象层

`Repository` 抽象接口 + SQLAlchemy 实现 + 注册表。详见 [`storage/AGENTS.md`](src/astock/storage/AGENTS.md)。

- `base.py` — `Repository` 抽象接口
- `registry.py` — `@register_repository` 装饰器 + `get_repository` 工厂
- `schema.py` — SQLAlchemy ORM（`StockORM / KLineORM / FinancialORM / MoneyFlowORM`）
- `sqlite_repo.py` — SQLite 实现（含分批 upsert）

**Architecture Invariant:**
- ORM 模型**仅存在于 `schema.py`**，禁止在 `*_repo.py` 里重复声明
- Repository 的 `get_*` 方法返回 `models/` 中的 DTO，**不暴露 ORM 实例**给上层
- 批量 upsert **必须分批**（SQLite 参数上限 32766），`_BATCH_SIZE = 800` 是硬性约束
- `klines` 与 `money_flows` 的 `(code, trade_date)` 组合唯一，重复写入走 upsert 而非 insert

### `src/astock/indicators/` — 技术指标计算

纯函数库（无状态），输入 `pandas.Series`，输出 `pandas.Series` 或 `bool`。

- `technical.py` — `ma / ema / macd / kdj / rsi / boll` + 形态判断 `is_ma_bull / is_macd_gold_cross / is_volume_burst`

**Architecture Invariant:**
- 所有指标函数是**纯函数**，无全局状态、无副作用
- 不依赖任何外部库除了 `pandas / numpy`（零 C 扩展依赖，跨平台运行）
- 形态判断函数数据不足时返回 `False`，不抛异常

### `src/astock/strategy/` — 选股策略插件层

`Strategy` 抽象接口 + 三种默认策略 + 注册表。详见 [`strategy/AGENTS.md`](src/astock/strategy/AGENTS.md)。

- `base.py` — `Strategy` 抽象接口 + `StrategyResult`
- `context.py` — `StrategyContext(stock, kline, financial, money_flows)`
- `registry.py` — `@register_strategy` 装饰器 + `get_strategy` 工厂
- `technical_strategy.py` / `fundamental_strategy.py` / `money_flow_strategy.py`

**Architecture Invariant:**
- 策略**只读 `StrategyContext`**，禁止直接调用 `DataProvider` 或 `Repository`（单一职责）
- 策略之间**无共享状态**，同一 `Strategy` 实例对不同股票的 `evaluate` 结果互不干扰
- 策略**不感知其它策略**，不访问 `engine` 模块
- 打分区间**强制 [0, 1]**，引擎做加权时假设此范围

### `src/astock/engine/` — 选股引擎

编排层，唯一允许组合 `DataProvider + Repository + Strategy` 的地方。

- `screener.py` — `ScreeningEngine.run()` 执行完整流水线：股票池 → 批量财务 → 逐只 K 线/资金流 → 策略评估 → 加权打分 → 排序

**Architecture Invariant:**
- `ScreeningEngine` 的依赖**全部通过构造函数注入**（便于 Mock 测试，见 `tests/test_e2e.py`）
- 引擎**不重复实现数据拉取逻辑**，全部走 provider
- 引擎**不自定义 ORM**，全部走 repository
- 引擎**不内嵌策略**，全部走注册表查找

### `src/astock/config/` — 配置加载

- `settings.py` — `Settings` dataclass + `load_settings(path)` 从 YAML 读取

**Architecture Invariant:**
- 配置是**只读**对象，运行期不修改
- 配置文件**必须幂等**（两次读取结果相同），不引用运行时状态

### `src/astock/output/` — 输出层

- `formatter.py` — `format_results`（控制台 rich 表格） + `save_results`（CSV / Excel / JSON）

**Architecture Invariant:**
- 输出层**只消费 `List[dict]`**，不回调引擎或策略
- 新增输出格式不应修改 `engine` 或 `strategy`

### `src/astock/cli.py` — CLI 入口

基于 `typer`。命令：`run` / `list-providers` / `list-storages` / `list-strategies`。

**Architecture Invariant:**
- CLI **不写业务逻辑**，所有动作委托给 `engine` / 注册表
- CLI 参数可**覆盖配置**（`--datasource / --storage / --output / --top-n / --limit`）

## Cross-Cutting Concerns

### 注册表与插件发现

三个独立注册表（`datasource._REGISTRY` / `storage._REGISTRY` / `strategy._REGISTRY`）各自维护。

**注册时机**：在每个模块的 `__init__.py` 末尾 `import` 具体实现文件，触发装饰器执行：

```python
# src/astock/datasource/__init__.py
from . import akshare_provider  # noqa: F401
```

**新增插件 = 新增文件 + 在 `__init__.py` 追加 import**，无需改其他代码。

### 重试与容错

- 网络调用：`tenacity` 的 `@retry(stop_after_attempt(3), wait_fixed(1))`，统一封装在 `AkshareProvider._call`
- 数据缺失：下游容错返回（`Financial(code=c)` 空占位 / `StrategyResult(passed=False)`），不抛未捕获异常
- 批量接口失败：有 fallback（`get_financials_batch` 失败时每只股票返回占位 `Financial`）

### 日志

- 统一 `logging.getLogger(__name__)`
- CLI 入口 `_setup_logging` 同时输出到控制台和文件（`data/logs/astock.log`）
- 关键路径日志级别：`INFO`（股票池过滤结果 / 批量接口成功）、`WARNING`（接口失败 / 回退）、`DEBUG`（单只股票拉取失败）

### 数据持久化周期

- `stocks` 表：每次 run 时全量 upsert（~5500 条）
- `klines` / `financials` / `money_flows`：每次 run 时按股票 upsert；历史数据累积保留
- 开发期清库：`rm -f data/astock.db`

### 测试策略

- **端到端 Mock 测试**：`tests/test_e2e.py` 使用 `MockProvider` + 内存 SQLite（`sqlite:///:memory:`）跑通完整引擎
- 真实数据源测试依赖外网（akshare），不进 CI
- 单元测试优先覆盖指标计算（纯函数易测）和策略评估（注入 `StrategyContext` 即可）

## 扩展方向（非当前实现）

以下内容**刻意不在当前代码中**，但架构已预留扩展点：

- **回测引擎**：独立 `backtest/` 模块，消费 `Repository` 中的历史 K 线
- **定时调度 + 推送**：在 `cli.py` 外层加 cron / APScheduler；推送通过新增 `output/notifier.py`
- **Web 服务**：基于 FastAPI 封装 `ScreeningEngine`，与 CLI 并列
- **因子 IC/IR 分析**：新增 `analytics/` 模块，复用 `indicators/`

任何扩展都应**遵守现有的接口边界**，不破坏上述 Architecture Invariant。
