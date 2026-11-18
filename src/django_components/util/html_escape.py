"""
Escape values for HTML attributes.

Django's `conditional_escape()` and `format_html()` pass a value marked safe (a `SafeString` from
`mark_safe()` or `format_html()`, or any object with `__html__()`) through unchanged. That is right
between tags, where marked-safe HTML is meant to stay HTML. Inside a quoted attribute value it is
wrong: a `"` in the marked-safe text ends the attribute, and the text after it becomes new
attributes. So `escape_attribute_value()` escapes every value, whatever its marking.
"""

import re
from html import unescape
from html.entities import html5
from typing import Any

from django.utils.html import escape

# One character reference, the same pattern Python's `html.unescape` uses.
_CHARREF = re.compile(r"&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)")

# The most digits, not counting leading zeros, that a numeric reference can have and still name
# a code point at or below U+10FFFF: 1114111 has seven decimal digits and 10FFFF six hex digits.
_MAX_DECIMAL_DIGITS = 7
_MAX_HEX_DIGITS = 6


def exact_str(text: str) -> str:
    """
    Return the characters of `text` as an exact `str`, never a subclass.

    `str()` of a Django `SafeString` returns the `SafeString` itself, which keeps `__html__`, and a
    `str` subclass can override methods such as `replace` that escaping relies on. A copy made by
    `str.__str__` reads the stored characters without calling any override.
    """
    if type(text) is str:
        return text
    return str.__str__(text)


def _decode_numeric_reference(name: str) -> str:
    """Return the character a browser reads from the numeric reference `name` (`#106` or `#x6A;`)."""
    is_hex = name[1:2] in {"x", "X"}
    digits = name[2:] if is_hex else name[1:]
    significant = digits.rstrip(";").lstrip("0")
    # Too many digits to be at or below U+10FFFF. Checking the length first also keeps `int()`
    # away from a reference with thousands of digits, which it refuses.
    if len(significant) > (_MAX_HEX_DIGITS if is_hex else _MAX_DECIMAL_DIGITS):
        return "�"
    code_point = int(significant or "0", 16 if is_hex else 10)
    # NUL, a surrogate and a value past U+10FFFF read as U+FFFD.
    if code_point == 0 or 0xD800 <= code_point <= 0xDFFF or code_point > 0x10FFFF:
        return "�"
    # The HTML standard reads 0x80 to 0x9F as Windows-1252, and keeps the five codes that
    # Windows-1252 leaves undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D) as they are; Python's cp1252
    # codec refuses exactly those five.
    if 0x80 <= code_point <= 0x9F:
        try:
            return bytes([code_point]).decode("cp1252")
        except UnicodeDecodeError:
            return chr(code_point)
    # The browser keeps every other code point, control characters included, while
    # `html.unescape` drops some of them.
    return chr(code_point)


def _decode_attribute_charref(match: re.Match[str]) -> str:
    """Decode one character reference the way a browser does inside an attribute value."""
    name = match.group(1)
    if name[0] == "#":
        return _decode_numeric_reference(name)
    # A name that matches exactly decodes as in text.
    if name in html5:
        return unescape(match.group(0))
    # A legacy name without ";" (such as "&copy") decodes from its longest known prefix. Inside an
    # attribute value a browser leaves it as typed when "=" or a letter or digit follows, so
    # "?a=1&copy=2" stays a URL.
    for end in range(len(name) - 1, 1, -1):
        prefix = name[:end]
        if prefix in html5:
            following = name[end]
            if following == "=" or (following.isascii() and following.isalnum()):
                return match.group(0)
            return html5[prefix] + name[end:]
    return match.group(0)


def decode_attribute_entities(html: str) -> str:
    """
    Return the attribute value a browser reads from `html` written inside quotes.

    A named reference written without `;` stays as typed when `=` or a letter or digit follows it,
    so `?a=1&copy=2` stays a URL, as the HTML parser reads it in an attribute value. The result is
    always an exact `str`.
    """
    text = exact_str(html)
    if "&" not in text:
        return text
    return _CHARREF.sub(_decode_attribute_charref, text)


def escape_attribute_value(value: Any) -> str:
    """
    Escape `value` as the text of a double-quoted HTML attribute value.

    Every value is escaped, including a `SafeString` and any other object with `__html__()`. Such
    a value is HTML, so it is first decoded to the text a browser would read from it and then
    escaped. `mark_safe("Tom &amp; Jerry")` still reads as `Tom & Jerry`, and a `"` in it can no
    longer end the attribute.

    Any other value is converted with `str()` and escaped.
    """
    html = getattr(value, "__html__", None)
    if html is not None:
        # The browser turns a raw CR, or CR LF, in the page into LF before it decodes references,
        # so do the same first. A CR that is left after decoding came from a reference such as
        # `&#13;`, and is written back as a reference so that the browser still reads a CR.
        source = exact_str(str(html())).replace("\r\n", "\n").replace("\r", "\n")
        # `decode_attribute_entities` returns an exact `str`, so no method that a `str` subclass
        # overrides can change the escape below.
        text = decode_attribute_entities(source)
        escaped = str(escape(text)).replace("\r", "&#13;")
    else:
        # `str()` of an object may return a `SafeString` too; an exact copy makes sure the escape
        # sees plain text.
        escaped = str(escape(exact_str(str(value))))
    # On a page read as ISO-2022-JP, a raw ESC can switch the decoder so that the closing quote
    # stops being a quote. A reference is read only after the page is decoded.
    return escaped.replace("\x1b", "&#27;")
