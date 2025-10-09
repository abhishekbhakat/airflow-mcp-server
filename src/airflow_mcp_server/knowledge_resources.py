"""Helpers for registering resources-folder Markdown files."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

_MARKDOWN_EXTENSIONS = {".md", ".markdown"}


def _sort_key(path: Path) -> tuple[str, int, str, str]:
    return (
        path.stem.lower(),
        len(path.suffix),
        path.suffix.lower(),
        path.name.lower(),
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "resource"


def _unique_slug(base: str, existing: set[str]) -> str:
    if base not in existing:
        existing.add(base)
        return base

    idx = 2
    while True:
        candidate = f"{base}-{idx}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        idx += 1


def _extract_title(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or None
    except Exception as exc:
        logger.debug("Failed to extract title from %s: %s", path, exc)
    return None


def _iter_markdown_files(root: Path) -> Iterable[Path]:
    candidates: list[Path] = []

    for entry in root.iterdir():
        try:
            resolved = entry.resolve(strict=True)
        except FileNotFoundError:
            logger.warning("Skipping resources file that does not exist: %s", entry)
            continue

        if resolved.is_dir():
            logger.debug("Skipping sub-directory in resources folder: %s", resolved)
            continue

        if resolved.suffix.lower() not in _MARKDOWN_EXTENSIONS:
            logger.debug("Skipping non-Markdown resources file: %s", resolved)
            continue

        if resolved.is_symlink():
            try:
                if not resolved.is_relative_to(root):
                    logger.warning("Skipping symlink outside resources folder: %s", resolved)
                    continue
            except AttributeError:
                if root not in resolved.parents:
                    logger.warning("Skipping symlink outside resources folder: %s", resolved)
                    continue

        candidates.append(resolved)

    for resolved in sorted(candidates, key=_sort_key):
        yield resolved


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def load_knowledge_resources(resources_dir: str | None) -> list[tuple[str, str, Callable[[], str], str]]:
    """Discover Markdown knowledge resources.

    Returns a list of tuples ``(uri, title, reader, mime_type)``.
    """

    if not resources_dir:
        return []

    root = Path(resources_dir).expanduser()
    try:
        root_resolved = root.resolve(strict=True)
    except FileNotFoundError:
        logger.warning("Resources directory not found: %s", resources_dir)
        return []

    if not root_resolved.is_dir():
        logger.warning("Resources directory is not a directory: %s", resources_dir)
        return []

    slugs: set[str] = set()
    discovered: list[tuple[str, str, Callable[[], str], str]] = []

    for markdown_file in _iter_markdown_files(root_resolved):
        relative_name = markdown_file.stem
        slug = _unique_slug(_slugify(relative_name), slugs)
        uri = f"resource://knowledge/{slug}"
        title = _extract_title(markdown_file)

        display_title = title or relative_name.replace("_", " ").strip()

        discovered.append((uri, display_title, lambda p=markdown_file: _read_file(p), "text/markdown"))
        logger.debug("Registered knowledge resource %s for %s", uri, markdown_file)

    if not discovered:
        logger.info("Resources directory contained no Markdown files: %s", resources_dir)

    return discovered
