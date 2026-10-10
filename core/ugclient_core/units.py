"""The single place where API units (mm, deg) are converted to internal SI (m, rad)."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

MM_PER_M = 1000.0


def deg_to_rad(v: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.radians(np.asarray(v, dtype=np.float64))


def rad_to_deg(v: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.degrees(np.asarray(v, dtype=np.float64))


def mm_to_m(v: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(v, dtype=np.float64) / MM_PER_M


def m_to_mm(v: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(v, dtype=np.float64) * MM_PER_M


def pose_api_to_si(pose: Sequence[float]) -> np.ndarray:
    """[x,y,z mm, r,p,y deg] -> [x,y,z m, r,p,y rad]."""
    p = np.asarray(pose, dtype=np.float64).reshape(-1)
    if p.size != 6 or not np.all(np.isfinite(p)):
        raise ValueError("pose must be 6 finite numbers")
    return np.concatenate([mm_to_m(p[:3]), deg_to_rad(p[3:])])


def pose_si_to_api(pose: Sequence[float]) -> list[float]:
    p = np.asarray(pose, dtype=np.float64).reshape(-1)
    return [*m_to_mm(p[:3]).tolist(), *rad_to_deg(p[3:]).tolist()]


def wrap_deg(a: float) -> float:
    return (a + 180.0) % 360.0 - 180.0


def is_close_angle(a: float, b: float, tol_deg: float) -> bool:
    return abs(wrap_deg(a - b)) <= tol_deg or math.isclose(a, b, abs_tol=tol_deg)
