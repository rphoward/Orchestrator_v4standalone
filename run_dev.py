"""
Run Orchestrator v4 from this folder without ``cd``'ing to the parent directory.

Layout (standalone or full repo)::

    <import_root>/              ← child process cwd (directory that *contains* the package)
        orchestrator_v4/        ← this folder: ``bootstrap.py``, ``run_dev.py``, ``.env``
            run_dev.py
            .venv/              ← created here on first run (not portable — see below)
            ...

The interpreter needs ``import_root`` on ``sys.path`` for ``python -m orchestrator_v4....``.
This script sets the child ``cwd`` to that directory.

**Virtualenv:** If ``.venv`` is missing under this folder, this script runs ``uv venv`` and
``uv pip install -r requirements.txt``. ``uv`` must be on ``PATH``. After copying this tree to
a new machine or path, remove ``.venv`` and run again so a fresh env is created (venvs embed
absolute paths and are not portable).

``.env`` in this folder is loaded (stdlib parser, ``KEY=VALUE`` lines) before the child starts
so the child inherits keys; ``bootstrap`` also loads ``orchestrator_v4/.env`` in dev.

Usage (from ``orchestrator_v4/``)::

    python run_dev.py              # Flask UI (default port 5001)
    python run_dev.py --smoke      # bootstrap smoke (orchestrator_v4.bootstrap_smoke)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


def _package_root() -> Path:
    """Directory containing ``run_dev.py`` (the ``orchestrator_v4`` package folder)."""
    return Path(__file__).resolve().parent


def _import_root() -> Path:
    """Directory used as ``cwd`` for ``python -m orchestrator_v4.…``.

    **Nested monorepo layout:** ``…/repo/orchestrator_v4/run_dev.py`` — import root is the
    parent of ``orchestrator_v4/`` so ``orchestrator_v4`` resolves as a package directory.

    **Flat standalone layout:** ``package-dir = { \"orchestrator_v4\" = \".\" }`` in
    ``pyproject.toml`` — the package root *is* this directory; ``cwd`` must be here, not
    the parent, or ``-m orchestrator_v4.*`` will not resolve.
    """
    pkg = _package_root()
    pyproject = pkg / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except OSError:
            data = {}
        except tomllib.TOMLDecodeError:
            data = {}
        pkg_dir = (data.get("tool") or {}).get("setuptools", {}).get("package-dir")
        if isinstance(pkg_dir, dict) and pkg_dir.get("orchestrator_v4") == ".":
            return pkg
    return pkg.parent


def _load_dotenv_simple(path: Path) -> None:
    """Set missing ``os.environ`` keys from a minimal ``.env`` (no extra deps for the launcher)."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8-sig")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value


def _venv_python(package_root: Path) -> Path:
    if sys.platform == "win32":
        return package_root / ".venv" / "Scripts" / "python.exe"
    return package_root / ".venv" / "bin" / "python"


def _ensure_venv(package_root: Path) -> Path:
    """Return path to the venv interpreter, creating ``.venv`` with ``uv`` if needed."""
    vpy = _venv_python(package_root)
    if vpy.is_file():
        return vpy

    uv = shutil.which("uv")
    if not uv:
        print(
            "orchestrator_v4: no .venv found and 'uv' is not on PATH.\n"
            "Install uv (https://docs.astral.sh/uv/) or create .venv yourself:\n"
            "  uv venv && uv pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("orchestrator_v4: creating .venv with uv …", file=sys.stderr)
    subprocess.run([uv, "venv"], cwd=package_root, check=True)

    req = package_root / "requirements.txt"
    if not req.is_file():
        print(f"orchestrator_v4: missing {req}", file=sys.stderr)
        raise SystemExit(1)

    print("orchestrator_v4: installing dependencies …", file=sys.stderr)
    subprocess.run([uv, "pip", "install", "-r", str(req)], cwd=package_root, check=True)

    if not vpy.is_file():
        print(f"orchestrator_v4: expected interpreter at {vpy}", file=sys.stderr)
        raise SystemExit(1)
    return vpy


def _ensure_editable_for_flat_layout(package_root: Path, python_exe: Path) -> None:
    """Flat ``package-dir`` trees need an editable install for ``python -m orchestrator_v4.*``."""
    if _import_root() != package_root:
        return
    uv = shutil.which("uv")
    if uv:
        subprocess.run(
            [uv, "pip", "install", "-q", "-e", "."],
            cwd=package_root,
            check=True,
        )
        return
    subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-q", "-e", "."],
        cwd=package_root,
        check=True,
    )


def main() -> None:
    pkg = _package_root()
    python_exe = _ensure_venv(pkg)
    _ensure_editable_for_flat_layout(pkg, python_exe)
    _load_dotenv_simple(pkg / ".env")

    parser = argparse.ArgumentParser(
        description="Run Orchestrator v4 from the orchestrator_v4 folder (standalone-friendly)."
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run bootstrap smoke test instead of the web app.",
    )
    args = parser.parse_args()
    mod = (
        "orchestrator_v4.bootstrap_smoke"
        if args.smoke
        else "orchestrator_v4.presentation.app"
    )
    raise SystemExit(
        subprocess.run(
            [str(python_exe), "-m", mod],
            cwd=_import_root(),
            check=False,
        ).returncode
    )


if __name__ == "__main__":
    main()
