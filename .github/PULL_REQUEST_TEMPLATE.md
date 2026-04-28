# 背景

为 `astock` 增加一个本地开发可用的 Web 工作台 MVP，在保留现有 CLI 和选股引擎边界的前提下，补齐最小前后端闭环：

- 后端提供 Web API：参数读取、运行创建、结果查询、历史查询
- 前端提供工作台页面与历史页基础壳
- README 补充本地启动和联调说明
- 用测试覆盖新增的 Web API 与前端页面壳

# 功能亮点

- 新增独立的 Web API 层，复用现有 `ScreeningEngine`，不改动核心选股职责边界
- 新增运行历史持久化能力，`POST /api/runs` 创建成功后会把结果快照写入 SQLite
- 新增前端 `frontend/` 工程，采用 React + Vite + TypeScript，和后端目录分离维护
- 提供最小可用的工作台页面：
  - 选股表单区域
  - 结果列表区域
- 提供最小可用的历史页面：
  - 历史列表加载
  - 空态展示
- README 新增 Web 工作台开发启动说明，支持本地快速联调

# 主要变更

## 1. 后端 Web API

新增历史相关模块：

- `src/astock/webapi/history_store.py`
- `src/astock/webapi/routes/history.py`
- `src/astock/webapi/services/history_service.py`

更新应用装配与运行流程：

- `src/astock/webapi/app.py`
- `src/astock/webapi/routes/runs.py`

具体能力：

- `GET /api/meta/options`
- `POST /api/runs`
- `GET /api/runs/{run_id}/results`
- `GET /api/runs/{run_id}/results/{code}`
- `GET /api/history`
- `GET /api/history/{run_id}`

运行历史的实现方式：

- 在创建 run 成功后，将 `params / summary / results / details` 持久化到 Web 专用 SQLite 历史库
- 历史查询接口从持久化快照读取，避免查询阶段重跑引擎

## 2. 前端工程初始化

新增 `frontend/` 工程：

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html`

新增应用入口与基础页面：

- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/pages/WorkbenchPage.tsx`
- `frontend/src/pages/HistoryPage.tsx`

新增基础状态与 API 封装：

- `frontend/src/store/useWorkbenchStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/types/api.ts`

新增基础组件：

- `frontend/src/components/StrategyConfigForm.tsx`
- `frontend/src/components/ResultsTable.tsx`
- `frontend/src/components/HistoryList.tsx`

## 3. 测试补充

后端新增历史 API 测试：

- `tests/webapi/test_history_api.py`

前端新增页面壳测试：

- `frontend/src/__tests__/workbench.test.tsx`
- `frontend/src/__tests__/history.test.tsx`

## 4. 文档与工程整理

更新文档：

- `README.md`

更新忽略规则：

- `.gitignore`

README 新增内容包括：

- Web 工作台后端启动方式
- 前端启动方式
- 本地联调入口地址
- 后端/前端验证命令

# 变更清单

## 后端

- 新增 Web 历史持久化存储
- 新增 `/api/history` 与 `/api/history/{run_id}` 接口
- 在 `POST /api/runs` 成功后写入历史快照
- 在 `create_app()` 中接入 `HistoryStore`

## 前端

- 初始化 React + Vite + TypeScript 工程
- 新增工作台页 `WorkbenchPage`
- 新增历史页 `HistoryPage`
- 新增最小状态层和 API client
- 新增结果表格、配置表单、历史列表组件

## 测试

- 新增后端历史 API 测试
- 新增前端工作台页测试
- 新增前端历史页测试

## 文档

- README 增加 Web 工作台开发启动说明
- README 更新项目结构说明

# 验证结果

已执行并通过：

```bash
PYTHONPATH=src pytest tests/webapi -q
PYTHONPATH=src python3 tests/test_e2e.py
ruff check src/ tests/
cd frontend && npm test
cd frontend && npm run build
```

结果：

- Web API 测试：`10 passed`
- 端到端 Mock 测试：通过
- Ruff：`All checks passed!`
- 前端测试：`2 passed`
- 前端构建：通过

# 当前范围与已知限制

本 PR 交付的是 Web 工作台 MVP，当前范围主要是“最小可用闭环”：

- 已支持工作台基础页面和历史列表页面
- 已支持运行结果快照落历史
- 前端当前仍偏基础壳，交互和展示能力较简化
- 历史页当前以列表/空态展示为主，未扩展更复杂的详情交互
- 工作台页面当前提供最小表单和结果表格，尚未补完整详情面板体验

# Reviewer 关注点

建议重点关注以下几个方面：

- Web API 是否保持对 `ScreeningEngine` 的正确复用，未破坏原有职责边界
- 运行历史是否满足“创建时快照、读取时只读”的语义
- 前后端目录拆分是否清晰，是否便于后续继续扩展
- README 的启动方式是否足够准确、可直接复现

# 后续可选增强

不在本 PR 范围内，但可作为后续迭代：

- 工作台结果详情面板
- 历史详情回看与跳转
- 前端路由与页面导航
- 更完整的参数配置 UI
- Web 运行态、加载态、错误态优化
