# CHANGELOG — astock Release 记录

> 本文件记录 `astock` 每一次对外可见的版本变化。
> 人类读者先看 [`README.md`](./README.md)，Agent 先看 [`AGENTS.md`](./AGENTS.md)；
> 发版信息（新功能、破坏性变更、修复）汇总于此。

## 规范

- 版本遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)：`MAJOR.MINOR.PATCH`
  - `MAJOR`：不兼容的接口变更（`DataProvider` / `Repository` / `Strategy` 契约）
  - `MINOR`：向后兼容的新功能（新增数据源、新增策略、新增配置项）
  - `PATCH`：向后兼容的修复（bug fix、文档、性能）
- 版本号与 [`pyproject.toml`](./pyproject.toml) 的 `project.version` 保持一致
- 格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
- 条目分类：`Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security` / `Docs` / `Infra`
- 最新版本放在文件最上方；未发布的改动挂在 `[Unreleased]` 段

---

## [Unreleased]

（当前无未发布改动）

---

## [0.1.0] — 2026-04-23

首个对外可用版本：**面向接口的 A 股选股系统**（CLI 交付形态）。

### 🎯 核心价值

- **可插拔架构**：数据源 / 存储 / 策略均面向接口编程，配置驱动切换，符合 OCP（开放封闭）原则
- **零 token 启动**：默认数据源 akshare，首次运行无需申请任何 API key
- **端到端可用**：内置 3 类默认策略 + 多因子加权打分，`astock run` 即可获得选股结果

### Added — 新增

#### 架构骨架
- 三条插件化接口及其注册表 + 工厂方法
  - `DataProvider` / `@register_provider` / `get_provider` — `src/astock/datasource/`
  - `Repository` / `@register_repository` / `get_repository` — `src/astock/storage/`
  - `Strategy` / `@register_strategy` / `get_strategy` — `src/astock/strategy/`
- 领域 DTO 层：`Stock` / `Board` / `Quote` / `KLine` / `Financial` / `MoneyFlow`（纯 dataclass）
- 选股引擎 `ScreeningEngine`（`src/astock/engine/screener.py`），按 "股票池 → 批量财务 → 逐只 K 线/资金流 → 策略评估 → 加权排序" 流水线编排
- `StrategyContext` 跨层上下文，策略层只读 context，不直接访问数据源/存储

#### 数据源
- **akshare 默认实现** `AkshareProvider`（无 token，免费）：
  - 全市场股票列表（`stock_info_a_code_name`）
  - 日 K 线（`stock_zh_a_hist`，支持前复权/后复权）
  - **批量财务指标**（`stock_zh_a_spot_em` 一次性快照，比 N+1 查询快 100+ 倍）
  - 个股资金流向（`stock_individual_fund_flow`）
  - 基于 `tenacity` 的重试封装 `_call`（默认 3 次 + 1s 固定间隔）
  - 中文列名自动映射为英文（`开盘/收盘/... → open/close/...`）
- 可选扩展位：`[tushare]` / `[baostock]` 预留 extras（按需安装）

#### 存储
- **SQLite 默认实现** `SQLiteRepository`（基于 SQLAlchemy 2.0）：
  - 4 张表：`stocks / klines / financials / money_flows`（`schema.py` 统一 ORM）
  - `ON CONFLICT DO UPDATE` 语义的 upsert
  - 分批写入 `_BATCH_SIZE = 800`，规避 SQLite 32766 绑定参数上限
  - 跨方言回退：非 SQLite 走 `sess.merge()`
- 切换到 MySQL / PostgreSQL 只需改 `storage.options.url`（无需改代码）

#### 策略
- `TechnicalStrategy`（`technical`）：均线多头 / MACD 金叉 / RSI 区间 / 放量
- `FundamentalStrategy`（`fundamental`）：PE / PB / ROE / 净利润同比
- `MoneyFlowStrategy`（`money_flow`）：最近 N 日主力净流入 / 单日最小净流入门槛
- 所有策略返回统一的 `StrategyResult(passed, score∈[0,1], reason, details)`
- 多因子综合打分：`total_score = Σ(weight_i × score_i) / Σ(weight_i)`
- 入选门槛：`any_passed=True AND total_score >= output.min_score`（默认 0.5）

#### 指标
- 纯 pandas 实现（零 C 扩展依赖）：`ma / ema / macd / rsi / kdj / boll`
- 形态判断：`is_ma_bull / is_macd_gold_cross / is_volume_burst`

#### CLI
- `astock run` — 执行选股（支持 `--config/--datasource/--storage/--output/--top-n/--limit/--kline-days/--save`）
- `astock list-providers` — 列出已注册数据源
- `astock list-storages` — 列出已注册存储后端
- `astock list-strategies` — 列出已注册策略

#### 输出
- 控制台（rich Table）、CSV、Excel（openpyxl）、JSON 四种输出格式

#### 配置
- `config/default.yaml` 统一管理：数据源 / 存储 / 策略组合与权重 / 市场过滤 / 输出
- 用户本地覆盖走 `config/local.yaml`（已在 `.gitignore`）

#### 测试
- `tests/test_e2e.py`：基于 `MockProvider` + 内存 SQLite 的端到端测试，零网络依赖

### Docs — 文档

- 建立 Harness 风格的分层文档体系：
  - L0：[`AGENTS.md`](./AGENTS.md) / [`README.md`](./README.md) / [`ARCHITECTURE.md`](./ARCHITECTURE.md)
  - L2：`src/astock/{datasource,storage,strategy}/AGENTS.md` 三份模块级入口
- 架构不变量（Architecture Invariants）明示刻意边界：
  - engine / strategy 只依赖抽象接口，禁止 import 具体 `*_provider.py` / `*_repo.py`
  - 所有插件必须通过 `@register_*` 装饰器注册
  - 跨模块传递统一走 `models/` 中的 DTO

### Infra — 工程基建

- `pyproject.toml`：setuptools 构建，ruff 配置（`line-length=100`, `target-version=py39`），extras 分组（tushare / baostock / dev）
- `.gitignore`：`data/`、`config/local.yaml`、`__pycache__/`、`.venv/` 等均已忽略
- Python 最低版本 3.9（所有模块启用 `from __future__ import annotations`）

### Known Limitations — 已知限制

- 仅支持日线级别；分钟线 / tick 数据尚未覆盖
- akshare 批量财务快照仅含 PE/PB/市值；ROE / 营收增速等需单只拉取，当前 `FundamentalStrategy` 在这些字段缺失时会降级为"未命中"
- 尚未引入 pre-commit hook（`ruff check` / `python3 tests/test_e2e.py` 需手动执行）
- 未提供 Web UI / 定时推送

### Verification — 发版前验证

- ✅ `ruff check src/ tests/` 全部通过
- ✅ `python3 tests/test_e2e.py` 端到端测试通过（`MockProvider` + 内存 SQLite，选出 5 只，Top 1/2 为 `600519` / `300750`）
- ✅ 真实环境联调：akshare 拉取全市场 5508 只股票、530 条 K 线、20 条财务、100 条资金流落库成功

### Upgrade Notes — 升级说明

首次发布，无升级路径。后续版本的破坏性变更将在此处给出迁移指引。

---

[Unreleased]: #unreleased
[0.1.0]: #010--2026-04-23
