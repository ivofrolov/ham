import contextlib
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from ham.proto import (
    Atom,
    CronCallback,
    DayOfMonth,
    DayOfWeek,
    Every,
    Hour,
    Minute,
    Month,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Expr:
    M: Minute = Every
    H: Hour = Every
    d: DayOfMonth = Every
    m: Month = Every
    w: DayOfWeek = Every


def _match(atom: Atom, unit: int) -> bool:
    match atom:
        case None:
            return True
        case [*values]:
            return unit in values
        case value:
            return unit == value


def is_it_time(expr: Expr, now: datetime) -> bool:
    return (
        _match(expr.M, now.minute)
        and _match(expr.H, now.hour)
        and (_match(expr.d, now.day) or _match(expr.w, now.isoweekday() % 7))
        and _match(expr.m, now.month)
    )


class Cron:
    _last_run: float
    _schedule: list[tuple[Expr, CronCallback]]
    _timer: threading.Event
    _lock: threading.Lock

    _wake_timeout: float = 1.0
    _granularity: float = 60.0

    def __init__(self) -> None:
        self._schedule = []
        self._timer = threading.Event()
        self._lock = threading.Lock()

    def _run_tasks(self, now: datetime) -> None:
        schedule = self._schedule.copy()
        for expr, callback in schedule:
            if is_it_time(expr, now):
                t = threading.Thread(
                    target=self._run_callback,
                    args=(callback,),
                    daemon=True,
                )
                t.start()

    def _run_callback(self, callback: CronCallback) -> None:
        try:
            callback()
        except Exception:
            logger.exception("callback failed")

    def run(self) -> None:
        self._last_run = time.monotonic()
        while not self._timer.wait(self._wake_timeout):
            now = time.monotonic()
            if now - self._last_run >= self._granularity:
                self._last_run = now
                self._run_tasks(datetime.now())

    def cancel(self) -> None:
        self._timer.set()

    def add(self, expr: Expr, callback: CronCallback) -> None:
        with self._lock:
            self._schedule.append((expr, callback))
        logger.debug("callback schedule")

    def remove(self, expr: Expr, callback: CronCallback) -> None:
        with self._lock:
            with contextlib.suppress(ValueError):
                self._schedule.remove((expr, callback))
        logger.debug("cron callback unschedule")
