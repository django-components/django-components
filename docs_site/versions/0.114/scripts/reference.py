# Adapted from https://github.com/mkdocstrings/python/blob/main/scripts/gen_ref_nav.py
# License: ISC License - Copyright (c) 2021, Timothée Mazzucotelli

"""Generate the code reference pages and navigation.

No need to run this script manually, it is called by mkdocs-material during the build process.

You can run it manually to test the output.
"""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

root = Path(__file__).parent.parent.parent.parent
src = root / "src"

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    if module_path.parts[-1] == "__init__":
        module_path = module_path.parent
    doc_path = path.relative_to(src).with_suffix("")
    if doc_path.parts[-1] == "__init__":
        doc_path = doc_path.parent
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    doc_path = doc_path / "index.md"
    full_doc_path = full_doc_path / "index.md"

    nav_parts = [f"{mod_symbol} {part}" for part in parts]
    nav[tuple(nav_parts)] = doc_path.as_posix()
    if parts[-1] == "__init__":
        parts = parts[:-1]

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(root))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines([line.replace("  ", " ").removeprefix(" ") for line in nav.build_literate_nav(indentation=2)])
