"""
Shared post-build HTML walker for the docs-site guardrails.

The SiteIndex parses every built HTML file exactly once and exposes a typed
view of each page (links, anchors, assets, images, headings, redirect info).
Every post-build guard reads from this index instead of re-parsing the site,
so the whole guardrail suite pays the lxml parse cost a single time.

Spec: docs_site/design/DESIGN_spike_10.md section 6 (SiteIndex) and section 3
(per-guard consumers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

import lxml.html  # type: ignore[import-untyped]
from lxml.etree import LxmlError  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pathlib import Path

# URL schemes / prefixes that mark a link or asset as external (not a local
# path the link/asset guards should resolve against the build output).
_EXTERNAL_SCHEMES = ("http://", "https://", "//", "mailto:", "tel:", "javascript:", "data:")


@dataclass(frozen=True)
class LinkRef:
    """A single `<a href>` on a page, pre-parsed into path + fragment."""

    href: str  # the raw href attribute value
    target: str  # path portion only (no fragment), may be relative or absolute
    anchor: str  # the #fragment, or "" if none

    @property
    def is_external(self) -> bool:
        return self.href.startswith(_EXTERNAL_SCHEMES)

    @property
    def is_anchor_only(self) -> bool:
        return self.href.startswith("#")


@dataclass(frozen=True)
class AssetRef:
    """A local asset reference (`<img src>`, `<script src>`, `<link href>`)."""

    tag: str  # "img" | "script" | "link"
    src: str

    @property
    def is_external(self) -> bool:
        return self.src.startswith(_EXTERNAL_SCHEMES)


@dataclass(frozen=True)
class ImageRef:
    """An `<img>` with its alt text (None = attribute absent, "" = empty)."""

    src: str
    alt: str | None


@dataclass(frozen=True)
class Heading:
    """A rendered heading: its level (1-6) and id (may be "")."""

    level: int
    id: str
    text: str


@dataclass
class PageRecord:
    """Everything the guards need to know about one built HTML page."""

    rel_path: PurePosixPath  # path relative to the build dir, e.g. "concepts/foo/index.html"
    url: str  # clean URL form, e.g. "/concepts/foo/"
    parse_error: str | None = None
    is_doc_page: bool = False  # rendered through DocPage (vs an example demo / fragment)
    is_redirect_stub: bool = False
    redirect_target: str | None = None
    robots: str = ""  # <meta name="robots"> content, e.g. "index,follow"
    canonical: str = ""  # <link rel="canonical"> href
    anchors: set[str] = field(default_factory=set)  # id= values
    name_aliases: set[str] = field(default_factory=set)  # legacy <a name="..."> values
    links: list[LinkRef] = field(default_factory=list)
    assets: list[AssetRef] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    headings: list[Heading] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    # Raw text of every <script type="application/ld+json"> block (for the
    # json_ld guard, which validates the structured data).
    jsonld_blocks: list[str] = field(default_factory=list)

    @property
    def h1_count(self) -> int:
        return sum(1 for h in self.headings if h.level == 1)

    @property
    def label(self) -> str:
        """A human-friendly identifier for guard messages."""
        return str(self.rel_path)


class SiteIndex:
    """Parses a built docs site once and indexes every page for the guards."""

    def __init__(self, build_dir: Path) -> None:
        self.build_dir = build_dir
        self.pages: list[PageRecord] = []
        self._by_rel: dict[PurePosixPath, PageRecord] = {}
        self.built_page_paths: set[PurePosixPath] = set()

        for html_path in sorted(build_dir.rglob("*.html")):
            rel = PurePosixPath(html_path.relative_to(build_dir).as_posix())
            record = self._parse(html_path, rel)
            self.pages.append(record)
            self._by_rel[rel] = record
            self.built_page_paths.add(rel)

    def get_page(self, rel: PurePosixPath | None) -> PageRecord | None:
        return self._by_rel.get(rel) if rel is not None else None

    def _parse(self, path: Path, rel: PurePosixPath) -> PageRecord:
        text = path.read_text(encoding="utf-8")
        record = PageRecord(rel_path=rel, url=_rel_to_url(rel))

        # Parse leniently. We deliberately do NOT use recover=False: libxml2's
        # strict HTML parser treats `<a id="X" name="X">` as defining ID "X"
        # twice (HTML4 shares the id/name namespace for <a>), which pymdownx
        # emits on every code line anchor - a false positive on nearly every
        # page. Real duplicate `id=` attributes are detected precisely by the
        # Counter in _extract (record.duplicate_ids).
        try:
            dom = lxml.html.fromstring(text)
        except LxmlError as e:
            record.parse_error = str(e)
            return record  # unparseable; nothing more to extract

        self._extract(dom, record)
        return record

    def _extract(self, dom: lxml.html.HtmlElement, record: PageRecord) -> None:
        seen_ids: dict[str, int] = {}
        for el in dom.iter():
            tag = el.tag
            if not isinstance(tag, str):
                continue  # comments / processing instructions

            el_id = el.get("id")
            if el_id:
                record.anchors.add(el_id)
                seen_ids[el_id] = seen_ids.get(el_id, 0) + 1

            if tag == "a":
                name = el.get("name")
                if name:
                    record.name_aliases.add(name)
                href = el.get("href")
                if href is not None:
                    record.links.append(_parse_link(href))
            elif tag == "img":
                src = el.get("src") or ""
                record.assets.append(AssetRef(tag="img", src=src))
                record.images.append(ImageRef(src=src, alt=el.get("alt")))
            elif tag == "script":
                src = el.get("src")
                if src:
                    record.assets.append(AssetRef(tag="script", src=src))
                elif (el.get("type") or "").lower() == "application/ld+json":
                    record.jsonld_blocks.append(el.text_content() or "")
            elif tag == "link":
                href = el.get("href")
                if href:
                    record.assets.append(AssetRef(tag="link", src=href))
                    if (el.get("rel") or "").lower() == "canonical":
                        record.canonical = href
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                record.headings.append(
                    Heading(level=int(tag[1]), id=el.get("id") or "", text=(el.text_content() or "").strip())
                )
            elif tag == "meta":
                self._read_meta(el, record)

        record.duplicate_ids = [i for i, n in seen_ids.items() if n > 1]

    @staticmethod
    def _read_meta(el: lxml.html.HtmlElement, record: PageRecord) -> None:
        # Pages rendered through DocPage carry this generator meta; example demo
        # pages and fragment responses (rendered via as_view) do not. Content
        # guards (single-h1, headings, alt-text) only apply to real doc pages.
        if el.get("name") == "generator" and "django-components docs builder" in (el.get("content") or ""):
            record.is_doc_page = True
        if el.get("name") == "robots":
            record.robots = el.get("content") or ""
        if (el.get("http-equiv") or "").lower() == "refresh":
            content = el.get("content") or ""
            _, _, url_part = content.partition("url=")
            if url_part:
                record.is_redirect_stub = True
                record.redirect_target = url_part.strip()

    def resolve_link(self, page_rel: PurePosixPath, target: str) -> PurePosixPath | None:
        """
        Resolve a link target (path only, no fragment) to a built page path.

        Handles clean URLs (`/foo/` -> `foo/index.html`) and relative links
        resolved against the source page's directory. Returns None if the
        target can't be matched to any built page.
        """
        target = unquote(target)
        if target.startswith("/"):
            base = PurePosixPath(target.lstrip("/"))
        else:
            base = PurePosixPath(page_rel).parent / target
        # Normalize away "." and ".." segments
        parts: list[str] = []
        for seg in base.parts:
            if seg == ".":
                continue
            if seg == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(seg)
        normalized = "/".join(parts)

        for candidate in _candidate_paths(normalized):
            cp = PurePosixPath(candidate)
            if cp in self.built_page_paths:
                return cp
        return None


def _candidate_paths(normalized: str) -> list[str]:
    """Clean-URL candidates for a normalized link target."""
    normalized = normalized.strip("/")
    if not normalized:
        return ["index.html"]
    candidates = [normalized]
    if normalized.endswith(".html"):
        return candidates
    candidates.append(f"{normalized}/index.html")
    candidates.append(f"{normalized}.html")
    return candidates


def _parse_link(href: str) -> LinkRef:
    if href.startswith("#"):
        return LinkRef(href=href, target="", anchor=href[1:])
    parsed = urlparse(href)
    return LinkRef(href=href, target=parsed.path, anchor=parsed.fragment)


def _rel_to_url(rel: PurePosixPath) -> str:
    """Convert a built file path to its clean URL (foo/index.html -> /foo/)."""
    s = rel.as_posix()
    if s == "index.html":
        return "/"
    if s.endswith("/index.html"):
        return "/" + s[: -len("index.html")]
    if s.endswith(".html"):
        return "/" + s[: -len(".html")] + "/"
    return "/" + s
