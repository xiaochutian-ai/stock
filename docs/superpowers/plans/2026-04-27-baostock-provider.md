# BaoStock Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `baostock`-backed `DataProvider` implementation that can run the existing screening engine with graceful degradation for unsupported data.

**Architecture:** Follow the existing datasource plugin pattern: create a single `BaostockProvider` class registered through the provider registry, keep third-party imports lazy, and translate BaoStock result sets into the repository's DTOs. Use explicit fallbacks for unsupported capabilities so engine and strategies keep working without uncaught exceptions.

**Tech Stack:** Python 3.9+, `pandas`, `tenacity`, `pytest`, optional `baostock`

---

## File Structure

- Create: `src/astock/datasource/baostock_provider.py`
  - BaoStock datasource implementation, resultset helpers, field mapping, login/logout, graceful fallbacks
- Modify: `src/astock/datasource/__init__.py`
  - Import the new provider module so registration happens on package import
- Create: `tests/test_baostock_provider.py`
  - Focused tests for stock listing, kline normalization, financial mapping, and money-flow fallback

### Task 1: Write Red Tests For BaoStock Provider

**Files:**
- Create: `tests/test_baostock_provider.py`

- [ ] Add tests that expect:
  - `list_stocks()` reads BaoStock rows and returns `Stock` DTOs with normalized codes, `Board`, and `is_st`
  - `get_kline()` converts BaoStock daily fields into the expected `KLine.df` columns and date index
  - `get_financial()` merges latest valuation row and latest financial rows into a `Financial`
  - `get_money_flow()` returns `[]` instead of raising when BaoStock has no native money-flow support
- [ ] Run `pytest tests/test_baostock_provider.py -q` and confirm RED because the provider module does not exist yet

### Task 2: Implement BaoStock Provider

**Files:**
- Create: `src/astock/datasource/baostock_provider.py`
- Modify: `src/astock/datasource/__init__.py`
- Test: `tests/test_baostock_provider.py`

- [ ] Add `BaostockProvider` with `@register_provider("baostock")`
- [ ] Implement lazy import plus `login()` in `__init__` and `logout()` in `close()`
- [ ] Add helpers to collect BaoStock result sets into `DataFrame`
- [ ] Implement `list_stocks()` via `query_all_stock()`
- [ ] Implement `get_kline()` via `query_history_k_data_plus()`
- [ ] Implement `get_financial()` using the latest available valuation and financial query results
- [ ] Keep `get_financials_batch()` on the base loop implementation unless a safe batch shortcut is available
- [ ] Implement `get_money_flow()` as explicit graceful degradation returning `[]`
- [ ] Register the provider in `src/astock/datasource/__init__.py`

### Task 3: Verify And Clean Up

**Files:**
- Test: `tests/test_baostock_provider.py`
- Check: `src/astock/datasource/baostock_provider.py`
- Check: `src/astock/datasource/__init__.py`

- [ ] Run `pytest tests/test_baostock_provider.py -q`
- [ ] Run `ruff check src/ tests/`
- [ ] Run diagnostics on edited files and fix any introduced issues
- [ ] If `baostock` is available locally, run a light smoke import such as `python3 -c "from astock.datasource import get_provider; print(type(get_provider('baostock')).__name__)"`
