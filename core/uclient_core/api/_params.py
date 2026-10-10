from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..errors import invalid_params


def require(params: dict[str, Any], name: str) -> Any:
    if name not in params:
        raise invalid_params(f"missing parameter: {name}")
    return params[name]


def vec(params: dict[str, Any], name: str, n: int, default: Any = None) -> np.ndarray:
    v = params.get(name, default)
    if v is None:
        raise invalid_params(f"missing parameter: {name}")
    if not isinstance(v, (list, tuple)) or len(v) != n:
        raise invalid_params(f"{name} must be an array of length {n}")
    try:
        arr = np.array([float(x) for x in v], dtype=np.float64)
    except (TypeError, ValueError):
        raise invalid_params(f"{name} must contain numbers") from None
    if not all(math.isfinite(x) for x in arr):
        raise invalid_params(f"{name} must be finite")
    return arr


def number(params: dict[str, Any], name: str, default: float | None = None) -> float:
    v = params.get(name, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise invalid_params(f"{name} must be a finite number")
    return float(v)
