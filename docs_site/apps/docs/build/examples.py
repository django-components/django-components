"""
Pre-render examples to static HTML files at build time.

For each discovered example:
- Renders the full page via the Page component's as_view()
- For fragment examples, also renders each fragment variant to a sub-path

The pre-rendered files are what the static site serves when users interact
with live demos (clicking "Load Fragment" buttons, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.test import RequestFactory

from django_components import get_component_url

if TYPE_CHECKING:
    from apps.docs.examples import ExampleInfo


def pre_render_examples(
    output_dir: Path,
    registry: dict[str, ExampleInfo],
    *,
    examples_to_render: list[str] | None = None,
) -> tuple[int, int]:
    """
    Pre-render example pages and fragments to static HTML files.

    Each example gets its full page rendered via Component.as_view().
    Fragment examples (those with DocsExample.fragments) additionally get
    each variant rendered with the declared query params, so the static
    site can serve them when users click "Load Fragment" buttons.

    Output layout:
        <output_dir>/examples/<name>/index.html              - full page
        <output_dir>/examples/<name>/<variant>/index.html    - fragment response

    Returns (rendered_count, error_count).
    """
    factory = RequestFactory()
    rendered = 0
    errors = 0

    names = examples_to_render if examples_to_render is not None else list(registry.keys())

    for name in names:
        info = registry.get(name)
        if info is None:
            errors += 1
            continue

        examples_output = output_dir / "examples" / name

        # Render the full page (every example gets this).
        # For fragment examples, rewrite get_component_url() outputs to static
        # paths so the fragment buttons work on the static site.
        try:
            full_page_html = _render_page(factory, info)
            if info.has_fragments:
                full_page_html = _rewrite_fragment_urls(full_page_html, info)
            _write_file(examples_output / "index.html", full_page_html)
            rendered += 1
        except Exception as e:
            print(f"  Example {name} full page error: {e}")
            errors += 1
            continue

        # For fragment examples, also render each declared variant.
        # E.g. fragments = {"alpine": {"type": "alpine"}} produces
        # examples/fragments/alpine/index.html with the alpine fragment response.
        if info.has_fragments:
            for variant_name, query_params in info.fragments.items():
                try:
                    fragment_html = _render_page(factory, info, query=query_params)
                    _write_file(examples_output / variant_name / "index.html", fragment_html)
                    rendered += 1
                except Exception as e:
                    print(f"  Example {name} fragment {variant_name} error: {e}")
                    errors += 1

    return rendered, errors


def examples_index_markdown(registry: dict[str, ExampleInfo]) -> str:
    """
    Markdown source for the /examples/ index page.

    A plain linked list for now, so the chrome's "Examples" link resolves in
    the built site; the proper card-gallery page comes with the post-cutover
    examples work (spike 11.11 section 4.1).
    """
    lines = [
        "# Examples",
        "",
        "Runnable demos of django-components features. Each example opens as a",
        "standalone live page.",
        "",
    ]
    lines.extend(f"* [{name}]({name}/)" for name in sorted(registry))
    return "\n".join(lines) + "\n"


def _render_page(
    factory: RequestFactory,
    info: ExampleInfo,
    *,
    query: dict | None = None,
) -> str:
    """
    Render an example page by calling its View.get() through as_view().

    For fragment variants, pass query params (e.g. {"type": "alpine"}) so the
    View returns the fragment response instead of the full page.
    """
    url = f"/examples/{info.name}/"

    # Build a fake GET request with optional query params for fragment variants
    request = factory.get(url, data=query or {})

    # as_view() returns a callable that dispatches to View.get()
    view_fn = info.page_cls.as_view()
    response = view_fn(request)

    # TemplateResponse needs an explicit .render() before .content is available
    if hasattr(response, "render"):
        response.render()
    return response.content.decode("utf-8")


def _rewrite_fragment_urls(page_html: str, info: ExampleInfo) -> str:
    """
    Replace get_component_url() outputs with static file paths.

    For each fragment variant, call get_component_url() with the same query
    params the example uses at runtime to get the exact URL string that
    appears in the rendered HTML, then replace it with the static path.
    """
    for variant_name, query_params in info.fragments.items():
        original_url = get_component_url(info.page_cls, query=query_params)
        static_url = f"/examples/{info.name}/{variant_name}/"
        page_html = page_html.replace(original_url, static_url)
    return page_html


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
