"""Tests for the Phase 5c Chunk 6 anchor-deprecation guard (feature 5c.12)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from apps.docs.build.guards import GuardContext, anchor_deprecation
from apps.docs.build.guards.base import Severity
from django.test import override_settings

PAST = date(2000, 1, 1)
FUTURE = datetime.now(tz=timezone.utc).date() + timedelta(days=3650)


def _ctx(content: Path) -> GuardContext:
    return GuardContext(
        content_dir=content,
        examples_dir=content,
        nav_path=content / "_nav.yml",
        static_dir=content / "static",
    )


def _write(content: Path, rel: str, body: str) -> None:
    path = content / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _run(content: Path) -> list:
    return list(anchor_deprecation.check(_ctx(content)))


# -- dormant until the date is configured + reached ----------------------------


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=None)
def test_noop_when_date_unset(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "See [Component](api.md#django_components.Component).")
    assert _run(tmp_path) == []


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=FUTURE)
def test_noop_before_deprecation_date(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "See [Component](api.md#django_components.Component).")
    assert _run(tmp_path) == []


# -- active after the date -----------------------------------------------------


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=PAST)
def test_flags_inline_link_fragment(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "See [Component](api.md#django_components.Component).")
    results = _run(tmp_path)
    assert len(results) == 1
    assert results[0].severity is Severity.WARNING
    assert results[0].line == 1


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=PAST)
def test_flags_reference_style_key(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "text\n\nSee [Component][django_components.Component] here.")
    results = _run(tmp_path)
    assert len(results) == 1
    assert results[0].line == 3


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=PAST)
def test_skips_inline_code_literal(tmp_path: Path) -> None:
    # The docstring guide documents the form inside backticks - not a real use.
    _write(tmp_path, "a.md", "Use `[X][django_components.X]` or the short form.")
    assert _run(tmp_path) == []


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=PAST)
def test_skips_fenced_block(tmp_path: Path) -> None:
    body = "Example:\n\n```python\n# [Component](api.md#django_components.Component)\n```\n"
    _write(tmp_path, "a.md", body)
    assert _run(tmp_path) == []


@override_settings(ANCHOR_ALIAS_DEPRECATION_DATE=PAST)
def test_short_form_is_not_flagged(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "See [Component][Component] and [Slot](#Slot).")
    assert _run(tmp_path) == []
