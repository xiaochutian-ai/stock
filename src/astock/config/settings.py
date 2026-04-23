"""配置加载与校验。"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# 默认配置路径（相对于项目根）
DEFAULT_CONFIG_PATH = "config/default.yaml"


@dataclass
class Settings:
    """运行时配置。"""

    datasource: Dict[str, Any] = field(default_factory=dict)
    storage: Dict[str, Any] = field(default_factory=dict)
    strategies: List[Dict[str, Any]] = field(default_factory=list)
    market: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    logging_cfg: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Settings":
        return cls(
            datasource=d.get("datasource", {}),
            storage=d.get("storage", {}),
            strategies=d.get("strategies", []),
            market=d.get("market", {}),
            output=d.get("output", {}),
            logging_cfg=d.get("logging", {}),
        )


def load_settings(path: Optional[str] = None) -> Settings:
    """从 YAML 加载配置。

    路径优先级：
        1. 显式传入 path
        2. 环境变量 ASTOCK_CONFIG
        3. 项目相对路径 config/default.yaml
    """
    cfg_path = path or os.environ.get("ASTOCK_CONFIG") or DEFAULT_CONFIG_PATH
    p = Path(cfg_path)
    if not p.exists():
        logger.warning("配置文件 %s 不存在，使用内置默认值", p)
        return Settings()
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.info("已加载配置文件: %s", p.resolve())
    return Settings.from_dict(data)
