"""astock: A 股选股系统

面向接口编程的分层架构：
- datasource: 数据源抽象层（可切换 akshare / tushare / baostock 等）
- storage: 存储抽象层（可切换 SQLite / MySQL 等）
- strategy: 策略抽象层（可插拔技术面/基本面/资金面/多因子）
- engine: 编排流程
- cli: 命令行入口
"""

__version__ = "0.1.0"
