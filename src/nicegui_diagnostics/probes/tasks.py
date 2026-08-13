"""Asyncio task probe — collects a summary of running tasks grouped by coroutine name."""
from __future__ import annotations

import asyncio
import collections
import time
from typing import Any

import nicegui.background_tasks as _bt

_task_birth_times: dict[int, float] = {}
_original_create = _bt.create


def _wrapped_create(*args: Any, **kwargs: Any) -> Any:
    """Wrap ``nicegui.background_tasks.create`` to stamp birth time at creation."""
    task = _original_create(*args, **kwargs)
    _task_birth_times[id(task)] = time.monotonic()
    task.add_done_callback(lambda t: _task_birth_times.pop(id(t), None))
    return task


def install() -> None:
    """Start tracking task birth times.

    Monkey-patches ``nicegui.background_tasks.create`` so tasks created after
    install() get accurate birth times.  Also snapshots existing tasks so that
    pre-existing tasks are accounted for (fallback for tasks already running).
    """
    _bt.create = _wrapped_create
    try:
        tasks = asyncio.all_tasks()
    except RuntimeError:
        return
    for task in tasks:
        tid = id(task)
        if tid not in _task_birth_times:
            _task_birth_times[tid] = time.monotonic()


def uninstall() -> None:
    """Restore original ``background_tasks.create`` and clear tracked birth times."""
    _bt.create = _original_create
    _task_birth_times.clear()


def collect() -> dict[str, Any]:
    """Collect asyncio task summary grouped by coroutine qualname.

    Returns a dict with ``total`` count and ``by_coroutine`` mapping
    each coroutine group to its count, oldest age, and task names.
    """
    now = time.monotonic()
    try:
        tasks = asyncio.all_tasks()
    except RuntimeError:
        # No running event loop — return empty summary
        return {
            'asyncio_tasks': {
                'total': 0,
                'by_coroutine': {},
            },
        }

    # Track birth times for current tasks; prune dead ones
    current_ids: set[int] = set()
    for task in tasks:
        tid = id(task)
        current_ids.add(tid)
        if tid not in _task_birth_times:
            _task_birth_times[tid] = now

    # Prune tasks that no longer exist
    for tid in list(_task_birth_times):
        if tid not in current_ids:
            del _task_birth_times[tid]

    counter: collections.Counter[str] = collections.Counter()
    names_by_group: dict[str, list[str]] = {}
    oldest_by_group: dict[str, float] = {}

    for task in tasks:
        qualname = getattr(task.get_coro(), '__qualname__', '')
        # Extract last two dotted segments for readable grouping
        key = '.'.join(qualname.rsplit('.', 2)[-2:])
        counter[key] += 1
        names_by_group.setdefault(key, []).append(task.get_name())

        tid = id(task)
        age = now - _task_birth_times.get(tid, now)
        if key not in oldest_by_group or age > oldest_by_group[key]:
            oldest_by_group[key] = age

    by_coroutine = {
        key: {
            'count': count,
            'oldest_age_s': round(oldest_by_group.get(key, 0.0), 3),
            'names': names_by_group[key],
        }
        for key, count in counter.most_common()
    }

    return {
        'asyncio_tasks': {
            'total': len(tasks),
            'by_coroutine': by_coroutine,
        },
    }
