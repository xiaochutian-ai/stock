# 背景

为 `astock` 增加一个本地开发可用的 Web 工作台 MVP，并继续完善本地运行体验与服务生命周期能力。在保留现有 CLI 和选股引擎边界的前提下，本 PR 补齐了最小前后端闭环，并进一步补上：

- 后端提供 Web API：参数读取、运行创建、结果查询、历史查询
- 前端提供工作台页面与历史页基础壳
- README 补充本地启动和联调说明
- 提供 `start / stop / restart` 生命周期脚本
- 支持可选的端口冲突自动释放
- 将 `/api/runs` 升级为后台 worker 模型
- 在服务 shutdown 时优雅取消运行中的选股任务
- 用测试覆盖新增的 Web API、前端页面壳和脚本能力

# 功能亮点

- 新增独立的 Web API 层，复用现有 `ScreeningEngine`，不改动核心选股职责边界
- 新增运行历史持久化能力，成功完成的 run 会把结果快照写入 SQLite
- 新增前端 `frontend/` 工程，采用 React + Vite + TypeScript，和后端目录分离维护
- 提供最小可用的工作台页面：
  - 选股表单区域
  - 结果列表区域
- 提供最小可用的历史页面：
  - 历史列表加载
  - 空态展示
- 提供本地生命周期脚本：
  - `scripts/start_web.sh`
  - `scripts/stop_web.sh`
  - `scripts/restart_web.sh`
- 提供 PID 文件管理：
  - `.run/web.pid`
- 提供可选的端口冲突自动释放能力：
  - `START_WEB_KILL_ON_PORT_CONFLICT=1 bash scripts/start_web.sh`
- 前端 API 改为相对路径 + Vite 代理：
  - 不再写死 `http://localhost:8000`
  - 一键脚本切换后端端口时，前端代理自动跟随
- 后端运行模型升级为后台 worker：
  - `POST /api/runs` 立即返回 `run_id`
  - 真正选股逻辑在后台线程执行
  - 任务状态支持 `pending / running / succeeded / cancelled / failed`
- 新增优雅关机能力：
  - FastAPI shutdown 时会取消运行中的任务
  - `ScreeningEngine` 在长循环与关键数据拉取前后检查取消信号
  - 成功任务才写历史，取消任务不会写成功快照

# 主要变更

## 1. 后端 Web API

新增历史相关模块：

- `src/astock/webapi/history_store.py`
- `src/astock/webapi/routes/history.py`
- `src/astock/webapi/services/history_service.py`

更新应用装配、运行流程与 run 生命周期：

- `src/astock/webapi/app.py`
- `src/astock/webapi/routes/runs.py`
- `src/astock/webapi/services/run_service.py`
- `src/astock/engine/screener.py`

具体能力：

- `GET /api/meta/options`
- `POST /api/runs`
- `GET /api/runs/{run_id}/results`
- `GET /api/runs/{run_id}/results/{code}`
- `GET /api/history`
- `GET /api/history/{run_id}`

运行历史与后台任务的实现方式：

- 创建 run 后立即返回，不再同步阻塞等待整个选股流程完成
- 真正选股逻辑在后台 worker 线程执行
- 运行中任务状态保存在 `app.state.run_cache / run_tasks`
- FastAPI shutdown 时统一取消运行中任务
- `ScreeningEngine` 协作式检查取消信号，在长循环中尽快退出
- 历史查询接口从持久化快照读取，避免查询阶段重跑引擎
- 只有成功完成的任务才写入历史库，`cancelled` / `failed` 不写成功快照

## 2. 前端工程初始化与 API 接入

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

前端 API 改造：

- 请求路径改为相对路径 `/api/...`
- `vite.config.ts` 增加 `/api` 代理
- 一键启动脚本注入 `VITE_BACKEND_PROXY_TARGET`，确保代理目标跟随后端实际端口

## 3. Web 生命周期脚本

新增/更新：

- `scripts/start_web.sh`
- `scripts/stop_web.sh`
- `scripts/restart_web.sh`
- `.gitignore`

具体行为：

- 启动前自动准备依赖
- 启动成功后写入 `.run/web.pid`
- `stop_web.sh` 基于 PID 文件精准停止本项目启动的前后端
- `restart_web.sh` 先停再起
- 支持可配置端口冲突处理：
  - 默认：端口冲突时报错退出
  - 开启 `START_WEB_KILL_ON_PORT_CONFLICT=1` 后：先释放占用端口再启动

## 4. 测试补充

后端新增/更新测试：

- `tests/webapi/test_history_api.py`
- `tests/webapi/test_runs_api.py`
- `tests/webapi/test_runs_api_review.py`

前端新增测试：

- `frontend/src/__tests__/workbench.test.tsx`
- `frontend/src/__tests__/history.test.tsx`
- `frontend/src/__tests__/client.test.ts`

脚本新增/更新测试：

- `tests/test_start_web_script.py`

实现计划文档：

- `docs/superpowers/plans/2026-04-28-web-run-worker-lifecycle.md`

## 5. 文档与工程整理

更新文档：

- `README.md`

README 新增内容包括：

- Web 工作台后端启动方式
- 前端启动方式
- 本地联调入口地址
- 一键启动 / 停止 / 重启命令
- 端口冲突自动释放用法
- 后端/前端验证命令

# 变更清单

## 后端

- 新增 Web 历史持久化存储
- 新增 `/api/history` 与 `/api/history/{run_id}` 接口
- 将 `/api/runs` 改为后台 worker 模型
- 新增运行中任务状态管理与取消逻辑
- 新增 shutdown 时的 run task 清理
- 引擎增加协作式取消检查点
- 成功任务完成后写历史快照
- `cancelled` / `failed` 不写成功历史

## 前端

- 初始化 React + Vite + TypeScript 工程
- 新增工作台页 `WorkbenchPage`
- 新增历史页 `HistoryPage`
- 新增最小状态层和 API client
- 新增结果表格、配置表单、历史列表组件
- API 调用改为相对路径
- Vite 增加反向代理
- 支持一键脚本动态代理到实际后端端口

## 启动脚本

- 新增 `start/stop/restart` 生命周期脚本
- 新增 `.run/web.pid` PID 文件管理
- 新增可选端口冲突自动释放能力

## 测试

- 新增后端历史 API 测试
- 新增后端后台 worker 与 shutdown cancel 测试
- 新增前端工作台页测试
- 新增前端历史页测试
- 新增前端 API 相对路径测试
- 新增启动脚本 PID/stop/restart 测试
- 新增端口冲突自动释放测试

## 文档

- README 增加 Web 工作台开发启动说明
- README 更新项目结构说明
- README 补充生命周期脚本与端口冲突处理说明

# 验证结果

已执行并通过：

```bash
PYTHONPATH=src pytest tests/webapi -q
PYTHONPATH=src pytest tests/test_start_web_script.py -q
PYTHONPATH=src python3 tests/test_e2e.py
ruff check src/ tests/
cd frontend && npm test
cd frontend && npm run build
```

结果：

- Web API 测试：`11 passed`
- 启动脚本测试：`4 passed`
- 端到端 Mock 测试：通过
- Ruff：`All checks passed!`
- 前端测试：`3 passed`
- 前端构建：通过

# 当前范围与已知限制

本 PR 交付的是 Web 工作台 MVP，并补齐了本地运行体验与优雅关机能力。当前范围主要是“最小可用闭环 + 生命周期增强”：

- 已支持工作台基础页面和历史列表页面
- 已支持运行结果快照落历史
- 已支持本地一键启动、停止、重启
- 已支持可选端口冲突自动释放
- 已支持后台 worker 和 shutdown 时取消运行中的任务
- 前端当前仍偏基础壳，交互和展示能力较简化
- 历史页当前以列表/空态展示为主，未扩展更复杂的详情交互
- 工作台页面当前提供最小表单和结果表格，尚未补完整详情面板体验
- 当前后台任务取消是“协作式取消”，不是强杀
- 如果任务正阻塞在单次底层网络调用中，需要等该调用返回后，才能在下一个检查点退出
- 当前任务状态仍是进程内内存态，服务重启后不会恢复运行中任务
- 本 PR 仍聚焦本地开发与 MVP 闭环，未引入完整任务队列或持久化调度系统

# Reviewer 关注点

建议重点关注以下几个方面：

- Web API 是否保持对 `ScreeningEngine` 的正确复用，未破坏原有职责边界
- `/api/runs` 改为后台 worker 后，接口语义是否仍满足现有前端使用方式
- 运行历史是否满足“成功完成后写快照、读取时只读”的语义
- shutdown -> cancel -> worker 退出这条链路是否清晰且无资源泄漏
- `ScreeningEngine` 中新增的取消检查点是否足够覆盖长耗时路径
- 前后端目录拆分是否清晰，是否便于后续继续扩展
- 生命周期脚本是否足够准确，是否会误伤非本项目服务
- README 的启动方式是否足够准确、可直接复现

# 后续可选增强

不在本 PR 范围内，但可作为后续迭代：

- 工作台结果详情面板
- 历史详情回看与跳转
- 前端路由与页面导航
- 更完整的参数配置 UI
- Web 运行态、加载态、错误态优化
- 任务列表、任务取消按钮和运行进度展示
- 持久化任务队列与跨进程 worker
