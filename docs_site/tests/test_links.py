"""
Unit tests for link post-processing (apps/docs/build/links.py).

Focuses on mark_external_links - the pass that makes off-site links open in a
new tab. Internal .md link rewriting is covered indirectly by the render
snapshot and the post-build internal_link guard.
"""

from __future__ import annotations

from apps.docs.build.links import mark_external_links


def test_external_https_link_opens_new_tab() -> None:
    out = mark_external_links('<a href="https://example.com">x</a>')
    assert out == '<a href="https://example.com" target="_blank" rel="noopener">x</a>'


def test_protocol_relative_link_is_external() -> None:
    out = mark_external_links('<a href="//example.com/x">x</a>')
    assert 'target="_blank"' in out
    assert 'rel="noopener"' in out


def test_internal_relative_links_untouched() -> None:
    for href in ("../foo/", "/docs/reference/", "#section", "img.png"):
        markup = f'<a href="{href}">x</a>'
        assert mark_external_links(markup) == markup


def test_mailto_and_tel_untouched() -> None:
    for href in ("mailto:hi@example.com", "tel:+123456789"):
        markup = f'<a href="{href}">x</a>'
        assert mark_external_links(markup) == markup


def test_existing_target_is_respected() -> None:
    # An explicit target (e.g. the chrome GitHub link pattern) is left as-is,
    # so we never produce a duplicate target attribute.
    markup = '<a href="https://example.com" target="_self">x</a>'
    assert mark_external_links(markup) == markup


def test_existing_rel_is_not_duplicated() -> None:
    # target gets added, but the existing rel is preserved (no second rel attr).
    out = mark_external_links('<a href="https://example.com" rel="nofollow">x</a>')
    assert out.count("rel=") == 1
    assert 'target="_blank"' in out
    assert 'rel="nofollow"' in out


def test_multiple_links_in_one_string() -> None:
    html = 'see <a href="https://a.com">a</a> and <a href="../b/">b</a>'
    out = mark_external_links(html)
    assert out == 'see <a href="https://a.com" target="_blank" rel="noopener">a</a> and <a href="../b/">b</a>'
