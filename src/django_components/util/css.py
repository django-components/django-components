import re

CSS_FUNC_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\(")

_CSS_WHITESPACE = "\n\r\t\f "
# `{` and `}` are refused outright, so only `(` and `[` group inside a value.
_CSS_BLOCK_PAIRS = {"(": ")", "[": "]"}
_CSS_BLOCK_CLOSERS = frozenset(_CSS_BLOCK_PAIRS.values())
# A null is replaced by the browser and a lone surrogate cannot be encoded as UTF-8.
_CSS_UNREADABLE_CHAR = re.compile(r"[\x00\ud800-\udfff]")


def is_css_func(value: str) -> bool:
    """
    Check if a string value is a CSS function call.

    CSS functions follow the pattern: one or more alphanumeric characters (or hyphens/underscores)
    followed by an opening parenthesis.

    Examples:
        - `calc(100% - 20px)` -> True
        - `var(--color)` -> True
        - `rgba(255, 0, 0, 0.5)` -> True
        - `linear-gradient(to right, red, blue)` -> True
        - `Hello World` -> False
        - `red` -> False

    """
    return bool(CSS_FUNC_PATTERN.match(value.strip()))


def serialize_css_var_name(name: object) -> str:
    """
    Write a key from `get_css_data()` as the text that follows `--` in a CSS custom property.

    A key can come from a mapping filled by a request, and a character such as `:` or `;`
    would end the name early. Anything other than ASCII letters, digits, `-` and `_` is
    written as a CSS hex escape, which the browser reads back as that same character, so the
    name stays one name.
    """
    # `str.__str__` reads the stored text, so a str subclass cannot change what is checked here.
    text = str.__str__(str(name))
    return "".join(
        char if char.isascii() and (char.isalnum() or char in "-_") else _css_hex_escape(char) for char in text
    )


def serialize_css_var_value(value: object) -> str:
    """
    Serialize a CSS variable value to CSS text that stays inside its own declaration.

    - `None` is converted to empty string
    - Other values are converted to text
    - Text stays as written when it reads as one CSS value, e.g. `red`, `10px`, `calc(1px + 2px)`
      or `url("/a.png")`
    - Any other text becomes a quoted CSS string, so `a;}b{c:d}` is shown as text and cannot end
      the declaration, add a rule, or end the `<style>` element
    - Text with whitespace is quoted too, unless it is a CSS function

    This never raises on text, so a value that comes from a request or from storage cannot
    make a page fail to render.

    The result holds only printable ASCII and CSS whitespace, with no `<`. Every other
    character is written as a CSS hex escape, so the value reads the same in any encoding that
    keeps ASCII bytes as they are, and no value can spell `</style`.

    This does not check what a value means: a `url()` still loads that URL, so check a URL
    that comes from a request before returning it from `get_css_data()`.
    """
    if value is None:
        return ""

    # Numbers and other types take the same path as strings, because their `__str__`
    # decides what reaches the page.
    # `str.__str__` reads the stored text, so a str subclass cannot change what is checked here.
    text = str.__str__(str(value))

    # Quote text with whitespace and not a CSS function, even if it is well formed: the browser
    # would read `10px 20px` the same either way, and this is how such values always rendered.
    has_whitespace = any(char.isspace() for char in text)
    if (has_whitespace and not is_css_func(text)) or not _is_single_css_value(text):
        text = _quote_css_string(text)

    return _escape_beyond_plain_ascii(text)


def serialize_css_string(value: str) -> str:
    """Write text as a CSS string that is safe inside a `<style>` tag on a page in any encoding."""
    return _escape_beyond_plain_ascii(_quote_css_string(value))


def _quote_css_string(value: str) -> str:
    """Write text as a double-quoted CSS string, escaping what would end the string early."""
    parts = ['"']
    for char in value:
        # A raw newline ends a string early, so control characters are escaped, not kept.
        # The browser reads a hex escape of 0 as U+FFFD, the same as a raw null.
        if ord(char) <= 0x1F or char == "\x7f":
            parts.append(_css_hex_escape(char))
        elif char in {'"', "\\"}:
            parts.append(f"\\{char}")
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def _css_hex_escape(char: str) -> str:
    # The escape ends in a space, which CSS reads as part of the escape, so a hex digit
    # after it is not taken as one more digit of it.
    return f"\\{ord(char):x} "


def _is_plain_css_char(char: str) -> bool:
    # `<` is left out because the HTML parser ends a `<style>` element at `</style`, even
    # inside a CSS string or `url()`, so the character must never be written raw.
    return char in _CSS_WHITESPACE or (" " <= char <= "~" and char != "<")


def _escape_beyond_plain_ascii(value: str) -> str:
    r"""
    Write every character that is not plain ASCII as a CSS hex escape.

    On a page in GBK or Big5, the browser reads the last byte of a non-ASCII character together
    with the next byte as one character, which can hide the backslash of an escaped quote and
    end a string early. On an ISO-2022-JP page, an ESC character changes how the next bytes
    are read. ASCII bytes read the same in all of these encodings.

    A hex escape is part of a name, even where the raw character was not, so the escaped text
    can be split differently from the raw text. `_is_single_css_value` has to allow for that.
    """
    if all(_is_plain_css_char(char) for char in value):
        return value

    parts: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if _is_plain_css_char(following):
                # Keep a backslash and the character after it together, so the second
                # backslash in `\\\\` is not read as the start of another escape.
                parts.append(char + following)
                index += 2
                continue
            # The hex escape below means the same as this backslash and character.
            index += 1
            char = following
        parts.append(char if _is_plain_css_char(char) else _css_hex_escape(char))
        index += 1
    return "".join(parts)


def _is_single_css_value(value: str) -> bool:
    """
    Check that the browser reads this text as one value that stays inside its declaration.

    This walks the text the way the browser splits CSS into pieces. It returns False for text
    that could end the declaration, open or close a rule, or that the browser reads as a broken
    string or URL, which would swallow the text after it. A False result only makes the caller
    quote the value, so the check leans towards False whenever a reading is uncertain.
    """
    if _CSS_UNREADABLE_CHAR.search(value):
        return False

    open_blocks: list[str] = []
    index = 0
    length = len(value)

    while index < length:
        char = value[index]

        # A brace opens or closes a rule. A backslash outside a string could spell any of the
        # characters checked here, and no ordinary value needs `<` outside a string or `url()`.
        if char in "{}\\<" or value.startswith("/*", index):
            return False

        if char in {'"', "'"}:
            index = _skip_css_string(value, index)
        elif value[index : index + 4].lower() == "url(":
            previous = value[index - 1] if index else ""
            # A character outside plain ASCII is written as a hex escape, which is part of a
            # name, so the `url` here would join that name in the text the browser reads.
            # This check reads the raw text, so its answer would not hold.
            if previous and not _is_plain_css_char(previous):
                return False
            if (previous == "" or not (previous.isalnum() or previous in "-_#@")) and not _is_quoted_url(value, index):
                index = _skip_css_url(value, index)
            else:
                # Either a longer name such as `xurl(`, or a quoted URL. Both are an ordinary
                # function, so the `(` is handled on the next step of the loop.
                index += 3
        elif char in _CSS_BLOCK_PAIRS:
            open_blocks.append(_CSS_BLOCK_PAIRS[char])
            index += 1
        elif char in _CSS_BLOCK_CLOSERS:
            if not open_blocks or open_blocks.pop() != char:
                return False
            index += 1
        elif char in ";!" and not open_blocks:
            # At the top level these end the declaration or change its priority.
            return False
        else:
            index += 1

        if index < 0:
            return False

    return not open_blocks


def _skip_css_string(value: str, start: int) -> int:
    """Return the index after a well-formed CSS string, or -1 if the string is broken."""
    quote = value[start]
    index = start + 1
    while index < len(value):
        char = value[index]
        if char == quote:
            return index + 1
        # A raw newline ends the string early, so the text after it would be read as more CSS.
        if char in "\n\r\f":
            return -1
        # Skipping one character after a backslash is enough here: the rest of a hex escape
        # is ordinary text to this scan, and a CRLF after a backslash fails on the LF.
        index += 2 if char == "\\" else 1
    return -1


def _is_quoted_url(value: str, start: int) -> bool:
    """Whether `url(` at `start` is followed by a quote, after any whitespace."""
    index = start + 4
    while index < len(value) and value[index] in _CSS_WHITESPACE:
        index += 1
    return index < len(value) and value[index] in {'"', "'"}


def _skip_css_url(value: str, start: int) -> int:
    """Return the index after a well-formed unquoted `url(...)`, or -1 if it is broken."""
    index = start + 4
    length = len(value)
    # The browser skips whitespace before the address starts.
    while index < length and value[index] in _CSS_WHITESPACE:
        index += 1

    while index < length:
        char = value[index]
        if char == ")":
            return index + 1
        # Whitespace may only come right before the closing bracket.
        if char in _CSS_WHITESPACE:
            while index < length and value[index] in _CSS_WHITESPACE:
                index += 1
            return index + 1 if index < length and value[index] == ")" else -1
        # These make the browser drop the text up to the next `)`.
        code = ord(char)
        if char in "\"'(" or code <= 0x08 or code in {0x0B, 0x7F} or 0x0E <= code <= 0x1F:
            return -1
        if char == "\\":
            # A backslash before a newline, or at the very end, is not a valid escape.
            if index + 1 >= length or value[index + 1] in "\n\r\f":
                return -1
            index += 2
            continue
        index += 1
    return -1
