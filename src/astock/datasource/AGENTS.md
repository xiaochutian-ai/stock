# AGENTS.md — src/astock/datasource/ 数据源抽象层

> 本文件是 `src/astock/datasource/` 模块的本地入口。
> 仓库总入口见 `../../../AGENTS.md`，架构边界见 `../../../ARCHITECTURE.md`。

## 模块定位

面向接口的 A 股数据源适配层：**上层不感知具体数据源**，通过 `DataProvider` 抽象接口统一访问。切换数据源仅需修改配置文件 `datasource.name`，无需改动策略或引擎代码。

## 知识导航

| 我要做什么 | 去哪里看 |
|---|---|
| 理解数据源接口契约 | `base.py` 的 `DataProvider` 抽象类 |
| 新增一种数据源 | 参考 `akshare_provider.py`，继承 `DataProvider` 并用 `@register_provider("name")` 注册 |
| 查看当前可用数据源 | 运行 `astock list-providers`，或看 `__init__.py` 末尾的 `import` |
| 调试 akshare 接口调用 | `akshare_provider.py` 的 `_call` 方法（含重试） |
| 添加 tushare/baostock 支持 | 新建 `tushare_provider.py` 并安装 `pip install -e ".[tushare]"` |

## 目录结构

```text
datasource/
├── __init__.py              # 对外导出 + 触发实现类注册
├── base.py                  # DataProvider 抽象接口（契约）
├── registry.py              # 全局注册表 + get_provider 工厂
└── akshare_provider.py      # akshare 实现（默认数据源，无需 token）
```

## 本地约束

- **所有数据源实现必须继承 `DataProvider`**，并通过 `@register_provider("name")` 装饰器注册，不得绕过注册表直接实例化
- **数据源层只负责拉取与格式化**，不落库、不做业务判断（落库由 `storage/`，业务判断由 `strategy/`）
- **返回值必须使用 `models/` 中的 DTO**（Stock / KLine / Financial / MoneyFlow），禁止返回未封装的原始 DataFrame 给策略层
- **网络调用必须有重试与超时**，参考 `AkshareProvider._call` 使用 `tenacity`；失败返回 `None` 或空列表，不得抛未捕获的异常打断全流程
- **批量接口优先**：如果数据源本身提供批量能力，必须重写 `get_financials_batch` 等批量方法，避免 N+1 拉取（参考 `AkshareProvider.get_financials_batch` 使用 `stock_zh_a_spot_em`）
- **字段命名英文化**：akshare 等返回的中文列名必须在实现内部映射为英文（`open/high/low/close/volume/...`），DTO 对外保持英文字段

## 常用命令

```bash
# 查看已注册数据源
astock list-providers

# 冒烟测试某个数据源（仅评估前 5 只股票）
astock run --datasource akshare --limit 5 --log-level DEBUG
```

## 关键文件

- `base.py` — 定义 `list_stocks / get_kline / get_financial / get_financials_batch / get_money_flow` 五个必须实现的抽象方法
- `registry.py` — `_REGISTRY` 全局字典 + `register_provider` 装饰器
- `akshare_provider.py` — 基于 akshare 的完整实现，含重试、中文列映射、市场前缀推断

## 进一步阅读

- 架构不变量（数据源层的刻意边界）：`../../../ARCHITECTURE.md`
- 策略层如何消费数据：`../strategy/AGENTS.md`
- 数据模型定义：`../models/`
