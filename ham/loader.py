import importlib.util
import logging
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from ham.context import Context

logger = logging.getLogger(__name__)


class LoadError(Exception): ...


@dataclass(slots=True)
class Script:
    ctx: Context
    mtime: int
    module: ModuleType
    path: Path


class Loader:
    _path: Path
    _context: Callable[[], Context]
    _poll_interval: float
    _scripts: dict[Path, Script]
    _failed: dict[Path, int]
    _timer: threading.Event

    def __init__(
        self,
        path: Path,
        context: Callable[[], Context],
        poll_interval: float = 1.0,
    ):
        self._path = path
        self._context = context
        self._poll_interval = poll_interval
        self._scripts = {}
        self._failed = {}
        self._timer = threading.Event()

    def run(self) -> None:
        while not self._timer.wait(self._poll_interval):
            self._poll()

    def cancel(self) -> None:
        self._timer.set()

    def _poll(self) -> None:
        seen: set[Path] = set()
        for file in sorted(self._path.glob("*.py")):
            if file.name in ("__init__.py", "__main__.py"):
                continue
            seen.add(file)
            try:
                mtime = int(file.stat().st_mtime)
                # try to reload previously failed script only if it has been changed
                if file in self._failed and mtime <= self._failed[file]:
                    continue
                script = self._scripts.get(file)
                if script is not None and mtime <= script.mtime:
                    continue
                self._load(file, mtime)
                if file in self._failed:
                    del self._failed[file]
                logger.info("(re)loaded script %s", file)
            except FileNotFoundError:
                logger.exception("failed to load script: not found")
            except LoadError as exc:
                self._failed[file] = mtime
                logger.exception("failed to load script: %s", exc)

        for file in self._failed.keys() - seen:
            del self._failed[file]

        # unload deleted scripts
        for file in self._scripts.keys() - seen:
            self._unload(file)
            logger.info("unloaded script %s", file)

    def _load(self, file: Path, mtime: int) -> None:
        assert __spec__ is not None
        # each reload needs unique module name in order to avoid caching
        name = f"{__spec__.parent}.scripts.{file.stem}.{mtime}"
        spec = importlib.util.spec_from_file_location(name, file)
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        # mirror import machinery so that module is registered before it body runs, see
        # https://docs.python.org/3/reference/import.html#loading
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            del sys.modules[name]
            raise LoadError("execution error") from exc

        ctx = self._context()
        try:
            setup = getattr(module, "setup", None)
            assert setup is not None
            setup(ctx)
        except Exception as exc:
            ctx.teardown()
            del sys.modules[name]
            raise LoadError("setup error") from exc

        # unload the previous script version only after the next one has been loaded
        if file in self._scripts:
            self._unload(file)

        self._scripts[file] = Script(path=file, mtime=mtime, module=module, ctx=ctx)

    def _unload(self, file: Path) -> None:
        script = self._scripts.pop(file)
        script.ctx.teardown()
        del sys.modules[script.module.__name__]
