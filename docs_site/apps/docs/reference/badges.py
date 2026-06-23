"""
Symbol-type heading badge (feature 4.42, ``SymbolTypeBadge``).

Emits ``<span class="doc doc-symbol-heading doc-symbol-{kind}">`` markup matching
the old mkdocstrings/Material classes, so the colored class/function/attribute
letter badges keep working once the CSS is ported. Until that CSS lands the span
is simply invisible - the heading still reads cleanly.
"""

from __future__ import annotations

# CSS symbol kinds, matching the old Material `doc-symbol-*` classes.
_KNOWN_SYMBOLS = frozenset({"class", "function", "method", "attribute", "module"})


def symbol_badge(symbol_kind: str) -> str:
    """Heading badge markup for a CSS symbol kind (``class``/``function``/...)."""
    kind = symbol_kind if symbol_kind in _KNOWN_SYMBOLS else "attribute"
    return f'<span class="doc doc-symbol doc-symbol-heading doc-symbol-{kind}" title="{kind}"></span>'
