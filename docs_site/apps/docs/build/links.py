"""
Internal markdown-link rewriting.

Existing docs author internal links as `[X](foo/bar.md)`, but the build uses
clean URLs (`foo.md` -> `/foo/`), so every page lives one directory deeper than
its source. A raw `.md` href would not resolve in the browser. This pass rewrites
each internal `.md` link to a relative URL that resolves correctly under the
clean-URL scheme.

Links that are already clean URLs (`../other/`), external (`https://...`),
anchors (`#section`), or non-`.md` are left untouched.

Example, in a page built from `content/test/pipeline_test.md` (served at
`/test/pipeline_test/`):

    [another page](./other.md)   ->  [another page](../other/)
    [another page](../other/)    ->  unchanged (already a clean URL)
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path
from urllib.parse import urlparse

from .paths import md_to_url

# Matches the href attribute of an anchor in the rendered HTML.
# python-markdown / Pygments emit double-quoted hrefs; code examples are
# HTML-escaped (&quot;), so this only matches real anchor attributes.
_HREF_RE = re.compile(r'href="([^"]*)"')


def rewrite_internal_md_links(html: str, *, source_path: Path, content_dir: Path) -> str:
    """
    Rewrite internal `.md` links in rendered HTML to clean relative URLs.

    Returns the HTML unchanged if the source file is not under content_dir
    (e.g. when build_one is run on a file outside the content tree).
    """
    content_root = content_dir.resolve()
    try:
        page_rel = source_path.resolve().relative_to(content_root)
    except ValueError:
        return html

    page_url = "/" + md_to_url(page_rel)  # e.g. "/test/pipeline_test/"
    source_dir = source_path.resolve().parent

    def replace(match: re.Match) -> str:
        href = match.group(1)
        rewritten = _rewrite_one(href, page_url=page_url, source_dir=source_dir, content_root=content_root)
        return f'href="{rewritten}"'

    return _HREF_RE.sub(replace, html)


def _rewrite_one(href: str, *, page_url: str, source_dir: Path, content_root: Path) -> str:
    parsed = urlparse(href)

    # Leave external links, schemes, protocol-relative, and anchor-only links alone
    if parsed.scheme or parsed.netloc or not parsed.path:
        return href

    # Only `.md` links need rewriting; clean URLs and other paths pass through
    if not parsed.path.endswith(".md"):
        return href

    # Resolve the target's source path (absolute links are content-root-relative)
    if parsed.path.startswith("/"):
        target_abs = (content_root / parsed.path.lstrip("/")).resolve()
    else:
        target_abs = (source_dir / parsed.path).resolve()

    # If the link points outside the content tree, leave it untouched
    try:
        target_rel = target_abs.relative_to(content_root)
    except ValueError:
        return href

    target_url = "/" + md_to_url(target_rel)  # e.g. "/test/other/"

    # Relative href from the current page's URL directory to the target
    rel = posixpath.relpath(target_url, page_url)
    if target_url.endswith("/") and not rel.endswith("/"):
        rel += "/"

    if parsed.fragment:
        rel += "#" + parsed.fragment

    return rel
