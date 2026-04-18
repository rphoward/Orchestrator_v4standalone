"""Shared prompt file cache with explicit invalidation semantics."""

from __future__ import annotations

import os


class CachedPromptFileReader:
    """Caches UTF-8 prompt files under one prompts root."""

    def __init__(self, prompts_root: str) -> None:
        self._prompts_root = os.path.realpath(prompts_root)
        self._cache_by_path: dict[str, str] = {}

    def read_or_empty(self, relative: str) -> str:
        path = self._resolve_under_root(relative)
        if not path:
            return ""
        return self._read_cached_path(path, missing_returns_empty=True)

    def read_or_raise(self, relative: str) -> str:
        path = self._resolve_under_root(relative)
        if not path:
            raise ValueError(f"Invalid prompt file path: {relative!r}")
        return self._read_cached_path(path, missing_returns_empty=False)

    def invalidate(self, relative: str | None = None) -> None:
        if relative is None:
            self._cache_by_path.clear()
            return
        path = self._resolve_under_root(relative)
        if not path:
            return
        self._cache_by_path.pop(path, None)

    def _read_cached_path(self, path: str, *, missing_returns_empty: bool) -> str:
        cached = self._cache_by_path.get(path)
        if cached is not None:
            return cached
        try:
            with open(path, encoding="utf-8") as f:
                body = f.read()
        except FileNotFoundError:
            if not missing_returns_empty:
                relative = os.path.relpath(path, self._prompts_root).replace("\\", "/")
                raise ValueError(f"Prompt file not found: {relative}") from None
            body = ""
        self._cache_by_path[path] = body
        return body

    def _resolve_under_root(self, relative: str) -> str | None:
        path = os.path.realpath(os.path.join(self._prompts_root, relative))
        if not path.startswith(self._prompts_root + os.sep):
            return None
        return path
