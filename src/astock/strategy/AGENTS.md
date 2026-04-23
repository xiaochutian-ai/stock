# AGENTS.md — src/astock/strategy/ 选股策略插件层

> 本文件是 `src/astock/strategy/` 模块的本地入口。
> 仓库总入口见 `../../../AGENTS.md`，架构边界见 `../../../ARCHITECTURE.md`。

## 模块定位

可插拔的选股策略层：每个策略独立实现 `Strategy` 接口，通过 `@register_strategy("name")` 装饰器注册；引擎根据配置文件动态组合多策略，对每只股票产出加权综合得分。**新增一个策略 = 新增一个文件，不修改任何现有代码**（OCP 原则）。

## 知识导航

| 我要做什么 | 去哪里看 |
|---|---|
| 理解策略接口契约 | `base.py` 的 `Strategy` 抽象类 + `StrategyResult` |
| 理解策略如何拿到数据 | `context.py` 的 `StrategyContext`（引擎统一组装） |
| 新增一种选股策略 | 参考 `technical_strategy.py`，继承 `Strategy` 并用 `@register_strategy("name")` 注册 |
| 查看当前可用策略 | 运行 `astock list-strategies`，或看 `__init__.py` 末尾的 `import` |
| 调整策略参数 | 改 `config/default.yaml` 的 `strategies.*.params`，不改代码 |
| 理解多因子打分规则 | `../engine/screener.py` 的 `_evaluate_one` 方法 |

## 目录结构

```text
strategy/
├── __init__.py                  # 对外导出 + 触发实现类注册
├── base.py                      # Strategy 抽象接口 + StrategyResult
├── context.py                   # StrategyContext 执行上下文
├── registry.py                  # 全局注册表 + get_strategy 工厂
├── technical_strategy.py        # 技术面策略（MA/MACD/RSI/放量）
├── fundamental_strategy.py      # 基本面策略（PE/PB/ROE/净利润同比）
└── money_flow_strategy.py       # 资金面策略（主力连续净流入）
```

## 本地约束

- **策略只读 context，不拉数据**：策略禁止直接调用 `DataProvider` 或 `Repository`；所需数据由引擎统一注入 `StrategyContext`（单一职责）
- **返回值统一为 `StrategyResult`**：包含 `passed`、`score (0~1)`、`reason`、`details` 四项，缺一不可
- **缺失数据必须容错**：`ctx.kline / financial / money_flows` 可能为 `None` / 空，策略必须返回 `StrategyResult(passed=False, reason="缺少X数据")` 而不是抛异常
- **enabled=0 时视为全通过**：若所有子因子都未启用（配置裁剪到空），返回 `StrategyResult(passed=True, score=1.0)`，避免零分歧义
- **打分区间强制 [0, 1]**：不得返回负分或超过 1.0 的分数（引擎假设此范围做加权）
- **参数从 `self.params` 读**：构造时 `params: dict` 已注入，禁止在 `evaluate` 里再读配置文件或环境变量
- **策略之间不共享状态**：策略实例在整次 run 中复用，但不应依赖上一次 `evaluate` 的结果

## 常用命令

```bash
# 查看已注册策略
astock list-strategies

# 只启用某一种策略跑通（临时调试，在配置文件里把其它 enabled 设为 false）
astock run -c config/tech_only.yaml --limit 50
```

## 关键文件

- `base.py` — `Strategy.evaluate(ctx: StrategyContext) -> StrategyResult`
- `context.py` — `StrategyContext(stock, kline, financial, money_flows)`
- `technical_strategy.py` — 使用 `../indicators/technical.py` 中的 `is_ma_bull / is_macd_gold_cross / rsi` 等工具函数
- `fundamental_strategy.py` — 只依赖 `ctx.financial`，所有因子可按参数开关单独启用
- `money_flow_strategy.py` — 按 `main_inflow_days` 参数要求最近 N 日连续主力净流入

## 打分与硬门槛

- 综合得分：`total_score = Σ(weight_i * score_i) / Σ(weight_i)`
- 入选门槛：`any_passed=True` **且** `total_score >= output.min_score`（默认 0.5）
- 门槛调整：修改 `config/default.yaml` 的 `output.min_score`

## 进一步阅读

- 架构不变量（策略层刻意边界）：`../../../ARCHITECTURE.md`
- 引擎如何组装与执行策略：`../engine/screener.py`
- 技术指标函数：`../indicators/technical.py`
