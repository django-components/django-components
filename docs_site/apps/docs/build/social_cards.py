"""
Social card generation: per-page 1200x630 OG image PNGs (Phase 5c, Chunk 4).

For each indexable page, the OgCard component is rendered to standalone HTML and
screenshotted to a PNG with Playwright, then the page's og:image / twitter:image
meta tags are swapped from the site-level default to the per-page card.

Design notes:
- Robust to a missing browser. Pages render with a valid default OG image
  (pipeline.default_og_image_url); a card only *replaces* it where one was
  produced. If Playwright or Chromium is unavailable, generation is skipped and
  every page keeps the working default - no broken images, no failed build.
- Content-addressed cache. A card is keyed by hash(template + title +
  description + section); the PNG is stored as `<hash>.png` in a persistent
  gitignored cache dir. build_site wipes the output each build, but the cache
  survives, so unchanged cards are copied (no browser launch) and only changed
  pages re-render. A fully-cached build needs no Chromium at all.

Specs: DESIGN_spike_9.md section 2.4 (5c.4/5c.5/5c.6), DESIGN_spike_12.md 2.A.4 (5c.3).
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

from apps.docs.build.frontmatter import PageMeta, parse_page
from apps.docs.build.nav import load_nav
from apps.docs.build.pipeline import default_og_image_url
from apps.docs.build.site_index import SiteIndex

if TYPE_CHECKING:
    from pathlib import Path

    from apps.docs.build.nav import NavTree
    from apps.docs.build.site_index import PageRecord

# Default location of the persistent card cache (gitignored via `.cache`).
DEFAULT_CACHE_DIR = settings.BASE_DIR / ".cache" / "og"

OG_VIEWPORT = {"width": 1200, "height": 630}


@dataclass
class SocialCardOutcome:
    eligible: int = 0  # pages that should carry a generated card
    rendered: int = 0  # cards freshly screenshotted this run
    cached: int = 0  # cards reused from the persistent cache
    placed: int = 0  # cards copied into the output + og:image rewritten
    skipped_reason: str = ""  # set when generation was skipped wholesale


@dataclass
class _Card:
    page_file: Path
    html: str
    title: str
    description: str
    section: str
    digest: str
    png_rel: str


def og_image_rel(page_url: str) -> str:
    """Output-relative PNG path for a page's card, e.g. '/docs/foo/' -> 'og/docs/foo.png'."""
    slug = page_url.strip("/") or "index"
    return f"og/{slug}.png"


def generate_social_cards(
    output_dir: Path,
    content_dir: Path,
    *,
    site_url: str,
    cache_dir: Path | None = None,
    log: Callable[[str], None] = lambda _msg: None,
) -> SocialCardOutcome:
    """Render/refresh per-page social cards and point each page's og:image at its card."""
    site_url = site_url.rstrip("/")
    default_url = default_og_image_url()
    cache_dir = cache_dir or DEFAULT_CACHE_DIR

    nav = load_nav(content_dir / "_nav.yml")
    template_version = _template_version()
    index = SiteIndex(output_dir)

    work = [
        card
        for page in index.pages
        if (card := _card_for(page, output_dir, nav, template_version, default_url)) is not None
    ]
    outcome = SocialCardOutcome(eligible=len(work))
    if not work:
        return outcome

    cache_dir.mkdir(parents=True, exist_ok=True)
    todo = [c for c in work if not (cache_dir / f"{c.digest}.png").is_file()]
    outcome.cached = len(work) - len(todo)

    if todo:
        outcome.rendered, reason = _render_cards(todo, cache_dir, log)
        if reason:
            outcome.skipped_reason = reason

    for card in work:
        cached_png = cache_dir / f"{card.digest}.png"
        if not cached_png.is_file():
            continue  # render was skipped (no browser) - leave the default og:image
        dest = output_dir / card.png_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached_png, dest)
        card.page_file.write_text(card.html.replace(default_url, f"{site_url}/{card.png_rel}"), encoding="utf-8")
        outcome.placed += 1

    _prune_cache(cache_dir, {c.digest for c in work})
    return outcome


def _card_for(
    page: PageRecord, output_dir: Path, nav: NavTree, template_version: str, default_url: str
) -> _Card | None:
    """Build the work item for a page, or None if it shouldn't get a card."""
    if not page.is_doc_page or page.is_redirect_stub or "noindex" in page.robots.lower():
        return None
    page_file = output_dir / page.rel_path
    html = page_file.read_text(encoding="utf-8")
    # A page with a custom front-matter og_image won't carry the default URL;
    # leave it untouched rather than overwrite an intentional image.
    if default_url not in html:
        return None

    meta = _page_meta(output_dir, page.url)
    title = (meta.title if meta else "") or "django-components"
    description = meta.description if meta else ""
    section = _section_label(nav, page.url)
    digest = _card_hash(template_version, title, description, section)
    return _Card(
        page_file=page_file,
        html=html,
        title=title,
        description=description,
        section=section,
        digest=digest,
        png_rel=og_image_rel(page.url),
    )


def _page_meta(output_dir: Path, url: str) -> PageMeta | None:
    companion = output_dir / url.strip("/") / "index.md"
    return parse_page(companion.read_text(encoding="utf-8")) if companion.is_file() else None


def _section_label(nav: NavTree, url: str) -> str:
    """Eyebrow label for the card: the page's top nav section (e.g. 'Concepts')."""
    for label, _path in nav.find_breadcrumbs(url):
        if label and label.lower() != "home":
            return label
    return "Documentation"


def _template_version() -> str:
    from apps.docs.components.og_card.og_card import OgCard  # noqa: PLC0415

    return hashlib.sha256(OgCard.template.encode("utf-8")).hexdigest()[:16]


def _card_hash(template_version: str, title: str, description: str, section: str) -> str:
    raw = f"{template_version}\x00{title}\x00{description}\x00{section}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _render_cards(cards: list[_Card], cache_dir: Path, log: Callable[[str], None]) -> tuple[int, str]:
    """
    Screenshot each card to `<cache_dir>/<hash>.png`. Returns (rendered, reason).

    `reason` is non-empty when rendering was skipped wholesale (no Playwright /
    no Chromium); the caller then leaves the default OG image on every page.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        log("Playwright not installed; skipping social cards (pages keep the default OG image)")
        return 0, "playwright-missing"

    from apps.docs.components.og_card.og_card import OgCard  # noqa: PLC0415

    rendered = 0
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as e:  # any launch failure (no browser binary, sandbox) is a graceful skip
            log(f"Chromium unavailable ({type(e).__name__}); skipping social cards")
            return 0, "chromium-missing"
        try:
            page = browser.new_page(viewport=OG_VIEWPORT, device_scale_factor=1)  # type: ignore[arg-type]
            for card in cards:
                markup = OgCard.render(
                    kwargs={"title": card.title, "description": card.description, "section": card.section}
                )
                page.set_content(markup, wait_until="load")
                page.screenshot(path=str(cache_dir / f"{card.digest}.png"))
                rendered += 1
        finally:
            browser.close()
    return rendered, ""


def _prune_cache(cache_dir: Path, used: set[str]) -> None:
    """Drop cached PNGs no longer referenced by any page, keeping the cache bounded."""
    for png in cache_dir.glob("*.png"):
        if png.stem not in used:
            png.unlink()
