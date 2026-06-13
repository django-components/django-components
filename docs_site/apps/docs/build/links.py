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

# Matches src attributes (images) in the rendered HTML.
_SRC_RE = re.compile(r'src="([^"]*)"')


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

    def replace_href(match: re.Match) -> str:
        href = match.group(1)
        rewritten = _rewrite_one(href, page_url=page_url, source_dir=source_dir, content_root=content_root)
        return f'href="{rewritten}"'

    def replace_src(match: re.Match) -> str:
        src = match.group(1)
        rewritten = _rewrite_asset(src, page_url=page_url, source_dir=source_dir, content_root=content_root)
        return f'src="{rewritten}"'

    html = _HREF_RE.sub(replace_href, html)
    return _SRC_RE.sub(replace_src, html)


def _rewrite_one(href: str, *, page_url: str, source_dir: Path, content_root: Path) -> str:
    parsed = urlparse(href)

    # Leave external links, schemes, protocol-relative, and anchor-only links alone
    if parsed.scheme or parsed.netloc or not parsed.path:
        return href

    # Non-`.md` links: clean URLs pass through, but links that target a real
    # asset file (e.g. a clickable screenshot) need the same depth correction
    # as image srcs
    if not parsed.path.endswith(".md"):
        return _rewrite_asset(href, page_url=page_url, source_dir=source_dir, content_root=content_root)

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


def _rewrite_asset(ref: str, *, page_url: str, source_dir: Path, content_root: Path) -> str:
    """
    Rewrite a relative asset reference (image etc.) authored against the source
    tree into a URL relative to the page's clean URL.

    Pages live one directory deeper in the URL space than in the source tree
    (`foo.md` -> `/foo/`), so a source-relative `../images/x.png` needs one more
    `../` in the built page. Only refs that resolve to a real file inside the
    content tree are touched - clean URLs, external refs, and absolute paths
    pass through.
    """
    parsed = urlparse(ref)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
        return ref

    target_abs = (source_dir / parsed.path).resolve()
    if not target_abs.is_file():
        return ref
    try:
        target_rel = target_abs.relative_to(content_root)
    except ValueError:
        return ref

    target_url = "/" + target_rel.as_posix()
    rel = posixpath.relpath(target_url, page_url)
    if parsed.fragment:
        rel += "#" + parsed.fragment
    return rel
