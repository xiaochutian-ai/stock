# AGENTS.md — src/astock/storage/ 存储抽象层

> 本文件是 `src/astock/storage/` 模块的本地入口。
> 仓库总入口见 `../../../AGENTS.md`，架构边界见 `../../../ARCHITECTURE.md`。

## 模块定位

面向接口的持久化适配层：**上层不感知具体数据库**，通过 `Repository` 抽象接口统一访问。默认基于 SQLAlchemy 的 SQLite 实现；切换到 MySQL / PostgreSQL 只需修改配置 `storage.options.url`（或新增独立 Repository 实现以利用方言特性）。

## 知识导航

| 我要做什么 | 去哪里看 |
|---|---|
| 理解存储接口契约 | `base.py` 的 `Repository` 抽象类 |
| 看表结构 / ORM 定义 | `schema.py`（4 张表：stocks / klines / financials / money_flows） |
| 新增一种存储后端 | 参考 `sqlite_repo.py`，继承 `Repository` 并用 `@register_repository("name")` 注册 |
| 切换到 MySQL | 修改 `config/default.yaml` 的 `storage.options.url`（SQLAlchemy 方言） |
| 诊断批量写入性能 | 查看 `sqlite_repo.py` 的 `_bulk_upsert` 方法（按 800 行分批） |
| 查看当前可用存储 | 运行 `astock list-storages` |

## 目录结构

```text
storage/
├── __init__.py              # 对外导出 + 触发实现类注册
├── base.py                  # Repository 抽象接口（契约）
├── registry.py              # 全局注册表 + get_repository 工厂
├── schema.py                # SQLAlchemy ORM 表结构（跨方言通用）
└── sqlite_repo.py           # SQLite/SQLAlchemy 默认实现（含分批 upsert）
```

## 本地约束

- **所有存储实现必须继承 `Repository`**，并通过 `@register_repository("name")` 装饰器注册
- **必须在 `init_schema()` 中幂等建表**，不得依赖使用方先建表
- **批量写入必须分批**：SQLite 单 SQL 绑定参数上限 32766，`_bulk_upsert` 默认 800 行/批，新增存储实现也必须遵守分批原则
- **Upsert 语义必须实现**：同一 PK 再次写入应更新，不得产生重复记录或抛约束异常；参考 `sqlite_repo.py` 使用 `ON CONFLICT DO UPDATE`
- **ORM 模型唯一来源**：所有后端共用 `schema.py` 中的 ORM 定义，禁止在具体 Repository 里重复声明字段
- **读取返回 DTO**：`list_stocks / get_kline / get_financial / get_money_flows` 返回 `models/` 中的 DTO，不得暴露 ORM 实例给上层
- **不跨库写**：一次 `session` 内只操作同一 engine；跨后端迁移走离线脚本

## 常用命令

```bash
# 查看已注册存储后端
astock list-storages

# 清库重建（开发期）
rm -f data/astock.db && astock run --limit 10

# 直接查看 SQLite 数据
sqlite3 data/astock.db "SELECT COUNT(*) FROM stocks;"
sqlite3 data/astock.db ".tables"
```

## 关键文件

- `base.py` — `Repository` 抽象接口，定义 `init_schema / close / upsert_* / get_* / list_*` 十余个方法
- `schema.py` — `StockORM / KLineORM / FinancialORM / MoneyFlowORM` 四个 ORM 类，`klines` 和 `money_flows` 有 `(code, trade_date)` 唯一索引
- `sqlite_repo.py` — `_bulk_upsert` 统一分批与方言分支逻辑，`_BATCH_SIZE = 800`

## 进一步阅读

- 架构不变量（存储层刻意边界）：`../../../ARCHITECTURE.md`
- 数据源如何产生写入数据：`../datasource/AGENTS.md`
- 引擎如何编排 upsert 调用：`../engine/screener.py`
