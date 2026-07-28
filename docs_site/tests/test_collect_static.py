"""Test for build_docs --collectstatic (the collect_static helper, feature: serveable preview build)."""

from __future__ import annotations

from pathlib import Path

from apps.docs.build.builder import collect_static


def test_collect_static_assembles_into_output(tmp_path: Path) -> None:
    static_dir = collect_static(tmp_path)
    assert static_dir == tmp_path / "static"
    # The CSS/JS the pages reference resolve under <output>/static/...
    assert (static_dir / "css" / "site.css").is_file()
    assert (static_dir / "js" / "site.js").is_file()
    # ...including the django_components package static (via the AppDirectories finder).
    assert (static_dir / "django_components" / "django_components.min.js").is_file()


def test_collect_static_works_after_storage_initialised(tmp_path: Path) -> None:
    # Regression: mid-build the staticfiles_storage is already cached, so a
    # STATIC_ROOT-override approach would write to the wrong dir. The finder-based
    # copy must still land in <output>/static.
    from django.contrib.staticfiles.storage import staticfiles_storage  # noqa: PLC0415

    _ = staticfiles_storage.location  # force the storage to initialise
    static_dir = collect_static(tmp_path)
    assert (static_dir / "css" / "tokens.css").is_file()
