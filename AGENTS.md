# AGENTS.md — 仓库文档总入口

> **本文件是 astock 仓库的总路由，不是百科全书。**
> Agent 默认从这里开始；人类读者可先看 `README.md`，再回到这里继续下钻。

- 本仓库默认使用**中文**进行文档撰写；代码标识符、路径、命令、类型名保留英文

---

## 如何使用本文件

- Agent：先读本文件，确定要进入哪个模块入口或专题文档
- 人类读者：先读 `README.md` 了解项目，再用本文件找模块入口
- 需要代码结构和边界：读 `ARCHITECTURE.md`
- 需要各模块的本地规则：进入对应模块 `AGENTS.md`

---

## 项目简介

**astock** 是一个面向 A 股市场的选股系统，基于 Python 3.9+，核心诉求是**可插拔**：

- **数据源** 面向接口编程（`DataProvider`），默认 akshare，可替换 tushare / baostock
- **存储层** 面向接口编程（`Repository`），默认 SQLite/SQLAlchemy，可替换 MySQL / PostgreSQL
- **策略层** 插件化（`Strategy` + 注册表），当前内置技术面 / 基本面 / 资金面三类
- **交付形态** 当前为 CLI（`astock run`），未来可按需扩展 Web / 定时推送

当前仓库的核心资产：

| 模块 | 路径 | 作用 |
|---|---|---|
| 数据源 | `src/astock/datasource/` | `DataProvider` 抽象 + akshare 实现 |
| 存储 | `src/astock/storage/` | `Repository` 抽象 + SQLite 实现 |
| 策略 | `src/astock/strategy/` | `Strategy` 抽象 + 三类默认策略 |
| 指标 | `src/astock/indicators/` | 纯函数技术指标（MA/MACD/KDJ/RSI/BOLL） |
| 模型 | `src/astock/models/` | DTO（Stock/Quote/KLine/Financial/MoneyFlow） |
| 引擎 | `src/astock/engine/` | `ScreeningEngine` 编排流水线 |
| 配置 | `src/astock/config/` | YAML 配置加载 |
| 输出 | `src/astock/output/` | 控制台 / CSV / Excel / JSON |
| CLI | `src/astock/cli.py` | typer 命令行入口 |

---

## 文档体系

| 层级 | 入口 | 作用 |
|---|---|---|
| L0 总入口 | `AGENTS.md` | 仓库任务路由、协作约束、阅读顺序 |
| L0 人类入口 | `README.md` | 项目介绍、快速开始 |
| L0 架构入口 | `ARCHITECTURE.md` | 代码地图、模块边界、不变量 |
| L0 发版记录 | `CHANGELOG.md` | 每次 release 的新增/变更/修复，遵循 SemVer + Keep a Changelog |
| L2 数据源模块 | `src/astock/datasource/AGENTS.md` | 数据源接口与实现约束 |
| L2 存储模块 | `src/astock/storage/AGENTS.md` | 存储接口与 Upsert 约束 |
| L2 策略模块 | `src/astock/strategy/AGENTS.md` | 策略接口与打分规则 |

---

## 知识导航（Progressive Disclosure）

根据你要做的事，按需查阅：

| 我要做什么 | 去哪里看 |
|---|---|
| 第一次进入仓库、了解项目是什么 | `README.md` |
| 理解整体架构与模块边界 | `ARCHITECTURE.md` |
| 运行选股流程 / CLI 使用说明 | `README.md` 的"快速开始"章节 + `src/astock/cli.py` |
| 新增数据源（tushare/baostock 等） | `src/astock/datasource/AGENTS.md` |
| 切换 / 新增存储后端（MySQL/PG） | `src/astock/storage/AGENTS.md` |
| 新增选股策略 | `src/astock/strategy/AGENTS.md` |
| 调整选股参数（不改代码） | `config/default.yaml` |
| 增加技术指标 | `src/astock/indicators/technical.py` |
| 理解 Engine 如何编排流水线 | `src/astock/engine/screener.py` |
| 端到端 Mock 测试（无需联网） | `tests/test_e2e.py` |
| 查看历次版本变更 / 发版记录 | `CHANGELOG.md` |

---

## 核心约束（所有 Agent 必须遵守）

### 架构边界

- **面向抽象编程**：`engine/` 与 `strategy/` 只依赖 `DataProvider` / `Repository` 抽象接口，禁止 import 任何具体 `*_provider.py` / `*_repo.py`
- **注册表强制**：新增数据源/存储/策略必须通过 `@register_*` 装饰器注册；禁止在外部代码绕过注册表直接 `new` 具体类
- **DTO 穿层**：跨模块传递数据统一使用 `src/astock/models/` 中的 DTO；禁止暴露 ORM 实例或未封装的 DataFrame 给策略层
- **职责边界**：
  - 数据源层：只拉取与格式化，不落库、不做策略判断
  - 存储层：只做持久化，不感知业务语义
  - 策略层：只读 `StrategyContext`，不直接调数据源/存储

### 代码质量

- **Python 版本**：项目目标 `py39`，新代码必须兼容 3.9+（`from __future__ import annotations` 已在多数文件启用）
- **Lint 规则**：`ruff` 已在 `pyproject.toml` 声明（line-length=100）；提交前应通过 `ruff check src/ tests/`
- **异常处理**：网络调用必须用 `tenacity` 重试；数据缺失走容错返回（`None` / 空列表 / `passed=False`），不得抛未捕获异常打断全流程
- **批量写入**：写 SQLite 必须走 `_bulk_upsert` 的分批逻辑（`_BATCH_SIZE = 800`），不得对全量数据一次性 `INSERT`

### 测试约束

- 端到端测试入口：`python3 tests/test_e2e.py`（使用 `MockProvider` + 内存 SQLite，不依赖外网）
- 新增策略或修改打分逻辑时，必须更新 / 新增对应测试用例
- 任何"测试通过"声明必须附带实际运行输出

### 配置与数据

- 所有可调参数优先走 `config/default.yaml`，禁止硬编码在策略或引擎代码中
- 用户本地配置请新建 `config/local.yaml`（已在 `.gitignore`），不要覆盖 `default.yaml`
- 数据目录 `data/`（SQLite、缓存、日志、输出）已 `.gitignore`，不进版本库

---

## 代码质量回压（Backpressure）

**当前状态**：仓库暂未启用 pre-commit hook。Agent 在贡献代码前应**手动**执行以下命令：

```bash
# Lint
ruff check src/ tests/

# 端到端自测
python3 tests/test_e2e.py
```

**建议后续启用**的 pre-commit 检查（未安装，仅建议）：

| 检查项 | 工具 | 作用 |
|---|---|---|
| 代码格式与规范 | `ruff check` + `ruff format` | Python 风格、导入顺序、未使用变量 |
| 类型检查 | `mypy src/` | 可选，按模块逐步开启 |
| 文件行数 | 自定义脚本 | 单文件 ≤ 600 行 |
| 通用卫生 | `trailing-whitespace` / `end-of-file-fixer` / `check-yaml` | 标准 pre-commit-hooks |
| 密钥扫描 | `detect-secrets` | 防止 tushare token 等进库 |

启用方式：新建 `.pre-commit-config.yaml` 并 `pre-commit install`。
