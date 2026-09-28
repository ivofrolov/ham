import importlib.util
import json
import logging
import subprocess
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
        self._requirements_mtime = None
        self._scripts = {}
        self._failed = {}
        self._timer = threading.Event()

    def run(self) -> None:
        while not self._timer.wait(self._poll_interval):
            self._poll_requirements()
            self._poll_scripts()

    def cancel(self) -> None:
        self._timer.set()
        for file in list(self._scripts):
            self._unload_script(file)

    def _poll_requirements(self) -> None:
        file = self._path / "requirements.txt"
        if not file.exists():
            return
        mtime = file.stat().st_mtime
        if self._requirements_mtime and self._requirements_mtime >= mtime:
            return
        try:
            command = (
                sys.executable, "-m", "pip", "install",
                "-qqq", "--report", "-",
                "-r", str(file),
            )  # fmt: skip
            output = subprocess.check_output(command)
        except Exception as exc:
            logger.exception("failed to install packages from %s", file)
        self._requirements_mtime = mtime
        report = json.loads(output)
        packages = [
            f"{p['metadata']['name']}=={p['metadata']['version']}"
            for p in report["install"]
        ]
        if not packages:
            return
        logger.info("packages installed from %s: %s", file, " ".join(packages))

    def _poll_scripts(self) -> None:
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
                self._load_script(file, mtime)
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
            self._unload_script(file)
            logger.info("unloaded script %s", file)

    def _load_script(self, file: Path, mtime: int) -> None:
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
            self._unload_script(file)

        self._scripts[file] = Script(path=file, mtime=mtime, module=module, ctx=ctx)

    def _unload_script(self, file: Path) -> None:
        script = self._scripts.pop(file)
        script.ctx.teardown()
        if teardown := getattr(sys.modules[script.module.__name__], "teardown", None):
            try:
                teardown()
            except Exception as exc:
                logger.warning("script teardown function failed: %s", exc)
        del sys.modules[script.module.__name__]
