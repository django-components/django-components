"""
Sphinx ``objects.inv`` inventories for external cross-references (feature 4.20).

The old mkdocstrings setup auto-linked stdlib + Django types (``Context``,
``Any``, ``Mapping``, ...) by reading those projects' ``objects.inv`` files. We
replicate that: download (and cache) each inventory, parse it into a
``canonical_path -> URL`` map, and merge them.

Network is optional: if an inventory can't be fetched (offline, CI without
egress), its entries are simply absent and those types render unlinked rather
than failing the build. We also *emit* our own inventory for linkbacks
(feature 4.22) - see ``build_objects_inv``.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
import urllib.request
import zlib
from functools import lru_cache
from pathlib import Path

# Version-pinned doc sources (mirrors the old mkdocs.yml inventories block).
_PYTHON_DOCS = "https://docs.python.org/3.13/"
_DJANGO_DOCS = "https://docs.djangoproject.com/en/5.2/"
_INVENTORIES = (
    (_PYTHON_DOCS + "objects.inv", _PYTHON_DOCS),
    (_DJANGO_DOCS + "_objects/", _DJANGO_DOCS),
)

_INV_LINE = re.compile(r"^(?P<name>.+?)\s+\S+:\S+\s+-?\d+\s+(?P<uri>\S+)\s+.*$")


def parse_objects_inv(data: bytes, base_url: str) -> dict[str, str]:
    """Parse a Sphinx v2 ``objects.inv`` payload into ``name -> absolute URL``."""
    # Header is 4 newline-terminated plaintext lines; the rest is zlib-compressed.
    parts = data.split(b"\n", 4)
    if len(parts) < 5 or not parts[0].startswith(b"# Sphinx inventory version 2"):
        return {}
    try:
        payload = zlib.decompress(parts[4]).decode("utf-8")
    except zlib.error:
        return {}

    base = base_url.rstrip("/") + "/"
    result: dict[str, str] = {}
    for line in payload.splitlines():
        match = _INV_LINE.match(line)
        if not match:
            continue
        name = match.group("name")
        # A trailing "$" in the URI is shorthand for the object's own name.
        uri = match.group("uri").replace("$", name)
        result.setdefault(name, base + uri)
    return result


def _cache_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "djc-docs-inventories"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_one(url: str, base_url: str) -> dict[str, str]:
    cache_file = _cache_dir() / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".inv")
    if cache_file.is_file():
        return parse_objects_inv(cache_file.read_bytes(), base_url)
    try:
        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 -- pinned https doc URLs
            data = response.read()
    except Exception:
        return {}
    cache_file.write_bytes(data)
    return parse_objects_inv(data, base_url)


@lru_cache(maxsize=1)
def external_inventory() -> dict[str, str]:
    """Merged ``canonical_path -> URL`` map for Python stdlib + Django."""
    merged: dict[str, str] = {}
    for url, base_url in _INVENTORIES:
        for name, target in _load_one(url, base_url).items():
            merged.setdefault(name, target)
    return merged


def build_objects_inv(entries: list[tuple[str, str]], *, project: str, version: str) -> bytes:
    """
    Build a Sphinx v2 ``objects.inv`` for our own symbols (feature 4.22).

    ``entries`` is a list of ``(canonical_name, relative_url)``. Other docs sites
    can then cross-link into ours with the same ``[X][path]`` convention.
    """
    header = (
        f"# Sphinx inventory version 2\n"
        f"# Project: {project}\n"
        f"# Version: {version}\n"
        f"# The remainder of this file is compressed using zlib.\n"
    ).encode()
    lines = "".join(f"{name} py:obj -1 {url} -\n" for name, url in sorted(entries))
    return header + zlib.compress(lines.encode("utf-8"), 9)
