# astock — A 股选股系统

面向接口编程的 A 股选股系统，数据源、存储后端、选股策略三者均通过抽象接口 + 注册表模式解耦，**切换任一实现不需要修改其他层的代码**。

- **数据源**：默认 akshare（免费开源，无需 token），可扩展 tushare / baostock / efinance
- **存储**：默认 SQLite（开箱即用），可通过 SQLAlchemy URL 切换 MySQL / PostgreSQL
- **策略**：插件化，内置技术面 / 基本面 / 资金面三类，支持多因子加权综合打分
- **交付**：CLI 优先，输出控制台 rich 表格 / CSV / Excel / JSON

## 快速开始

### 1. 安装

需要 Python 3.9+（开发环境已验证 3.13）。

```bash
# 克隆代码
git clone <repo-url> && cd stock

# 创建虚拟环境并安装
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

可选数据源依赖：

```bash
pip install -e ".[tushare]"     # 装 tushare
pip install -e ".[baostock]"    # 装 baostock
pip install -e ".[dev]"         # 装 pytest / ruff / mypy
```

### 2. 运行

```bash
# 使用默认配置全市场选股
astock run

# 仅评估前 100 只股票（调试用）
astock run --limit 100

# 导出 CSV 到 data/output/
astock run --output csv --save

# 使用自定义配置
astock run -c config/my_strategy.yaml
```

### 3. 查看插件

```bash
astock list-providers      # 可用数据源
astock list-storages       # 可用存储
astock list-strategies     # 可用策略
```

### 4. 端到端 Mock 测试（无需联网）

```bash
python3 tests/test_e2e.py
```

## Web 工作台

### 开发启动

后端和前端是分离维护的两个开发进程：

- 后端：FastAPI，默认地址 `http://localhost:8000`
- 前端：Vite + React + TypeScript，默认地址 `http://localhost:5173`

### 1. 启动后端 API

先在项目根目录安装 Python 依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

然后启动 Web API：

```bash
python3 - <<'PY'
from astock.config import load_settings
from astock.webapi.app import create_app
import uvicorn

app = create_app(load_settings())
uvicorn.run(app, host="127.0.0.1", port=8000)
PY
```

说明：

- 默认读取 `config/default.yaml`
- 若需切换配置文件，可先设置 `ASTOCK_CONFIG=/path/to/config.yaml`
- 当前 `create_app()` 需要显式注入 `Settings`，因此这里使用 Python 启动脚本而不是直接执行 `uvicorn astock.webapi.app:create_app --factory`

### 2. 启动前端

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

启动后可在浏览器访问：

- 前端页面：`http://localhost:5173`
- 后端 API：`http://localhost:8000`
- OpenAPI 文档：`http://localhost:8000/docs`

### 3. 本地验证

后端验证：

```bash
PYTHONPATH=src pytest tests/webapi -q
python3 tests/test_e2e.py
ruff check src/ tests/
```

前端验证：

```bash
cd frontend
npm test
npm run build
```

## 配置说明

默认配置文件：[`config/default.yaml`](config/default.yaml)

```yaml
datasource:
  name: akshare              # 切换数据源只需改这里
  options: { timeout: 30, retry: 3 }

storage:
  name: sqlite               # 切换存储后端
  options:
    url: "sqlite:///./data/astock.db"
    # 切换 MySQL: url: "mysql+pymysql://user:pass@host:3306/astock"

strategies:                  # 策略可任意组合，每项独立权重
  - name: technical
    enabled: true
    weight: 0.4
    params: { ma_bull: true, macd_gold_cross: true, rsi_range: [30, 70] }
  - name: fundamental
    enabled: true
    weight: 0.3
    params: { pe_max: 50, pb_max: 10, roe_min: 0.10 }
  - name: money_flow
    enabled: true
    weight: 0.3
    params: { main_inflow_days: 3, min_inflow_amount: 1000000 }

market:
  boards: [main_board, sme_board]   # 选股市场范围
  exclude_st: true                   # 排除 ST 股

output:
  format: console
  top_n: 50
  min_score: 0.5                     # 综合得分阈值
```

## 项目结构

```text
stock/
├── AGENTS.md                # Agent 总入口（任务路由）
├── README.md                # 你正在看的文件
├── ARCHITECTURE.md          # 代码地图与架构不变量
├── pyproject.toml           # 项目定义 + 依赖
├── config/default.yaml      # 默认配置
├── src/astock/
│   ├── models/              # DTO（Stock/Quote/KLine/Financial/MoneyFlow）
│   ├── datasource/          # DataProvider 抽象 + akshare 实现
│   ├── storage/             # Repository 抽象 + SQLite 实现
│   ├── indicators/          # 纯函数技术指标
│   ├── strategy/            # Strategy 抽象 + 三类默认策略
│   ├── engine/              # 选股引擎（编排流水线）
│   ├── config/              # YAML 配置加载
│   ├── output/              # 控制台 / CSV / Excel / JSON
│   ├── webapi/              # FastAPI Web API（meta / runs / history）
│   └── cli.py               # typer CLI 入口
├── frontend/                # React + Vite Web 前端
└── tests/
    ├── webapi/              # Web API 测试
    └── test_e2e.py          # 端到端 Mock 测试
```

详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

## 扩展指南

### 新增一种数据源

参考 [`src/astock/datasource/AGENTS.md`](src/astock/datasource/AGENTS.md)：

1. 新建 `src/astock/datasource/tushare_provider.py`
2. 继承 `DataProvider`，实现 `list_stocks / get_kline / get_financial / get_money_flow`
3. 用 `@register_provider("tushare")` 装饰类
4. 在 `src/astock/datasource/__init__.py` 末尾添加 `from . import tushare_provider`
5. 配置 `datasource.name: tushare` 即可

### 新增一种选股策略

参考 [`src/astock/strategy/AGENTS.md`](src/astock/strategy/AGENTS.md)：

1. 新建 `src/astock/strategy/my_strategy.py`
2. 继承 `Strategy`，实现 `evaluate(ctx: StrategyContext) -> StrategyResult`
3. 用 `@register_strategy("my_strategy")` 装饰类
4. 在 `src/astock/strategy/__init__.py` 末尾添加 `from . import my_strategy`
5. 在配置文件 `strategies` 列表中启用

### 切换存储后端

参考 [`src/astock/storage/AGENTS.md`](src/astock/storage/AGENTS.md)：

- **基础切换**：修改 `config/default.yaml` 的 `storage.options.url`（SQLAlchemy URL）即可支持 MySQL / PostgreSQL
- **方言优化**：若需使用 MySQL 的 `ON DUPLICATE KEY UPDATE` 等特性，新建 `src/astock/storage/mysql_repo.py` 继承 `Repository` 并 `@register_repository("mysql")`

## 开发规范

请阅读 [`AGENTS.md`](AGENTS.md) 的"核心约束"章节。要点：

- 面向抽象编程，禁止绕过注册表
- 网络调用必须重试，数据缺失走容错返回
- 批量写入必须分批（SQLite 参数上限 32766）
- Lint：`ruff check src/ tests/`

## 免责声明

本项目仅用于学习与研究。选股结果仅供参考，**不构成任何投资建议**。A 股投资有风险，入市需谨慎。

## 许可证

根据仓库的 LICENSE 文件（如有）。
