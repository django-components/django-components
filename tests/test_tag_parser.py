import re
from unittest import skip

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.template.base import Parser
from django.template.engine import Engine

from django_components import Component, register, types
from django_components.util.tag_parser import TagAttr, TagValue, TagValuePart, TagValueStruct, parse_tag

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


# NOTE: We have to define the parser to be able to resolve filters
def _get_parser() -> Parser:
    engine = Engine.get_default()
    return Parser(
        tokens=[],
        libraries=engine.template_libraries,
        builtins=engine.template_builtins,
        origin=None,
    )


@djc_test
class TestTagParser:
    def test_args_kwargs(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 two' ", None)

        expected_attrs = [
            TagAttr(
                key=None,
                start_index=0,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key=None,
                start_index=10,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key",
                start_index=20,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
            ),
            TagAttr(
                key="key2",
                start_index=28,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2 two", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            "'my_comp'",
            "key=val",
            "key2='val2 two'",
        ]

    def test_nested_quotes(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" ", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            "'my_comp'",
            "key=val",
            "key2='val2 \"two\"'",
            'text="organisation\'s"',
        ]

    def test_trailing_quote_single(self):
        _, attrs = parse_tag("component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            "'my_comp'",
            "key=val",
            "key2='val2 \"two\"'",
            'text="organisation\'s"',
            "'abc",
        ]

    def test_trailing_quote_double(self):
        _, attrs = parse_tag('component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),  # noqa: E501
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            '"my_comp"',
            "key=val",
            "key2=\"val2 'two'\"",
            "text='organisation\"s'",
            '"abc',
        ]

    def test_trailing_quote_as_value_single(self):
        _, attrs = parse_tag(
            "component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc",
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted="'", spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='val2 "two"', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="organisation's", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="'abc", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            "'my_comp'",
            "key=val",
            "key2='val2 \"two\"'",
            'text="organisation\'s"',
            "value='abc",
        ]

    def test_trailing_quote_as_value_double(self):
        _, attrs = parse_tag(
            'component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc',
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="val2 'two'", quoted='"', spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=28,
            ),
            TagAttr(
                key="text",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value='organisation"s', quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=46,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value='"abc', quoted=None, spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=68,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            '"my_comp"',
            "key=val",
            "key2=\"val2 'two'\"",
            "text='organisation\"s'",
            'value="abc',
        ]

    def test_translation(self):
        _, attrs = parse_tag('component "my_comp" _("one") key=_("two")', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="one", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="two", quoted='"', spread=None, translation=True, filter=None)]
                        )
                    ],
                ),
                start_index=29,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            '"my_comp"',
            '_("one")',
            'key=_("two")',
        ]

    def test_tag_parser_filters(self):
        _, attrs = parse_tag(
            'component "my_comp" value|lower key=val|yesno:"yes,no" key2=val2|default:"N/A"|upper',
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="my_comp", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=20,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="yesno", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="yes,no", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        )
                    ],
                ),
                start_index=32,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="N/A", quoted='"', spread=None, translation=False, filter=":"),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=55,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            '"my_comp"',
            "value|lower",
            'key=val|yesno:"yes,no"',
            'key2=val2|default:"N/A"|upper',
        ]

    def test_translation_whitespace(self):
        _, attrs = parse_tag('component value=_(  "test"  )', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="value",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="test", quoted='"', spread=None, translation=True, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

    def test_filter_whitespace(self):
        _, attrs = parse_tag("component value  |  lower    key=val  |  upper    key2=val2", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="key",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        )
                    ],
                ),
                start_index=29,
            ),
            TagAttr(
                key="key2",
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=50,
            ),
        ]

        assert attrs == expected_attrs

    def test_filter_argument_must_follow_filter(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Filter argument (':arg') must follow a filter ('|filter')"),
        ):
            parse_tag('component value=val|yesno:"yes,no":arg', None)

    def test_dict_simple(self):
        _, attrs = parse_tag('component data={ "key": "val" }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    def test_dict_trailing_comma(self):
        _, attrs = parse_tag('component data={ "key": "val", }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    def test_dict_missing_colon(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Dictionary key is missing a value"),
        ):
            parse_tag('component data={ "key" }', None)

    def test_dict_missing_colon_2(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Dictionary key is missing a value"),
        ):
            parse_tag('component data={ "key", "val" }', None)

    def test_dict_extra_colon(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Unexpected colon"),
        ):
            _, attrs = parse_tag("component data={ key:: key }", None)

    def test_dict_spread(self):
        _, attrs = parse_tag("component data={ **spread }", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None),
                            ]
                        )
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    def test_dict_spread_between_key_value_pairs(self):
        _, attrs = parse_tag('component data={ "key": val, **spread, "key2": val2 }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="key2", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    # Test that dictionary keys cannot have filter arguments - The `:` is parsed as dictionary key separator
    # So instead, the content below will be parsed as key `"key"|filter`, and value `"arg":"value"'
    # And the latter is invalid because it's missing the `|` separator.
    def test_colon_in_dictionary_keys(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Filter argument (':arg') must follow a filter ('|filter')"),
        ):
            _, attrs = parse_tag('component data={"key"|filter:"arg": "value"}', None)

    def test_list_simple(self):
        _, attrs = parse_tag("component data=[1, 2, 3]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    def test_list_trailing_comma(self):
        _, attrs = parse_tag("component data=[1, 2, 3, ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]

        assert attrs == expected_attrs

    def test_lists_complex(self):
        _, attrs = parse_tag(
            """
                component
                nums=[
                    1,
                    2|add:3,
                    *spread
                ]
                items=[
                    "a"|upper,
                    'b'|lower,
                    c|default:"d"
                ]
                mixed=[
                    1,
                    [*nested],
                    {"key": "val"}
                ]
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                ),
                            ]
                        )
                    ],
                ),
                start_index=17,
            ),
            TagAttr(
                key="nums",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="add", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="3", quoted=None, spread=None, translation=False, filter=":"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="*", translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=43,
            ),
            TagAttr(
                key="items",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted="'", spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="c", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="d", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=164,
            ),
            TagAttr(
                key="mixed",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None)]
                        ),
                        TagValueStruct(
                            type="list",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="nested",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=302,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            "nums=[1, 2|add:3, *spread]",
            'items=["a"|upper, \'b\'|lower, c|default:"d"]',
            'mixed=[1, [*nested], {"key": "val"}]',
        ]

    def test_dicts_complex(self):
        _, attrs = parse_tag(
            """
            component
            simple={
                "a": 1|add:2
            }
            nested={
                "key"|upper: val|lower,
                **spread,
                "obj": {"x": 1|add:2}
            }
            filters={
                "a"|lower: "b"|upper,
                c|default: "e"|yesno:"yes,no"
            }
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
                start_index=13,
            ),
            TagAttr(
                key="simple",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="1", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="add", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="2", quoted=None, spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
            TagAttr(
                key="nested",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="spread", quoted=None, spread="**", translation=False, filter=None)
                            ]
                        ),
                        TagValue(
                            parts=[TagValuePart(value="obj", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="x", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
                start_index=99,
            ),
            TagAttr(
                key="filters",
                value=TagValueStruct(
                    type="dict",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="lower", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="c", quoted=None, spread=None, translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="e", quoted='"', spread=None, translation=False, filter=None),
                                TagValuePart(value="yesno", quoted=None, spread=None, translation=False, filter="|"),
                                TagValuePart(value="yes,no", quoted='"', spread=None, translation=False, filter=":"),
                            ]
                        ),
                    ],
                ),
                start_index=238,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            'simple={"a": 1|add:2}',
            'nested={"key"|upper: val|lower, **spread, "obj": {"x": 1|add:2}}',
            'filters={"a"|lower: "b"|upper, c|default: "e"|yesno:"yes,no"}',
        ]

    def test_mixed_complex(self):
        _, attrs = parse_tag(
            """
            component
            data={
                "items": [
                    1|add:2,
                    {"x"|upper: 2|add:3},
                    *spread_items|default:""
                ],
                "nested": {
                    "a": [
                        1|add:2,
                        *nums|default:""
                    ],
                    "b": {
                        "x": [
                            *more|default:""
                        ]
                    }
                },
                **rest|default,
                "key": _('value')|upper
            }
            """,
            None,
        )

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
                start_index=13,
            ),
            TagAttr(
                key="data",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="items", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        ),
                        TagValueStruct(
                            type="list",
                            spread=None,
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="1", quoted=None, spread=None, translation=False, filter=None
                                        ),
                                        TagValuePart(
                                            value="add",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(
                                            value="2", quoted=None, spread=None, translation=False, filter=":"
                                        ),
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    spread=None,
                                    meta={},
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="upper",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                            ]
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="3",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="spread_items",
                                            quoted=None,
                                            spread="*",
                                            translation=False,
                                            filter=None,
                                        ),
                                        TagValuePart(
                                            value="default",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter="|",
                                        ),
                                        TagValuePart(value="", quoted='"', spread=None, translation=False, filter=":"),
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="nested", quoted='"', spread=None, translation=False, filter=None)
                            ]
                        ),
                        TagValueStruct(
                            type="dict",
                            meta={},
                            spread=None,
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="a", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="list",
                                    spread=None,
                                    meta={},
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="1",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="add",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="2",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ],
                                        ),
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="nums",
                                                    quoted=None,
                                                    spread="*",
                                                    translation=False,
                                                    filter=None,
                                                ),
                                                TagValuePart(
                                                    value="default",
                                                    quoted=None,
                                                    spread=None,
                                                    translation=False,
                                                    filter="|",
                                                ),
                                                TagValuePart(
                                                    value="",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=":",
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="b", quoted='"', spread=None, translation=False, filter=None
                                        )
                                    ]
                                ),
                                TagValueStruct(
                                    type="dict",
                                    meta={},
                                    spread=None,
                                    parser=None,
                                    entries=[
                                        TagValue(
                                            parts=[
                                                TagValuePart(
                                                    value="x",
                                                    quoted='"',
                                                    spread=None,
                                                    translation=False,
                                                    filter=None,
                                                )
                                            ]
                                        ),
                                        TagValueStruct(
                                            type="list",
                                            meta={},
                                            spread=None,
                                            parser=None,
                                            entries=[
                                                TagValue(
                                                    parts=[
                                                        TagValuePart(
                                                            value="more",
                                                            quoted=None,
                                                            spread="*",
                                                            translation=False,
                                                            filter=None,
                                                        ),
                                                        TagValuePart(
                                                            value="default",
                                                            quoted=None,
                                                            spread=None,
                                                            translation=False,
                                                            filter="|",
                                                        ),
                                                        TagValuePart(
                                                            value="",
                                                            quoted='"',
                                                            spread=None,
                                                            translation=False,
                                                            filter=":",
                                                        ),
                                                    ]
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="rest", quoted=None, spread="**", translation=False, filter=None),
                                TagValuePart(value="default", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="value", quoted="'", spread=None, translation=True, filter=None),
                                TagValuePart(value="upper", quoted=None, spread=None, translation=False, filter="|"),
                            ]
                        ),
                    ],
                ),
                start_index=35,
            ),
        ]

        assert attrs == expected_attrs
        assert [a.serialize() for a in attrs] == [
            "component",
            'data={"items": [1|add:2, {"x"|upper: 2|add:3}, *spread_items|default:""], "nested": {"a": [1|add:2, *nums|default:""], "b": {"x": [*more|default:""]}}, **rest|default, "key": _(\'value\')|upper}',  # noqa: E501
        ]

    # Test that spread operator cannot be used as dictionary value
    def test_spread_as_dictionary_value(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax cannot be used in place of a dictionary value"),
        ):
            parse_tag('component data={"key": **spread}', None)

    def test_spread_with_colon_interpreted_as_key(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax cannot be used in place of a dictionary key"),
        ):
            _, attrs = parse_tag("component data={**spread|abc: 123 }", None)

    def test_spread_in_filter_position(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax cannot be used inside of a filter"),
        ):
            _, attrs = parse_tag("component data=val|...spread|abc }", None)

    def test_spread_whitespace(self):
        # NOTE: Separating `...` from its variable is NOT valid, and will result in error.
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' is missing a value"),
        ):
            _, attrs = parse_tag("component ... attrs", None)

        _, attrs = parse_tag('component dict={"a": "b", ** my_attr} list=["a", * my_list]', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
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
            TagAttr(
                key="dict",
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="b", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="my_attr", quoted=None, spread="**", translation=False, filter=None
                                ),
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
            TagAttr(
                key="list",
                value=TagValueStruct(
                    type="list",
                    meta={},
                    spread=None,
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="a", quoted='"', spread=None, translation=False, filter=None),
                            ]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="my_list", quoted=None, spread="*", translation=False, filter=None),
                            ]
                        ),
                    ],
                ),
                start_index=38,
            ),
        ]
        assert attrs == expected_attrs

    # Test that one cannot use e.g. `...`, `**`, `*` in wrong places
    def test_spread_incorrect_syntax(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '*' found outside of a list"),
        ):
            _, attrs = parse_tag('component dict={"a": "b", *my_attr}', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' found in dict. It must be used on tag attributes only"),
        ):
            _, attrs = parse_tag('component dict={"a": "b", ...my_attr}', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '**' found outside of a dictionary"),
        ):
            _, attrs = parse_tag('component list=["a", "b", **my_list]', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' found in list. It must be used on tag attributes only"),
        ):
            _, attrs = parse_tag('component list=["a", "b", ...my_list]', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '*' found outside of a list"),
        ):
            _, attrs = parse_tag("component *attrs", None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '**' found outside of a dictionary"),
        ):
            _, attrs = parse_tag("component **attrs", None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '*' found outside of a list"),
        ):
            _, attrs = parse_tag("component key=*attrs", None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '**' found outside of a dictionary"),
        ):
            _, attrs = parse_tag("component key=**attrs", None)

    # Test that one cannot do `key=...{"a": "b"}`
    def test_spread_onto_key(self):
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' cannot follow a key ('key=...attrs')"),
        ):
            _, attrs = parse_tag('component key=...{"a": "b"}', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' cannot follow a key ('key=...attrs')"),
        ):
            _, attrs = parse_tag('component key=...["a", "b"]', None)

        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Spread syntax '...' cannot follow a key ('key=...attrs')"),
        ):
            _, attrs = parse_tag("component key=...attrs", None)

    def test_spread_dict_literal_nested(self):
        _, attrs = parse_tag('component { **{"key": val2}, "key": val1 }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread=None,
                    parser=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="dict",
                            spread="**",
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="key",
                                            quoted='"',
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val2",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val1", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

        assert [a.serialize() for a in attrs] == [
            "component",
            '{**{"key": val2}, "key": val1}',
        ]

    def test_spread_dict_literal_as_attribute(self):
        _, attrs = parse_tag('component ...{"key": val2}', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    spread=None,
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    spread="...",
                    meta={},
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

        assert [a.serialize() for a in attrs] == [
            "component",
            '...{"key": val2}',
        ]

    def test_spread_list_literal_nested(self):
        _, attrs = parse_tag("component [ *[val1], val2 ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread=None,
                    parser=None,
                    meta={},
                    entries=[
                        TagValueStruct(
                            type="list",
                            spread="*",
                            meta={},
                            parser=None,
                            entries=[
                                TagValue(
                                    parts=[
                                        TagValuePart(
                                            value="val1",
                                            quoted=None,
                                            spread=None,
                                            translation=False,
                                            filter=None,
                                        )
                                    ]
                                ),
                            ],
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(value="val2", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

        assert [a.serialize() for a in attrs] == [
            "component",
            "[*[val1], val2]",
        ]

    def test_spread_list_literal_as_attribute(self):
        _, attrs = parse_tag("component ...[val1]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    parser=None,
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    spread="...",
                    parser=None,
                    meta={},
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(value="val1", quoted=None, spread=None, translation=False, filter=None)
                            ]
                        ),
                    ],
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

        assert [a.serialize() for a in attrs] == [
            "component",
            "...[val1]",
        ]

    def test_dynamic_expressions(self):
        _, attrs = parse_tag("component '{% lorem w 4 %}'", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted="'", spread=None, translation=False, filter=None
                                )
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

    def test_dynamic_expressions_in_dict(self):
        _, attrs = parse_tag('component { "key": "{% lorem w 4 %}" }', None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="dict",
                    entries=[
                        TagValue(
                            parts=[TagValuePart(value="key", quoted='"', spread=None, translation=False, filter=None)]
                        ),
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted='"', spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ]
                        ),
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs

    def test_dynamic_expressions_in_list(self):
        _, attrs = parse_tag("component [ '{% lorem w 4 %}' ]", None)

        expected_attrs = [
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="simple",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="component", quoted=None, spread=None, translation=False, filter=None
                                )  # noqa: E501
                            ],
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=0,
            ),
            TagAttr(
                key=None,
                value=TagValueStruct(
                    type="list",
                    entries=[
                        TagValue(
                            parts=[
                                TagValuePart(
                                    value="{% lorem w 4 %}", quoted="'", spread=None, translation=False, filter=None
                                )
                            ]
                        )
                    ],
                    spread=None,
                    meta={},
                    parser=None,
                ),
                start_index=10,
            ),
        ]
        assert attrs == expected_attrs


@djc_test
class TestResolver:
    def test_resolve_simple(self):
        _, attrs = parse_tag("123", None)
        resolved = attrs[0].value.resolve(Context())
        assert resolved == 123

        _, attrs = parse_tag("'123'", None)
        resolved = attrs[0].value.resolve(Context())
        assert resolved == "123"

        _, attrs = parse_tag("abc", None)
        resolved = attrs[0].value.resolve(Context({"abc": "foo"}))
        assert resolved == "foo"

    def test_resolve_list(self):
        _, attrs = parse_tag("[1, 2, 3,]", None)
        resolved = attrs[0].value.resolve(Context())
        assert resolved == [1, 2, 3]

    def test_resolve_list_with_spread(self):
        _, attrs = parse_tag("[ 1, 2, *[3, val1, *val2, 5], val3, 6 ]", None)
        resolved = attrs[0].value.resolve(Context({"val1": "foo", "val2": ["bar", "baz"], "val3": "qux"}))
        assert resolved == [1, 2, 3, "foo", "bar", "baz", 5, "qux", 6]

    def test_resolve_dict(self):
        _, attrs = parse_tag('{"a": 1, "b": 2,}', None)
        resolved = attrs[0].value.resolve(Context())
        assert resolved == {"a": 1, "b": 2}

    def test_resolve_dict_with_spread(self):
        _, attrs = parse_tag('{ **{"key": val2, **{ val3: val4 }, "key3": val4 } }', None)
        context = Context({"val2": "foo", "val3": "bar", "val4": "baz"})
        resolved = attrs[0].value.resolve(context)
        assert resolved == {"key": "foo", "bar": "baz", "key3": "baz"}

    def test_resolve_dynamic_expr(self):
        parser = _get_parser()
        _, attrs = parse_tag("'{% lorem 4 w %}'", parser)
        resolved = attrs[0].value.resolve(Context())
        assert resolved == "lorem ipsum dolor sit"

    def test_resolve_complex(self):
        parser = _get_parser()

        _, attrs = parse_tag(
            """
            data={
                "items": [
                    1|add:2,
                    {"x"|upper: 2|add:3},
                    *spread_items
                ],
                "nested": {
                    "a": [
                        1|add:2,
                        *nums|default:"",
                        *"{% lorem 1 w %}",
                    ],
                    "b": {
                        "x": [
                            *more|first,
                        ],
                        "{% lorem 2 w %}": "{% lorem 3 w %}",
                    }
                },
                **rest,
                "key": _('value')|upper
            }
            """,
            parser,
        )

        context = Context(
            {
                "spread_items": ["foo", "bar"],
                "nums": [1, 2, 3],
                "more": ["baz", "qux"],
                "rest": {"a": "b"},
            }
        )
        resolved = attrs[0].value.resolve(context)

        assert resolved == {
            "items": [3, {"X": 5}, "foo", "bar"],
            "nested": {
                "a": [3, 1, 2, 3, "l", "o", "r", "e", "m"],
                "b": {
                    "x": ["b", "a", "z"],
                    "lorem ipsum": "lorem ipsum dolor",
                },
            },
            "a": "b",
            "key": "VALUE",
        }

    @skip("TODO: Enable once template parsing is fixed by us")
    def test_resolve_complex_as_component(self):
        captured = None

        @register("test")
        class Test(Component):
            def get_context_data(self, **kwargs):
                nonlocal captured
                captured = kwargs
                return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component "test"
                data={
                    "items": [
                        1|add:2,
                        {"x"|upper: 2|add:3},
                        *spread_items
                    ],
                    "nested": {
                        "a": [
                            1|add:2,
                            *nums|default:"",
                            *"{% lorem 1 w %}",
                        ],
                        "b": {
                            "x": [
                                *more|first,
                            ],
                            "{% lorem 2 w %}": "{% lorem 3 w %}",
                        }
                    },
                    **rest,
                    "key": _('value')|upper
                }
            / %}
        """

        template = Template(template_str)
        template.render(
            Context(
                {
                    "spread_items": ["foo", "bar"],
                    "nums": [1, 2, 3],
                    "more": ["baz", "qux"],
                    "rest": {"a": "b"},
                }
            )
        )

        assert captured == {
            "items": [3, {"X": 5}, "foo", "bar"],
            "nested": {
                "a": [3, 1, 2, 3, "l", "o", "r", "e", "m"],
                "b": {
                    "x": ["b", "a", "z"],
                    "lorem ipsum": "lorem ipsum dolor",
                },
            },
            "a": "b",
            "key": "VALUE",
        }

    def test_component_args_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            template = "var"

            def get_context_data(self, *args, **kwargs):
                nonlocal captured
                captured = args, kwargs
                return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' 42 myvar key='val' key2=val2 %}
            {% endcomponent %}
        """
        Template(template_str).render(Context({"myvar": "myval", "val2": [1, 2, 3]}))

        assert captured == ((42, "myval"), {"key": "val", "key2": [1, 2, 3]})

    def test_component_special_kwargs(self):
        captured = None

        @register("test")
        class Test(Component):
            template = "var"

            def get_context_data(self, *args, **kwargs):
                nonlocal captured
                captured = args, kwargs
                return {}

        template_str: types.django_html = """
            {% load component_tags %}
            {% component 'test' date=date @lol=2 na-me=bzz @event:na-me.mod=bzz #my-id=True %}
            {% endcomponent %}
        """
        Template(template_str).render(Context({"date": 2024, "bzz": "fzz"}))

        assert captured == (
            tuple([]),
            {
                "date": 2024,
                "@lol": 2,
                "na-me": "fzz",
                "@event": {"na-me.mod": "fzz"},
                "#my-id": True,
            },
        )
