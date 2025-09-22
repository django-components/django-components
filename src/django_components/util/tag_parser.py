# ruff: noqa: S105
"""
Parser for Django template tags.

The parser reads a tag like this (without the `{%` `%}`):

```django
{% component 'my_comp' key=val key2='val2 two' %}
```

and returns an AST representation of the tag:

```py
[
    TagAttr(
        key=None,
        value=TagValueStruct(
            type="simple",
            spread=None,
            meta={},
            entries=[
                TagValue(
                    parts=[
                        TagValuePart(
                            value="component", quoted=None, spread=None, translation=False, filter=None
                        ),
                    ]
                ),
            ],
        ),
        start_index=0,
    ),
    ...
]
```

See `parse_tag()` for details.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union, cast

from django.template.base import FilterExpression, Parser
from django.template.context import Context
from django.template.exceptions import TemplateSyntaxError

from django_components.expression import DynamicFilterExpression, is_dynamic_expression

TAG_WHITESPACE = (" ", "\t", "\n", "\r", "\f")
TAG_FILTER = ("|", ":")
TAG_SPREAD = ("*", "**", "...")


@dataclass
class TagAttr:
    """
    A tag attribute represents a single token of a tag.

    E.g. the following tag:

    ```django
    {% component "my_comp" key=val key2='val2 two' %}
    ```

    Has 4 attributes: `component`, `my_comp`, `key=val` and `key2='val2 two'`.
    """

    key: Optional[str]
    value: "TagValueStruct"
    start_index: int

    def serialize(self, omit_key: bool = False) -> str:
        s = self.value.serialize()
        if not omit_key and self.key:
            return f"{self.key}={s}"
        return s


@dataclass
class TagValue:
    """
    A tag value represents the text to the right of the `=` in a tag attribute.

    E.g. in the following tag:
    ```django
    {% component "my_comp" key=val2|filter1:"one" %}
    ```

    The `key` attribute has the TagValue `val2|filter1:"one"`.
    """

    parts: List["TagValuePart"]
    compiled: Optional[Union[FilterExpression, DynamicFilterExpression]] = None

    @property
    def is_spread(self) -> bool:
        if not self.parts:
            return False
        return self.parts[0].spread is not None

    def serialize(self) -> str:
        return "".join(part.serialize() for part in self.parts)

    def compile(self, parser: Optional[Parser]) -> None:
        if self.compiled is not None:
            return

        serialized = self.serialize()
        # Remove the spread token from the start of the serialized value
        # E.g. `*val|filter:arg` -> `val|filter:arg`
        if self.is_spread:
            spread_token = self.parts[0].spread
            spread_token_offset = len(spread_token) if spread_token else 0
            serialized = serialized[spread_token_offset:]

        if parser is None:
            raise ValueError("Parser is required to compile tag values")

        # Allow to use dynamic expressions as args, e.g. `"{{ }}"` inside of strings
        if is_dynamic_expression(serialized):
            self.compiled = DynamicFilterExpression(parser, serialized)
        else:
            self.compiled = FilterExpression(serialized, parser)

    def resolve(self, context: Context) -> Any:
        if self.compiled is None:
            raise TemplateSyntaxError("Malformed tag: TagValue.resolve() called before compile()")
        return self.compiled.resolve(context)


@dataclass
class TagValuePart:
    """
    Django tag attributes may consist of multiple parts, being separated by filter pipes (`|`)
    or filter arguments (`:`). This class represents a single part of the attribute value.

    E.g. in the following tag:
    ```django
    {% component "my_comp" key="my val's" key2=val2|filter1:"one" %}
    ```

    The value of attribute `key2` has three parts: `val2`, `filter1` and `"one"`.
    """

    value: str
    """The textual value"""
    quoted: Optional[str]
    """Whether the value is quoted, and the character that's used for the quotation"""
    spread: Optional[str]
    """
    The prefix used by a spread syntax, e.g. `...`, `*`, or `**`. If present, it means
    this values should be spread into the parent tag / list / dict.
    """
    translation: bool
    """Whether the value is a translation string, e.g. `_("my string")`"""
    filter: Optional[str]
    """The prefix of the filter, e.g. `|` or `:`"""

    def __post_init__(self) -> None:
        if self.translation and not self.quoted:
            raise TemplateSyntaxError("Translation value must be quoted")
        if self.translation and self.spread:
            raise TemplateSyntaxError("Cannot combine translation and spread syntax")
        if self.spread and self.filter:
            raise TemplateSyntaxError("Cannot define spread syntax inside a filter")
        if self.filter and self.filter not in TAG_FILTER:
            raise TemplateSyntaxError(f"Invalid filter character: {self.filter}")

    def serialize(self) -> str:
        value = f"{self.quoted}{self.value}{self.quoted}" if self.quoted else self.value
        if self.translation:
            value = f"_({value})"
        elif self.spread:
            value = f"{self.spread}{value}"

        if self.filter:
            value = f"{self.filter}{value}"

        return value

    # NOTE: dataclass is used so we can validate the input. But dataclasses are not hashable,
    # by default, hence these methods.
    def __hash__(self) -> int:
        # Create a hash based on the attributes that define object equality
        return hash((self.value, self.quoted, self.spread, self.translation, self.filter))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TagValuePart):
            return False
        return (
            self.value == other.value
            and self.quoted == other.quoted
            and self.spread == other.spread
            and self.translation == other.translation
            and self.filter == other.filter
        )


@dataclass
class TagValueStruct:
    """
    TagValueStruct represents a potential container (list or dict) that holds other tag values.

    Types:

    - `simple`: Plain tag value
    - `list`: A list of tag values
    - `dict`: A dictionary of tag values

    TagValueStruct may be arbitrarily nested, creating JSON-like structures
    that contains lists, dicts, and simple values.
    """

    type: Literal["list", "dict", "simple"]
    entries: List[Union["TagValueStruct", TagValue]]
    spread: Optional[str]
    """
    The prefix used by a spread syntax, e.g. `...`, `*`, or `**`. If present, it means
    this values should be spread into the parent tag / list / dict.
    """
    # Container for parser-specific metadata
    meta: Dict[str, Any]
    # Parser is passed through so we can resolve variables with filters
    parser: Optional[Parser]
    compiled: bool = False

    def serialize(self) -> str:
        """
        Recursively walks down the value of potentially nested lists and dicts,
        and serializes them all to a string.

        This is effectively the inverse of `parse_tag()`.
        """

        def render_value(value: Union[TagValue, TagValueStruct]) -> str:
            if isinstance(value, TagValue):
                return value.serialize()
            return value.serialize()

        if self.type == "simple":
            value = self.entries[0]
            return render_value(value)
        if self.type == "list":
            prefix = self.spread or ""
            return prefix + "[" + ", ".join([render_value(entry) for entry in self.entries]) + "]"
        if self.type == "dict":
            prefix = self.spread or ""
            dict_pairs = []
            dict_pair: List[str] = []
            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                rendered = render_value(entry)
                if isinstance(entry, TagValueStruct):
                    if entry.spread:
                        if dict_pair:
                            raise TemplateSyntaxError("Malformed dict: spread operator cannot be used as a dict key")
                        dict_pairs.append(rendered)
                    else:
                        dict_pair.append(rendered)
                elif entry.is_spread:
                    if dict_pair:
                        raise TemplateSyntaxError("Malformed dict: spread operator cannot be used as a dict key")
                    dict_pairs.append(rendered)
                else:
                    dict_pair.append(rendered)
                if len(dict_pair) == 2:
                    dict_pairs.append(": ".join(dict_pair))
                    dict_pair = []
            return prefix + "{" + ", ".join(dict_pairs) + "}"

        raise ValueError(f"Invalid type: {self.type}")

    # When we want to render the TagValueStruct, which may contain nested lists and dicts,
    # we need to find all leaf nodes (the "simple" types) and compile them to FilterExpression.
    #
    # To make sure that the compilation needs to be done only once, the result
    # each TagValueStruct contains a `compiled` flag to signal to its parent.
    def compile(self) -> None:
        if self.compiled:
            return

        def compile_value(value: Union[TagValue, TagValueStruct]) -> None:
            if isinstance(value, TagValue):
                value.compile(self.parser)
            else:
                value.compile()

        if self.type == "simple":
            value = self.entries[0]
            compile_value(value)
        elif self.type == "list":
            for entry in self.entries:
                compile_value(entry)
        elif self.type == "dict":
            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                compile_value(entry)

        self.compiled = True

    # Walk down the TagValueStructs and resolve the expressions.
    #
    # NOTE: This is where the TagValueStructs are converted to lists and dicts.
    def resolve(self, context: Context) -> Any:
        self.compile()

        if self.type == "simple":
            value = self.entries[0]
            if not isinstance(value, TagValue):
                raise TemplateSyntaxError("Malformed tag: simple value is not a TagValue")
            return value.resolve(context)

        if self.type == "list":
            resolved_list: List[Any] = []
            for entry in self.entries:
                resolved = entry.resolve(context)
                # Case: Spreading a literal list: [ *[1, 2, 3] ]
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if not entry.type == "list":
                        raise TemplateSyntaxError("Malformed tag: cannot spread non-list value into a list")
                    resolved_list.extend(resolved)
                # Case: Spreading a variable: [ *val ]
                elif isinstance(entry, TagValue) and entry.is_spread:
                    resolved_list.extend(resolved)
                # Case: Plain value: [ val ]
                else:
                    resolved_list.append(resolved)
            return resolved_list

        if self.type == "dict":
            resolved_dict: Dict = {}
            dict_pair: List = []

            # NOTE: Here we assume that the dict pairs have been validated by the parser and
            #       that the pairs line up.
            for entry in self.entries:
                resolved = entry.resolve(context)
                if isinstance(entry, TagValueStruct) and entry.spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value",
                        )
                    # Case: Spreading a literal dict: { **{"key": val2} }
                    resolved_dict.update(resolved)
                elif isinstance(entry, TagValue) and entry.is_spread:
                    if dict_pair:
                        raise TemplateSyntaxError(
                            "Malformed dict: spread operator cannot be used on the position of a dict value",
                        )
                    # Case: Spreading a variable: { **val }
                    resolved_dict.update(resolved)
                else:
                    # Case: Plain value: { key: val }
                    dict_pair.append(resolved)

                if len(dict_pair) == 2:
                    dict_key = dict_pair[0]
                    dict_value = dict_pair[1]
                    resolved_dict[dict_key] = dict_value
                    dict_pair = []
            return resolved_dict

        raise ValueError(f"Invalid type: {self.type}")


def parse_tag(text: str, parser: Optional[Parser]) -> Tuple[str, List[TagAttr]]:
    """
    Parse the content of a Django template tag like this:

    ```django
    {% component 'my_comp' key=val key2='val2 two' %}
    ```

    into an AST representation:

    [
        TagAttr(
            key=None,
            start_index=0,
            value=TagValue(
                parts=tuple([
                    TagValuePart(value="component", quoted=None, spread=None, translation=False, filter=None)
                ])
            ),
        ),
        TagAttr(
            key=None,
            start_index=10,
            value=TagValue(
                parts=tuple([
                    TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                ])
            ),
        ),
        ...
    ]
    ```

    Supported syntax:
    - Variables: `val`, `key`
    - Kwargs (attributes): `key=val`, `key2='val2 two'`
    - Quoted strings: `"my string"`, `'my string'`
    - Translation: `_("my string")`
    - Filters: `val|filter`, `val|filter:arg`
    - List literals: `[value1, value2]`, `key=[value1, [1, 2, 3]]`
    - Dict literals: `{"key1": value1, "key2": value2}`, `key={"key1": value1, "key2": {"nested": "value"}}`
    - Trailing commas: `[1, 2, 3,]`, `{"key": "value", "key2": "value2",}`
    - Spread operators: `...`, `*`, `**`
    - Spread inside lists and dicts: `key=[1, *val, 3]`, `key={"key": val, **kwargs, "key2": 3}`
    - Spread with list and dict literals: `{**{"key": val2}, "key": val1}`, `[ ...[val1], val2 ]`
    - Spread list and dict literals as attributes: `{% ...[val1] %}`, `{% ...{"key" val1 } %}`

    Invalid syntax:
    - Spread inside a filter: `val|...filter`
    - Spread inside a dictionary key: `attr={...attrs: "value"}`
    - Spread inside a dictionary value: `attr={"key": ...val}`
    - Misplaced spread: `attr=[...val]`, `attr={...val}`, `attr=[**val]`, `attr={*val}`
    - Spreading lists and dicts: `...[1, 2, 3]`, `...{"key": "value"}`
    """
    index = 0
    normalized = ""

    def add_token(token: str) -> None:
        nonlocal normalized
        nonlocal index

        normalized += token
        index += len(token)

    def is_at_end(offset: int = 0) -> bool:
        return index + offset >= len(text)

    def is_next_token(tokens: Union[List[str], Tuple[str, ...]]) -> bool:
        if not tokens:
            raise TemplateSyntaxError("No tokens provided")

        def is_token_match(token: str) -> bool:
            if not token:
                raise TemplateSyntaxError("Empty token")

            for token_index, token_char in enumerate(token):
                text_char = text[index + token_index] if not is_at_end(token_index) else None
                if text_char is None or text_char != token_char:
                    return False
            return True

        for token in tokens:
            is_match = is_token_match(token)
            if is_match:
                return True
        return False

    def taken_n(n: int) -> str:
        result = text[index : index + n]
        add_token(result)
        return result

    # tag_name = take_until([" ", "\t", "\n", "\r", "\f", ">", "/>"])
    def take_until(
        tokens: Union[List[str], Tuple[str, ...]],
        ignore: Optional[Sequence[str]] = None,
    ) -> str:
        result = ""
        while not is_at_end():
            char = text[index]

            ignore_token_match: Optional[str] = None
            for ignore_token in ignore or []:
                if is_next_token([ignore_token]):
                    ignore_token_match = ignore_token

            if ignore_token_match:
                result += "".join(ignore_token_match)
                add_token(ignore_token_match)
                continue

            if is_next_token(tokens):
                return result

            result += char
            add_token(char)
        return result

    # tag_name = take_while([" ", "\t", "\n", "\r", "\f"])
    def take_while(tokens: Union[List[str], Tuple[str, ...]]) -> str:
        result = ""
        while not is_at_end():
            char = text[index]

            if is_next_token(tokens):
                result += char
                add_token(char)
            else:
                return result

        return result

    def extract_spread_token(curr_struct: TagValueStruct, filter_token: Optional[str]) -> Optional[str]:
        # Move the spread syntax out of the way, so that we properly handle what's next.
        # Spread syntax MUST NOT be part of a filter, so that will raise if so.
        #
        # NOTE: To be consistent with Python API, the spread operator is marked with `*` or `**`
        # inside lists and dicts:
        # - `...` - Outside: `{% component ...spread %}`
        # - `*` - Inside lists: `{% component key=[ *spread ] %}`
        # - `**` - Inside dicts: `{% component key={ **spread } %}`
        spread_token: Optional[str] = None
        is_spread = is_next_token(TAG_SPREAD)
        if is_spread:
            if is_next_token(["..."]):
                if curr_struct.type != "simple":
                    raise TemplateSyntaxError(
                        f"Spread syntax '...' found in {curr_struct.type}. It must be used on tag attributes only",
                    )
                spread_token = "..."
            elif is_next_token(["**"]):
                if curr_struct.type != "dict":
                    raise TemplateSyntaxError("Spread syntax '**' found outside of a dictionary")
                spread_token = "**"
            elif is_next_token(["*"]):
                if curr_struct.type != "list":
                    raise TemplateSyntaxError("Spread syntax '*' found outside of a list")
                spread_token = "*"
            else:
                raise TemplateSyntaxError("Invalid spread syntax")

        if spread_token is not None:
            # Check for usage like `args|...filter`
            if filter_token:
                raise TemplateSyntaxError("Spread syntax cannot be used inside of a filter")

            # Check for usage like `key=...attrs`
            if curr_struct.type == "simple" and key is not None:
                raise TemplateSyntaxError("Spread syntax '...' cannot follow a key ('key=...attrs')")

            taken_n(len(cast("str", spread_token)))  # ... or * or **
            # Allow whitespace between spread and the variable, but only for the Python-like syntax
            # (lists and dicts). E.g.:
            # `{% component key=[ * spread ] %}` or `{% component key={ ** spread } %}`
            #
            # But not for the template tag syntax, because template tags rely on the whitespace
            # to determine the end of the attribute value. E.g.:
            # `{% component key=val ...spread key2=val2 %}`
            if spread_token != "...":
                take_while(TAG_WHITESPACE)
            elif is_next_token(TAG_WHITESPACE) or is_at_end():
                raise TemplateSyntaxError("Spread syntax '...' is missing a value")
        return spread_token

    # Parse attributes
    attrs: List[TagAttr] = []
    while not is_at_end():
        # Skip whitespace
        take_while(TAG_WHITESPACE)

        start_index = len(normalized)
        key = None

        # If token starts with any of these, we assume it's a value without key part.
        # e.g. `component 'my_comp'`
        # Otherwise, try to parse the key.
        if is_next_token(["'", '"', '_("', "_('", "[", "{", *TAG_SPREAD]):
            key = None
        else:
            key = take_until(["=", "'", '"', '_("', "_('", "|", "[", "{", *TAG_SPREAD, *TAG_WHITESPACE])

            # We've reached the end of the text
            if not key and is_at_end():
                break

            if not is_next_token(["="]):
                # This was actually a value (variable) without the key part
                index -= len(key)
                normalized = normalized[:start_index]
                key = None
            else:
                add_token("=")

        # NOTE: We put a fake root item, so we can modify the list in place.
        # At the end, we'll unwrap the list to get the actual value.
        total_value = TagValueStruct(type="simple", entries=[], spread=None, meta={}, parser=parser)
        stack = [total_value]

        while len(stack) > 0:
            take_while(TAG_WHITESPACE)

            curr_value = stack[-1]

            # Manage state with regards to lists and dictionaries
            if is_next_token(["[", "...[", "*[", "**["]):
                spread_token = extract_spread_token(curr_value, None)
                if spread_token is not None and curr_value.type == "simple" and key is not None:
                    raise TemplateSyntaxError("Spread syntax '...' cannot follow a key ('key=...attrs')")
                # NOTE: The `...`, `**`, `*` are "taken" in `extract_spread_token()`
                taken_n(1)  # [
                struct = TagValueStruct(type="list", entries=[], spread=spread_token, meta={}, parser=parser)
                curr_value.entries.append(struct)
                stack.append(struct)
                continue

            if is_next_token(["]"]):
                if curr_value.type != "list":
                    raise TemplateSyntaxError("Unexpected closing bracket")
                taken_n(1)  # ]
                stack.pop()
                # Allow only 1 top-level list, similar to JSON
                if stack[-1].type == "simple":
                    stack.pop()
                continue

            if is_next_token(["{", "...{", "*{", "**{"]):
                spread_token = extract_spread_token(curr_value, None)
                if spread_token is not None and curr_value.type == "simple" and key is not None:
                    raise TemplateSyntaxError("Spread syntax '...' cannot follow a key ('key=...attrs')")
                # NOTE: The `...`, `**`, `*` are "taken" in `extract_spread_token()`
                taken_n(1)  # {

                # Disallow nested structs on the position of a key
                # E.g. `{ [val1, val2]: value }` or `{ {key: val}: value }`
                # However, technically, we could allow this if the spread syntax is used.
                # E.g. `{ ...{"key": val2} }`
                if curr_value.type == "dict" and curr_value.meta["expects_key"]:
                    if spread_token:
                        curr_value.meta["expects_key"] = True
                    else:
                        raise TemplateSyntaxError("Dictionary cannot be used as a dictionary key")

                struct = TagValueStruct(type="dict", entries=[], spread=spread_token, meta={}, parser=parser)
                curr_value.entries.append(struct)
                struct.meta["expects_key"] = True
                stack.append(struct)
                continue

            if is_next_token(["}"]):
                if curr_value.type != "dict":
                    raise TemplateSyntaxError("Unexpected closing bracket")

                # Validate that the dicts contains only key-value pairs and spread entries
                dict_pair: List[Union[TagValueStruct, TagValue]] = []
                for entry in curr_value.entries:
                    # Dicts and lists can be used only as values, not as keys
                    if isinstance(entry, TagValueStruct):
                        if entry.spread:
                            # Case: `{ "key": **{"key2": val2} }`
                            if dict_pair:
                                raise TemplateSyntaxError(
                                    "Spread syntax cannot be used in place of a dictionary value",
                                )
                            # Case: `{ **{"key": val2} }`
                            continue
                        # Case: `{ {"key": val2}: value }`
                        if not dict_pair:
                            val_type = "Dictionary" if curr_value.type == "dict" else "List"
                            raise TemplateSyntaxError(f"{val_type} cannot be used as a dictionary key")
                        # Case: `{ "key": {"key2": val2} }`
                        dict_pair.append(entry)
                        if len(dict_pair) == 2:
                            dict_pair = []
                    # Spread is fine when on its own, but cannot be used after a dict key
                    elif entry.is_spread:
                        # Case: `{ "key": **my_attrs }`
                        if dict_pair:
                            raise TemplateSyntaxError(
                                "Spread syntax cannot be used in place of a dictionary value",
                            )
                        # Case: `{ **my_attrs }`
                        continue
                    # Non-spread value can be both key and value.
                    else:
                        # Cases: `{ my_attrs: "value" }` or `{ "key": my_attrs }`
                        dict_pair.append(entry)
                        if len(dict_pair) == 2:
                            dict_pair = []
                # If, at the end, there an unmatched key-value pair, raise an error
                if dict_pair:
                    raise TemplateSyntaxError("Dictionary key is missing a value")

                del curr_value.meta["expects_key"]

                taken_n(1)  # }
                stack.pop()
                # Allow only 1 top-level dict, similar to JSON
                if stack[-1].type == "simple":
                    stack.pop()
                continue

            if is_next_token([","]):
                if curr_value.type not in ("list", "dict"):
                    raise TemplateSyntaxError("Unexpected comma")
                taken_n(1)  # ,
                if curr_value.type == "dict":
                    curr_value.meta["expects_key"] = True
                continue

            # NOTE: Altho `:` is used also in filter syntax, the "value" part
            # that the filter is part of is parsed as a whole block. So if we got
            # here, we know we're NOT in filter.
            if is_next_token([":"]):
                if curr_value.type != "dict":
                    raise TemplateSyntaxError("Unexpected colon")
                if not curr_value.meta["expects_key"]:
                    raise TemplateSyntaxError("Unexpected colon")
                taken_n(1)  # :
                curr_value.meta["expects_key"] = False
                continue

            # Allow only 1 top-level plain value, similar to JSON
            if curr_value.type == "simple":
                stack.pop()
            elif is_at_end():
                raise TemplateSyntaxError("Unexpected end of text")

            # Once we got here, we know that next token is NOT a list nor dict.
            # So we can now parse the value.

            # Parse all filter parts of a value, e.g. `height="20" | yesno : "1,2,3" | lower`
            # should be parsed as `"20" | yesno : "1,2,3" | lower`
            values_parts: List[TagValuePart] = []
            is_first_part = True
            end_of_value = False
            while not end_of_value:
                is_translation = False

                take_while(TAG_WHITESPACE)

                if is_at_end():
                    if is_first_part:
                        raise TemplateSyntaxError("Unexpected end of text")
                    end_of_value = True
                    continue

                # In this case we've reached the end of a filter sequence
                # e.g. image:      `height="20"|lower key1=value1`
                # and we're here:                     ^
                # such that the next token already belongs to the next attribute.
                if not is_first_part and not is_next_token(TAG_FILTER):
                    end_of_value = True
                    continue

                # Catch cases like `|filter` or `:arg`, which should be `var|filter` or `filter:arg`
                if is_first_part and is_next_token(TAG_FILTER):
                    raise TemplateSyntaxError("Filter is missing a value")

                # Get past the filter tokens like `|` or `:`, until the next value part.
                # E.g. imagine:    `height="20" | yesno : "1,2,3" | lower`
                # and we're here:               ^
                # (or here)                             ^
                # (or here)                                       ^
                # and we want to parse `yesno` next
                if not is_first_part:
                    filter_token = taken_n(1)  # | or :
                    take_while(TAG_WHITESPACE)  # Allow whitespace after filter

                    if filter_token == ":" and values_parts[-1].filter != "|":
                        raise TemplateSyntaxError("Filter argument (':arg') must follow a filter ('|filter')")
                else:
                    filter_token = None
                    is_first_part = False

                # Move the spread syntax out of the way, so that we properly handle what's next.
                # Spread syntax MUST NOT be part of a filter, so that will raise if so.
                #
                # NOTE: To be consistent with Python API, the spread operator is marked with `*` or `**`
                # inside lists and dicts:
                # - `...` - Outside: `{% component ...spread %}`
                # - `*` - Inside lists: `{% component key=[ *spread ] %}`
                # - `**` - Inside dicts: `{% component key={ **spread } %}`
                spread_token = extract_spread_token(curr_value, filter_token)
                # Handle top-level spread `{% component ...attrs %}`
                if curr_value.type == "simple":
                    curr_value.spread = spread_token

                # IMPORTANT!!! Depending on whether we're in a list or dict, there may be extra terminal tokens.
                #
                # E.g. in `[value | filter : argument, value2 | filter2 : argument2]`, the two values
                # are separated by a comma, and terminated by `]`.
                #
                # And in `{key1: value1 | filter1 : argument1, key2: value2 | filter2 : argument2}`
                # the two key-value pairs are separated by a comma, and terminated by `}`.
                #
                # But as you can see, the dictionary also uses `:` syntax to separate the key from value.
                # This effectively means that when we're parsing a dictionary KEY, we're unable to tell
                # if the next `:` is the key-value syntax versus filter argument syntax.
                #
                # THUS, to resolve this, in dictionary we don't allow KEY to have a filter argument syntax `:`.
                # So if we see `:`, we end the key part of key-value syntax, and start parsing the value.
                if curr_value.type == "dict":
                    if curr_value.meta["expects_key"]:
                        terminal_tokens: Tuple[str, ...] = (":", ",", "}")
                    else:
                        if spread_token:
                            raise TemplateSyntaxError("Spread syntax cannot be used in place of a dictionary value")
                        terminal_tokens = (",", "}")
                elif curr_value.type == "list":
                    terminal_tokens = (",", "]")
                else:
                    terminal_tokens = ()

                # Parse the value
                #
                # E.g. imagine:    `height="20" | yesno : "1,2,3" | lower`
                # and we're here:          ^
                # or here:                        ^
                # or here:                                ^
                # or here:                                          ^
                if is_next_token(["'", '"', "_("]):
                    # NOTE: Strings may be wrapped in `_()` to allow for translation.
                    # See https://docs.djangoproject.com/en/5.2/topics/i18n/translation/#string-literals-passed-to-tags-and-filters  # noqa: E501
                    # NOTE 2: We could potentially raise if this token is supposed to be a filter
                    # name (after `|`) and we got a translation or a quoted string instead. But we
                    # leave that up for Django.
                    if is_next_token(["_("]):
                        taken_n(2)  # _(
                        # There may be whitespace between the translation syntax and the quote.
                        # E.g. `_("20")` vs `_(  "20"  )`
                        take_while(TAG_WHITESPACE)  # Allow whitespace after translation
                        is_translation = True

                    quote_char = taken_n(1)  # " or '

                    # NOTE: Handle escaped quotes like \" or \', and continue until we reach the closing quote.
                    value = take_until([quote_char], ignore=["\\" + quote_char])

                    if is_next_token([quote_char]):
                        add_token(quote_char)
                        if is_translation:
                            # There may be whitespace between the translation syntax and the quote.
                            # E.g. `_("20")` vs `_(  "20"  )`
                            take_while(TAG_WHITESPACE)  # Allow whitespace after translation
                            taken_n(1)  # )
                        quoted = quote_char
                    # Handle the case when there is a trailing quote, e.g. when a text value is not closed.
                    # `{% component 'my_comp' text="organis %}`
                    else:
                        quoted = None
                        value = quote_char + value
                # E.g. the `20` or `lower` of `height=20|lower`
                # Since this is not a string, we know that it CANNOT contain whitespace.
                #
                # NOTE: This branch is also taken by terminal tokens like `]` or `}`.
                else:
                    quoted = None
                    value = take_until(TAG_WHITESPACE + TAG_FILTER + terminal_tokens)

                take_while(TAG_WHITESPACE)

                if terminal_tokens and is_next_token(terminal_tokens):
                    end_of_value = True

                values_parts.append(
                    TagValuePart(
                        value=value,
                        quoted=quoted,
                        spread=spread_token,
                        translation=is_translation,
                        filter=filter_token,
                    ),
                )

            # Here we're done with the value (+ a sequence of filters)
            # E.g.        `height="20" | yesno : "1,2,3" | lower`
            # we're here:                                       ^
            #
            # This whole sequence could be part of a list or a dict,
            # E.g. `[my_comp, 'height="20" | yesno : "1,2,3" | lower']`
            #
            # So we add it to the parent struct
            curr_value.entries.append(TagValue(parts=values_parts))

            if curr_value.type == "dict":
                if values_parts[0].spread:
                    # Validation for `{"key": **spread }`
                    if not curr_value.meta["expects_key"]:
                        raise TemplateSyntaxError(
                            "Got spread syntax on the position of a value inside a dictionary key-value pair",
                        )

                    # Validation for `{**spread: value }`
                    take_while(TAG_WHITESPACE)
                    if is_next_token([":"]):
                        raise TemplateSyntaxError("Spread syntax cannot be used in place of a dictionary key")
                # Validation for `{"key", value }`
                elif curr_value.meta["expects_key"]:
                    take_while(TAG_WHITESPACE)
                    if not is_next_token([":"]):
                        raise TemplateSyntaxError("Dictionary key is missing a value")

        # And at this point, we have the full representation of the tag value,
        # including any lists or dictionaries (even nested). E.g.
        # ```py
        # TagValueStruct(type="simple", entries=[
        #     TagValueStruct(type="list", entries=[
        #         TagValuePart(value="my_comp", quoted=None, spread=False, translation=False, filter=None),
        #         TagValuePart(value="'height=\"20\" | yesno : \"1,2,3\" | lower'", quoted="'", spread=False, translation=False, filter=None),  # noqa: E501
        #         TagValueStruct(type="dict", entries=[
        #             TagValuePart(value="key1", quoted=None, spread=False, translation=False, filter=None),
        #             TagValuePart(value="value1|filter2 : \"1,2,3\"", quoted="'", spread=False, translation=False, filter=None),  # noqa: E501
        #         ]),
        #     ]),
        # ])
        # ```

        # Unwrap top-level list / dict
        if isinstance(total_value.entries[0], TagValueStruct) and total_value.entries[0].type != "simple":
            total_value = total_value.entries[0]

        attrs.append(
            TagAttr(
                key=key,
                start_index=start_index,
                value=total_value,
            ),
        )

    return normalized, attrs
