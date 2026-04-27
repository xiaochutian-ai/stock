# A股大盘走势多层打分框架设计

## 背景

目标是在仓库中新增一个可复用的大盘走势打分框架，并提供一个可直接运行的演示脚本。

该框架采用三层结构：

- 底层技术因子：从指数行情和市场宽度原始数据中提取细粒度信号
- 聚合因子：将多个底层技术因子聚合为趋势、成交量、宽度等中层因子
- 策略层：对多个聚合因子进行加权，输出总分、市场状态和解释

这样设计的原因：

- 符合“技术因子 -> 聚合因子 -> 量化策略”的分层方式
- 便于后续继续扩展更多聚合因子与策略模板
- 不直接耦合现有 `ScreeningEngine` 和个股 `strategy/`，避免边界混淆

## 范围

本次实现包含：

- 一个新的分析模块：`src/astock/analytics/market_scoring.py`
- 一个新的分析子包：`src/astock/analytics/__init__.py`
- 一个可执行演示脚本：`scripts/market_score_demo.py`
- 一组 focused tests：`tests/test_market_scoring.py`

本次实现不包含：

- 实时行情抓取
- 接入现有 CLI 主命令
- 接入数据库
- 接入现有选股策略注册表
- 回测与参数寻优

## 文件位置

- `src/astock/analytics/__init__.py`
  - 分析子包入口
- `src/astock/analytics/market_scoring.py`
  - 大盘走势多层打分框架主实现
- `scripts/market_score_demo.py`
  - 内置样例数据的演示脚本
- `tests/test_market_scoring.py`
  - 框架与演示输出的测试

## 分层设计

### 1. 底层技术因子

底层技术因子只做“单一可解释信号”的计算，不负责最终决策。

输入：

- 指数收盘价序列
- 指数成交量序列
- 市场宽度快照序列

输出示例：

- `close_above_ma20`
- `ma20_above_ma60`
- `momentum_20d`
- `volume_ratio_20d`
- `advancers_ratio`
- `new_high_ratio`
- `above_ma20_ratio`

设计原则：

- 每个因子单独命名
- 因子值和因子分数分离
- 数据不足时优先返回中性结果，不抛未捕获异常

### 2. 聚合因子

聚合因子将多个底层技术因子汇总为可直接解释的中层信号。

本次实现三个聚合因子：

- `trend`
- `volume`
- `breadth`

聚合规则：

- 每个聚合因子由多个底层因子加权组成
- 聚合因子输出 `0-100` 分
- 聚合因子同时保留底层因子明细，便于解释

### 3. 策略层

策略层消费聚合因子，不直接处理原始行情。

本次实现一个默认市场状态策略：

- `MarketRegimeStrategy`

职责：

- 对 `trend`、`volume`、`breadth` 进行加权汇总
- 输出总分
- 输出市场状态标签
- 输出简洁解释

默认标签：

- `强势`
- `震荡`
- `弱势`

## 数据模型

### 输入模型

- `MarketBar`
  - `trade_date`
  - `close`
  - `volume`
- `BreadthSnapshot`
  - `trade_date`
  - `advancers`
  - `decliners`
  - `new_highs`
  - `new_lows`
  - `stocks_above_ma20`
  - `total_stocks`
- `MarketDataset`
  - `bars`
  - `breadth`

### 输出模型

- `FactorValue`
  - `name`
  - `value`
  - `score`
  - `comment`
- `CompositeFactorResult`
  - `name`
  - `score`
  - `factors`
  - `comment`
- `MarketScoreResult`
  - `trend`
  - `volume`
  - `breadth`
  - `total_score`
  - `regime`
  - `summary`

## 量化规则

### 底层技术因子

#### 趋势类

- `close_above_ma20`
  - 最近收盘价高于 MA20 记为强信号
- `ma20_above_ma60`
  - MA20 高于 MA60 记为中期趋势偏强
- `momentum_20d`
  - 20 日动量为 `(latest_close / close_20d_ago - 1)`

#### 成交量类

- `volume_ratio_20d`
  - 最近成交量 / 20 日平均成交量
- `up_day_volume_ratio`
  - 最近 10 日上涨日成交量 / 最近 10 日全部成交量

#### 宽度类

- `advancers_ratio`
  - 上涨家数 / 总家数
- `new_high_ratio`
  - 创新高家数 / (创新高家数 + 创新低家数)
- `above_ma20_ratio`
  - 站上 MA20 个股数 / 总家数

### 聚合因子得分

#### 趋势

使用三个底层因子：

- `close_above_ma20`
- `ma20_above_ma60`
- `momentum_20d`

默认权重：

- `0.35 / 0.35 / 0.30`

#### 成交量

使用两个底层因子：

- `volume_ratio_20d`
- `up_day_volume_ratio`

默认权重：

- `0.50 / 0.50`

#### 宽度

使用三个底层因子：

- `advancers_ratio`
- `new_high_ratio`
- `above_ma20_ratio`

默认权重：

- `0.40 / 0.25 / 0.35`

### 策略层得分

默认总分公式：

```text
total_score =
    trend.score * 0.40 +
    volume.score * 0.25 +
    breadth.score * 0.35
```

总分输出为 `0-100`。

市场标签：

- `>= 70`：`强势`
- `40 <= score < 70`：`震荡`
- `< 40`：`弱势`

## 容错与错误处理

- 指数样本为空时抛出 `ValueError`
- 宽度样本为空时抛出 `ValueError`
- 最近日期找不到对应宽度快照时抛出 `ValueError`
- 因子需要的窗口长度不足时，返回中性值：
  - 布尔/结构信号按 `0.5` 折算
  - 比例信号缺数据时记为 `0.5`
- 所有打分统一裁剪到 `0-100`
- 分母为 0 时返回 `0.5` 或 `0.0` 的安全值，避免崩溃

## 演示脚本

脚本 `scripts/market_score_demo.py` 应：

- 构造一组带趋势、量能、宽度变化的样例市场数据
- 调用 `MarketRegimeStrategy`
- 打印：
  - 趋势分
  - 成交量分
  - 宽度分
  - 总分
  - 市场状态
  - 分项解释

运行方式：

```bash
python3 scripts/market_score_demo.py
```

## 测试策略

测试覆盖以下场景：

- 趋势、量能、宽度分项可计算
- 强市场样例输出 `强势`
- 弱市场样例输出 `弱势`
- 数据不足时不报错，并回落到中性得分
- 缺失关键输入时按预期抛出异常
- 演示脚本 `main()` 可正常运行并输出核心字段

## 非目标

- 本框架是结构化演示与后续扩展基础，不构成投资建议
- 本次不做交易信号买卖点细化
- 本次不做回测胜率验证
- 本次不尝试替代现有个股打分策略体系
