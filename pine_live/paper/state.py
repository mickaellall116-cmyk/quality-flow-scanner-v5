"""Persistence for the paper phase: portfolio state, watermarks, health.

All writes are atomic (tmp file + os.replace + directory fsync) so a
crash mid-write can never leave a half-written state file behind. The
runner persists portfolio state + watermarks AFTER every wake-up; a
persistence failure is a HALT condition (fail closed, never proceed on
unpersisted state).
"""

from __future__ import annotations

import json
import os

from pine_live.portfolio import PortfolioState

SCHEMA = "paper-state-v1"


def _atomic_write_json(path: str, obj: dict) -> None:
    """Write JSON atomically: tmp file, fsync, rename, fsync directory."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dirfd = os.open(os.path.dirname(os.path.abspath(path)), os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def portfolio_path(state_dir: str) -> str:
    return os.path.join(state_dir, "portfolio.json")


def watermarks_path(state_dir: str) -> str:
    return os.path.join(state_dir, "watermarks.json")


def health_path(state_dir: str) -> str:
    return os.path.join(state_dir, "download_health.json")


def load_portfolio(state_dir: str, mark_fn, cost: float):
    """Load persisted portfolio; returns (state, existed).

    existed=False means this is the first run ever: the caller gets a
    fresh PortfolioState and must persist it.
    """
    path = portfolio_path(state_dir)
    if not os.path.exists(path):
        return PortfolioState(mark_fn, cost), False
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if raw.get("schema") != SCHEMA:
        raise ValueError(
            f"paper state schema mismatch: {raw.get('schema')!r} != {SCHEMA!r}")
    st = PortfolioState.from_dict(raw["portfolio"], mark_fn)
    if abs(st.cost - float(cost)) > 1e-12:
        raise ValueError(
            f"paper state cost {st.cost} != frozen cost {cost}: refusing to "
            "run on a state built with different cost assumptions")
    return st, True


def save_portfolio(state_dir: str, state: PortfolioState) -> None:
    """Persist portfolio state atomically. Raises on any failure."""
    _atomic_write_json(portfolio_path(state_dir),
                       {"schema": SCHEMA, "portfolio": state.to_dict()})


def load_watermarks(state_dir: str) -> dict:
    """Symbol -> ISO of last-processed BAR OPEN. Missing file -> {}."""
    path = watermarks_path(state_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if raw.get("schema") != SCHEMA:
        raise ValueError(
            f"watermark schema mismatch: {raw.get('schema')!r}")
    return dict(raw.get("watermarks", {}))


def save_watermarks(state_dir: str, watermarks: dict) -> None:
    _atomic_write_json(watermarks_path(state_dir),
                       {"schema": SCHEMA, "watermarks": dict(watermarks)})


def load_health(state_dir: str) -> dict:
    """Per-symbol consecutive download-failure counts. Missing -> {}."""
    path = health_path(state_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return dict(json.load(f).get("failures", {}))


def save_health(state_dir: str, failures: dict) -> None:
    _atomic_write_json(health_path(state_dir),
                       {"schema": SCHEMA, "failures": dict(failures)})
