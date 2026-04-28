# Web Run Worker Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `/api/runs` from synchronous execution to a cancellable background worker model so shutdown can stop in-flight screening work gracefully.

**Architecture:** Introduce an in-memory run task manager on `app.state` that tracks run status, cancellation events, worker threads, and cached results. `POST /api/runs` creates a run record and schedules work in a background thread; `ScreeningEngine` receives a cancellation callback and checks it during long loops so shutdown can cancel work promptly.

**Tech Stack:** FastAPI, Python threading, in-memory app state, pytest, FastAPI TestClient

---

### Task 1: Define Run Task State

**Files:**
- Modify: `src/astock/webapi/app.py`
- Modify: `src/astock/webapi/schemas.py`
- Test: `tests/webapi/test_runs_api.py`

- [ ] Add run status fields needed for pending/running/succeeded/cancelled/failed responses
- [ ] Add app state containers for task registry, run cache, and shutdown coordination
- [ ] Update tests to expect asynchronous create-run semantics

### Task 2: Implement Background Run Manager

**Files:**
- Modify: `src/astock/webapi/services/run_service.py`
- Modify: `src/astock/webapi/routes/runs.py`
- Test: `tests/webapi/test_runs_api_review.py`

- [ ] Add task creation that returns immediately with a new `run_id`
- [ ] Run screening work in a thread and update task status/result cache on completion
- [ ] Keep results/detail endpoints read-only from cached snapshots, without rerunning the engine

### Task 3: Add Cancellation Hooks

**Files:**
- Modify: `src/astock/engine/screener.py`
- Modify: `src/astock/webapi/services/run_service.py`
- Test: `tests/webapi/test_runs_api_review.py`

- [ ] Add a cancellable execution hook to `ScreeningEngine`
- [ ] Check cancellation before and during long stock-processing loops
- [ ] Mark cancelled runs distinctly from failed runs

### Task 4: Shutdown Lifecycle

**Files:**
- Modify: `src/astock/webapi/app.py`
- Modify: `src/astock/webapi/services/run_service.py`
- Test: `tests/webapi/test_runs_api_review.py`

- [ ] Register FastAPI lifespan/shutdown cleanup
- [ ] On shutdown, cancel in-flight runs and wait briefly for worker threads to exit
- [ ] Ensure successful runs still persist history while cancelled runs do not

### Task 5: Verify End-to-End

**Files:**
- Modify: `tests/webapi/test_runs_api.py`
- Modify: `tests/webapi/test_runs_api_review.py`

- [ ] Run focused web API tests for create, list, detail, cancel-on-shutdown semantics
- [ ] Run broader `tests/webapi` suite and confirm no regression
