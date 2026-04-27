# A股短线选股独立打分脚本设计

## 背景

目标是提供一个独立、可直接运行的 Python 脚本，用内置示例数据演示 A 股短线选股的五维打分模型，并输出多只股票的排序结果与候选榜单，方便本地快速验证评分逻辑。

该脚本不直接接入现有 `ScreeningEngine`，而是保持为单文件演示工具，优先满足以下要求：

- 开箱即跑
- 不依赖第三方库
- 输出清晰可读
- 后续容易迁移到现有项目结构中

## 范围

本次仅实现一个独立脚本，包含：

- 市场环境、板块强度、个股趋势、资金成交、风险结构五个维度的量化评分
- 1 组市场示例数据
- 3 个板块示例数据
- 6 只股票示例数据
- 候选榜单排序输出
- Top 3 个股的详细分项解释

本次不包含：

- 实时行情抓取
- 外部 JSON/CSV 输入
- 写入数据库
- 接入 CLI 主命令
- 自动化测试新增

## 文件位置

建议脚本路径：

- `scripts/short_term_rank_demo.py`

选择该路径的原因：

- 与主业务代码解耦，不影响现有引擎
- 便于用户直接运行验证
- 后续如果需要迁移，可将打分逻辑拆到 `src/astock/strategy/` 或 `src/astock/engine/` 下

## 核心设计

脚本采用轻量数据类 + 打分器的结构：

- `MarketSnapshot`：描述当天市场环境
- `SectorSnapshot`：描述某个板块的强弱与热度
- `StockCandidate`：描述候选个股的量价、趋势、风险特征
- `ScoreBreakdown`：保存每只股票的五维分项分数、总分、标签与理由
- `ShortTermScorer`：封装五个维度的打分逻辑和总分汇总逻辑

## 输入字段

### MarketSnapshot

- `index_above_ma5: bool`
- `index_above_ma10: bool`
- `advancers_ratio: float`
- `limit_up_count: int`
- `limit_down_count: int`
- `strong_stock_premium: float`

### SectorSnapshot

- `name: str`
- `change_1d_rank_pct: float`
- `change_3d_rank_pct: float`
- `up_stock_ratio: float`
- `limit_up_count: int`
- `has_catalyst: bool`

### StockCandidate

- `code: str`
- `name: str`
- `sector: str`
- `price_change_5d: float`
- `sector_change_5d: float`
- `above_ma5: bool`
- `above_ma10: bool`
- `above_ma20: bool`
- `ma_bullish: bool`
- `breakout: bool`
- `close_near_high: bool`
- `volume_ratio: float`
- `volume_vs_avg5: float`
- `turnover_rate: float`
- `amount_billion: float`
- `capital_inflow_positive: bool`
- `tail_strength: bool`
- `distance_to_support_pct: float`
- `is_accelerating_high: bool`
- `overhead_pressure_low: bool`
- `event_risk_low: bool`
- `reward_risk_ratio: float`

## 量化规则

### 1. 市场环境

权重：`20%`

满分：`100`

规则：

- 站上 5 日线：`+20`
- 站上 10 日线：`+20`
- 上涨家数占比 `>= 0.60`：`+20`
- 涨停家数 `>= 70` 且跌停家数 `<= 10`：`+20`
- 强势股平均溢价 `>= 2%`：`+20`

说明：

- 该分数为当天公共背景，对所有个股共享

### 2. 板块强度

权重：`25%`

满分：`100`

规则：

- 1 日涨幅排名前 10%：`+25`
- 3 日涨幅排名前 10%：`+25`
- 板块涨停数 `>= 2`：`+20`
- 板块上涨家数占比 `>= 0.70`：`+15`
- 有催化：`+15`

### 3. 个股趋势

权重：`25%`

满分：`100`

规则：

- `price_change_5d - sector_change_5d >= 5`：`+25`
- 同时站上 `MA5/MA10/MA20`：`+20`
- `ma_bullish` 为真：`+20`
- `breakout` 为真：`+20`
- `close_near_high` 为真：`+15`

### 4. 资金成交

权重：`20%`

满分：`100`

规则：

- `volume_ratio >= 1.5`：`+20`
- `volume_vs_avg5 >= 1.5`：`+25`
- `8 <= turnover_rate <= 25`：`+20`
- `10 <= amount_billion <= 80`：`+20`
- `capital_inflow_positive` 且 `tail_strength` 为真：`+15`

### 5. 风险结构

权重：`10%`

满分：`100`

规则：

- `distance_to_support_pct <= 5`：`+30`
- `is_accelerating_high` 为假：`+20`
- `overhead_pressure_low` 为真：`+20`
- `event_risk_low` 为真：`+15`
- `reward_risk_ratio >= 2.0`：`+15`

## 总分公式

```text
total_score =
    market_score * 0.20 +
    sector_score * 0.25 +
    trend_score * 0.25 +
    flow_score * 0.20 +
    risk_score * 0.10
```

输出总分保留两位小数。

## 排名标签

- `>= 80`：`重点关注`
- `70 <= score < 80`：`观察池`
- `< 70`：`暂不推荐`

## 输出设计

脚本执行后输出 3 段内容：

### 1. 市场环境摘要

展示：

- 市场环境总分
- 上涨家数占比
- 涨停/跌停家数
- 强势股平均溢价

### 2. 候选榜单

展示字段：

- `rank`
- `code`
- `name`
- `sector`
- `total_score`
- `market_score`
- `sector_score`
- `trend_score`
- `flow_score`
- `risk_score`
- `tag`
- `reason`

榜单按 `total_score` 降序排序。

### 3. Top 3 明细

额外输出前 3 名个股的详细解释，包括：

- 总分
- 五维分项
- 主要加分原因
- 风险提醒

## main() 流程

1. 构造 1 组市场数据、3 个板块、6 只股票
2. 初始化 `ShortTermScorer`
3. 校验输入数据合法性
4. 逐只打分并生成 `ScoreBreakdown`
5. 按总分降序排序
6. 生成排名与标签
7. 打印市场环境摘要
8. 打印候选榜单
9. 打印 Top 3 明细

## 错误处理

处理原则：

- 如果股票引用了不存在的板块，抛出 `ValueError`
- 比例字段不在合法范围内时，抛出 `ValueError`
- 数值型字段为负且不应为负时，抛出 `ValueError`
- 候选股票列表为空时，打印提示并正常退出
- 每个维度分数限制在 `0-100`
- 权重总和小于等于 0 时，抛出 `ValueError`

本次不引入日志系统，不接网络，不做重试。

## 可扩展点

后续可沿以下方向扩展：

- 将阈值抽成配置字典
- 将权重做成不同交易风格模板
- 支持 JSON/CSV 外部输入
- 增加 CSV/JSON 导出
- 将打分器迁移为项目内可复用模块
- 为真实行情数据接入预留适配层

## 验证方式

### 运行验证

执行：

```bash
python3 scripts/short_term_rank_demo.py
```

预期：

- 正常打印市场环境摘要
- 正常打印 6 只股票排序榜单
- 正常打印 Top 3 详细解释
- 进程无异常退出

### 逻辑验证

示例数据应覆盖：

- 板块强、个股强、量价健康的高分股
- 板块强但个股一般的中分股
- 个股趋势不错但风险偏高的样本
- 成交不足或板块较弱的低分股

预期排序应符合直觉：

- 高质量前排股排在前面
- 高位风险偏大的股票不会仅凭短期涨幅排第一
- 量价不配合的股票得分明显落后

### 手工边界验证

用户可直接改示例数据验证模型行为：

- 降低 `advancers_ratio`，观察全体总分下降
- 将某只股票的 `is_accelerating_high` 改为真，观察风险分下降
- 将某只股票切到弱板块，观察板块分下降
- 将某只股票的 `volume_vs_avg5` 调低，观察资金成交分下降

## 非目标与约束说明

- 本脚本是逻辑演示工具，不构成投资建议
- 不追求回测严谨性，只追求结构清晰和规则可验证
- 不直接复用项目现有策略抽象，避免首次验证时引入额外耦合
- 后续如果验证通过，可再决定是否迁移为项目内正式策略或评分模块
