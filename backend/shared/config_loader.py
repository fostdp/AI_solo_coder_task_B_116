import os
import yaml
from typing import Any, Dict
from pathlib import Path


_CONFIG_CACHE: Dict[str, Any] = {}


def _config_path() -> str:
    candidates = [
        os.environ.get("SPINNING_CONFIG_PATH"),
        str(Path(__file__).resolve().parent.parent / "config.yaml"),
        str(Path.cwd() / "config.yaml"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise FileNotFoundError("config.yaml not found. Set SPINNING_CONFIG_PATH or place it in backend/")


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE and not force_reload:
        return _CONFIG_CACHE
    path = _config_path()
    with open(path, "r", encoding="utf-8") as f:
        _CONFIG_CACHE = yaml.safe_load(f) or {}
    return _CONFIG_CACHE


def get_config(*keys: str, default: Any = None) -> Any:
    cfg = load_config()
    cur = cfg
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur
