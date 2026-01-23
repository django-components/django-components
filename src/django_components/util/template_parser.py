r"""
Parser for Django template.

The parser reads a template file (usually HTML, but not necessarily), which may contain
"template tags" like this:

```django
{% component 'my_comp' key=val key2='val2 two' %}
{% endcomponent %}

{{ my_var }}

{# I am comment #}
```

and returns a list of Tokens:

```py
[
    (TokenType.TEXT, '\n', (0, 1), 1),
    (TokenType.BLOCK, "component 'my_comp' key=val key2='val2 two'", (1, 50), 2),
    (TokenType.TEXT, '\n', (50, 51), 2),
    (TokenType.BLOCK, 'endcomponent', (51, 69), 3),
    (TokenType.TEXT, '\n\n', (69, 71), 3),
    (TokenType.VAR, 'my_var', (71, 83), 5),
    (TokenType.TEXT, '\n\n', (83, 85), 5),
    (TokenType.COMMENT, 'I am comment', (85, 103), 7),
    (TokenType.TEXT, '\n', (103, 104), 7),
]
```

See `parse_template()` for details.
"""

import re
from functools import lru_cache

from django.template.base import DebugLexer, Token, TokenType
from django.template.exceptions import TemplateSyntaxError


# NOTE: As of 0.125, the strategy is to use Django's lexer, and use our own parser
#   only when necessary, for the shortest time possible.
#
#   Before I switched to this strategy, my initial parser was about 50x slower than Django's lexer.
#   I (Juro) assume it was because I was walking character by character, instead of using a regex.
#
#   The overall speed should then depend on the number of broken tokens in the template.
#
#   Performance of the new strategy on a real-world example:
#   - A template with about 110 lines and 6 components
#   - Components spanning ~35 lines in total, so roughly 1/3 of the template
#   - The custom parser is about 8x slower than Django's Debug lexer.
#   - For a mid-sized project of 200 templates, it would take 7-8 seconds to load all the templates
#     (from 1 second with Django's lexer).
#     - However, thanks to django-component's lazy-loading, this should not be a problem.
#
#   How it works is that:
#   1. We use Django's lexer to get the tokens.
#   2. We check them one-by-one, and if we find a broken token, we switch to our parser to fix it.
#   3. Once the broken token is fixed, we find it's end position, and switch back to the Django lexer
#      for the remaining text (step 1).
def parse_template(text: str) -> list[Token]:
    resolved_tokens: list[Token] = []

    index_start = 0
    index_end = len(text)
    lineno_offset = 0

    while index_start < index_end:
        broken_token: Token | None = None
        # Do fast tokenization with regex - This is about 50x faster than our custom tokenizer.
        # We use DebugLexer because we need to get the position of the tokens.
        # DebugLexer and Lexer have very similar speeds, Debug is about 33% slower.
        lexer = DebugLexer(text[index_start:index_end])
        tokens: list[Token] = lexer.tokenize()

        for token in tokens:
            token.lineno += lineno_offset
            token.position = (token.position[0] + index_start, token.position[1] + index_start)

            if token.token_type == TokenType.BLOCK and ("'" in token.contents or '"' in token.contents):
                broken_token = token
                break
            resolved_tokens.append(token)

        # If we found a broken token, we switch to our slow parser
        if broken_token is not None:
            broken_token_start = broken_token.position[0]
            fixed_token = _detailed_tag_parser(text[broken_token_start:], broken_token.lineno, broken_token_start)

            resolved_tokens.append(fixed_token)
            index_start = fixed_token.position[1]
            lineno_offset += (
                fixed_token.lineno - 1  # -1 because lines are 1-indexed
                + fixed_token.contents.count("\n")
            )  # fmt: skip
        else:
            break

    return resolved_tokens


# Handle parsing of `{% %}` tags, while allowing `%}` inside of strings
def _detailed_tag_parser(text: str, lineno: int, start_index: int) -> Token:
    index = 0
    length = len(text)
    result_content: list[str] = []

    # Pre-compute common substrings
    QUOTE_CHARS = ("'", '"')  # noqa: N806
    QUOTE_OR_PERCENT = (*QUOTE_CHARS, "%")  # noqa: N806

    def take_char() -> str:
        nonlocal index
        if index >= length:
            return ""
        char = text[index]
        index += 1
        return char

    def peek_char(offset: int = 0) -> str:
        peek_index = index + offset
        if peek_index >= length:
            return ""
        return text[peek_index]

    # This is an optimized version that uses regex to find the next stop character
    # and ignores the stop characters if they are prefixed by a backslash, if allow_escapes is True.
    #
    # For the intuition, the original version is:
    #
    # ```py
    # def take_until_any(stop_chars: tuple[str, ...], allow_escapes: bool = False) -> str:
    #     nonlocal index
    #     start = index
    #     while index < length:
    #         char = text[index]
    #         if allow_escapes and char == BACKSLASH and index + 1 < length:
    #             index += 2
    #             continue
    #         if char in stop_chars:
    #             break
    #         index += 1
    #     return text[start:index]
    # ```
    def take_until_any(stop_chars: tuple[str, ...], allow_escapes: bool = False) -> str:
        nonlocal index

        stop_chars_str = "".join(stop_chars)
        pattern = _compile_take_until_pattern(stop_chars_str, allow_escapes)

        # Find match at current position
        match = pattern.match(text, index)
        if match:
            matched_text = match.group(0)
            index += len(matched_text)
            return matched_text

        return ""

    # Given that this function is called only when there's a broken token,
    # we know that the first two characters are always "{%"
    take_char()  # {
    take_char()  # %

    # Main parsing loop
    while index < length:
        char = peek_char()

        # Handle strings within `{% %}`
        if char in QUOTE_CHARS:
            quote_char = take_char()
            result_content.append(quote_char)

            # Take content until matching quote, allowing escaped quotes
            content = take_until_any((quote_char,), allow_escapes=True)
            result_content.append(content)

            # Handle the closing quote
            if peek_char() == quote_char:
                result_content.append(take_char())
            else:
                raise TemplateSyntaxError(f"Unexpected end of text - unterminated {quote_char} string")
            continue

        # Check for closing tag
        if char == "%":
            if peek_char(1) == "}":
                take_char()  # %
                take_char()  # }
                break
            # False alarm, just a string
            content = take_until_any(QUOTE_CHARS)
            result_content.append(content)
            continue

        # Take regular content until we hit a quote or potential closing tag
        content = take_until_any(QUOTE_OR_PERCENT)
        result_content.append(content)

    else:
        raise TemplateSyntaxError("Unexpected end of text - unterminated {% tag")

    result_str = "".join(result_content).strip()  # Django's Lexer.tokenize() strips the whitespace
    return Token(TokenType.BLOCK, result_str, (start_index, index + start_index), lineno)


# Create a regex pattern that takes anything until any of the stop characters are found.
#
# If allow_escapes is True, also the stop characters are allowed, given that they are
# prefixed by a backslash.
@lru_cache(maxsize=128)
def _compile_take_until_pattern(stop_chars: str, allow_escapes: bool) -> re.Pattern:
    escaped_stops = "".join(re.escape(c) for c in stop_chars)

    if allow_escapes:
        # Match either escaped characters or anything until stop chars
        pattern = f"(?:\\\\.|[^{escaped_stops}])*"
    else:
        # Match anything until stop chars
        pattern = f"[^{escaped_stops}]*"

    return re.compile(pattern)
