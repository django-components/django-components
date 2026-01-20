"""
This file is defined both in django-components and djc_core.template_parser to ensure compatibility.

Source of truth is djc_core.template_parser.
"""

# ruff: noqa: ARG001,ARG005,E501
import re
from typing import Any, Dict, List, Optional, Union, cast
from unittest.mock import Mock

import pytest
from djc_core.template_parser import (
    EndTag,
    ForLoopTag,
    GenericTag,
    ParserConfig,
    TagAttr,
    TagConfig,
    TagSpec,
    TagValue,
    TagValueFilter,
    TemplateVersion,
    Token,
    ValueChild,
    ValueKind,
    compile_tag,
    parse_tag,
)

###############################
# RESOLVERS
###############################


def expr_resolver(ctx, src, token, filters, tags, code):
    return f"EXPR_RESOLVED:{code}"


def template_resolver(ctx, src, token, filters, tags, expr):
    return f"TEMPLATE_RESOLVED:{expr}"


def translation_resolver(ctx, src, token, filters, tags, text):
    return f"TRANSLATION_RESOLVED:{text}"


def filter_resolver(ctx, src, token, filters, tags, name, value, arg=None):
    return f"{name}({value}, {arg})"


def variable_resolver(ctx, src, token, filters, tags, var):
    return ctx[var]


###############################
# HELPERS
###############################


def _simple_compile_tag(tag_or_attrs: Union[GenericTag, EndTag, ForLoopTag, List[TagAttr]], source: str):
    if isinstance(tag_or_attrs, (EndTag, ForLoopTag)):
        raise TypeError("EndTag and ForLoopTag are not supported for compile_tag")

    return compile_tag(
        tag_or_attrs,
        source,
        filters={},
        tags={},
        template_string=template_resolver,
        expr=expr_resolver,
        translation=translation_resolver,
        filter=filter_resolver,
        variable=variable_resolver,
    )


# Helper function to create a Token struct
# Takes content, start_index, line number, and column number
# Calculates end_index automatically as start_index + len(content)
def token(content: str, start_index: int, line: int, col: int) -> Token:
    return Token(
        content=content,
        start_index=start_index,
        end_index=start_index + len(content),
        line_col=(line, col),
    )


# Helper function to create a TagAttr
# Takes key (optional), value, and is_flag
# Calculates the token field internally from key token + "=" + value token
# If key is None, the token is just the value token
def tag_attr(key: Optional[Token], value: TagValue, is_flag: bool) -> TagAttr:
    if key is not None:
        # Calculate token content: key + "=" + value.token.content
        token_content = f"{key.content}={value.token.content}"
        attr_token = Token(
            content=token_content,
            start_index=key.start_index,
            end_index=value.token.end_index,
            line_col=key.line_col,
        )
    else:
        # If no key, token is just the value token
        attr_token = value.token
    return TagAttr(
        token=attr_token,
        key=key,
        value=value,
        is_flag=is_flag,
    )


# Helper function to create a plain TagValue with ValueKind::String.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_string_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("string"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a plain TagValue with ValueKind::Int.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_int_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("int"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a plain TagValue with ValueKind::Float.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_float_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("float"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a plain TagValue with ValueKind::Translation.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_translation_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("translation"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a plain TagValue with ValueKind::Variable.
# No filters, no children, and no assigned_variables
# Populates used_variables with a single token for the root variable name
# (the part before the first dot, or the entire variable if no dots)
# If spread is provided, the token includes the spread prefix, but value does not
def plain_variable_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    # Extract root variable name (everything before first dot, or entire content if no dot)
    root_var = content.split(".")[0] if "." in content else content
    used_var_start_index = start_index + len(spread) if spread is not None else start_index
    used_var_col = col + len(spread) if spread is not None else col
    used_var_token = token(root_var, used_var_start_index, line, used_var_col)
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("variable"),
        spread=spread,
        filters=[],
        used_variables=[used_var_token],
        assigned_variables=[],
    )


# Helper function to create a TagValue with ValueKind::String
# Creates a TagValue with empty children
def string_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("string"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a TagValue with ValueKind::Int
# Creates a TagValue with empty children
def int_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("int"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a TagValue with ValueKind::Variable
# Creates a TagValue with empty children
# Automatically computes and adds the root variable name (before first dot) to used_variables
def variable_value(
    full_token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    # Extract root variable name (everything before first dot, or entire value if no dot)
    root_var = value.content.split(".")[0] if "." in value.content else value.content
    used_var_token = token(
        root_var,
        value.start_index,
        value.line_col[0],
        value.line_col[1],
    )
    used_variables = [*used_variables, used_var_token]
    return TagValue(
        token=full_token,
        value=value,
        children=[],
        kind=ValueKind("variable"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a TagValue with ValueKind::Float
# Creates a TagValue with empty children
def float_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("float"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a TagValue with ValueKind::Translation
# Creates a TagValue with empty children
def translation_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("translation"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a plain TagValue with ValueKind::TemplateString.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_template_string_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("template_string"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a TagValue with ValueKind::TemplateString
# Creates a TagValue with empty children
def template_string_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("template_string"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a plain TagValue with ValueKind::PythonExpr.
# No filters, no children, and no used/assigned variables
# If spread is provided, the token includes the spread prefix, but value does not
def plain_python_expr_value(
    content: str,
    start_index: int,
    line: int,
    col: int,
    spread: Optional[str] = None,
) -> TagValue:
    if spread is not None:
        token_content = f"{spread}{content}"
        value_start_index = start_index + len(spread)
        value_col = col + len(spread)
        token_val = token(token_content, start_index, line, col)
        value_token = token(content, value_start_index, line, value_col)
    else:
        token_val = token(content, start_index, line, col)
        value_token = token_val
    return TagValue(
        token=token_val,
        value=value_token,
        children=[],
        kind=ValueKind("python_expr"),
        spread=spread,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a TagValue with ValueKind::PythonExpr
# Creates a TagValue with empty children
def python_expr_value(
    token: Token,
    value: Token,
    spread: Optional[str],
    filters: List[TagValueFilter],
    used_variables: List[Token],
    assigned_variables: List[Token],
) -> TagValue:
    return TagValue(
        token=token,
        value=value,
        children=[],
        kind=ValueKind("python_expr"),
        spread=spread,
        filters=filters,
        used_variables=used_variables,
        assigned_variables=assigned_variables,
    )


# Helper function to create a simple TagValue with ValueKind::Dict.
# No spread, no filters, and no used/assigned variables.
# The token and value are the same.
def plain_dict_value(
    token: Token,
    children: List[ValueChild],
) -> TagValue:
    return TagValue(
        token=token,
        value=token,
        children=children,
        kind=ValueKind("dict"),
        spread=None,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


# Helper function to create a simple TagValue with ValueKind::List.
# No spread, no filters, and no used/assigned variables.
# The token and value are the same.
def plain_list_value(
    token: Token,
    children: List[ValueChild],
) -> TagValue:
    return TagValue(
        token=token,
        value=token,
        children=children,
        kind=ValueKind("list"),
        spread=None,
        filters=[],
        used_variables=[],
        assigned_variables=[],
    )


############################################################
# TESTS
############################################################


# Test that resolvers are called correctly
class TestResolvers:
    def _setup_resolver_test(self, tag_content: str, context: Any):
        tag = parse_tag(tag_content)

        # Mock variable resolver to return different values for different variables
        def variable_side_effect(ctx, src, token, filters, tags, var):
            if var == "my_var":
                return "test_value"
            elif var == "arg":
                return "arg_value"
            return None

        mock_variable = Mock(side_effect=variable_side_effect)
        mock_template_string = Mock(return_value="resolved_template")
        mock_translation = Mock(return_value="resolved_translation")
        mock_filter = Mock(return_value="resolved_filter")
        mock_expr = Mock(return_value="resolved_expr")

        filters = {"my_filter": lambda *args, **kwargs: "<my_filter>"}
        tags = {"my_tag": lambda *args, **kwargs: "<my_tag>"}

        tag_func = compile_tag(
            tag,  # type: ignore[arg-type]
            tag_content,
            filters=filters,
            tags=tags,
            variable=mock_variable,
            template_string=mock_template_string,
            translation=mock_translation,
            filter=mock_filter,
            expr=mock_expr,
        )

        tag_func(context)

        return (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        )

    def test_variable_resolver(self):
        context = {"my_var": "test"}
        tag_content = "{% component my_var %}"
        (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        ) = self._setup_resolver_test(tag_content, context)

        # Assert variable resolver was called once with expected arguments
        mock_variable.assert_called_once()
        call_args = mock_variable.call_args
        assert call_args[0][0] == context  # context
        assert call_args[0][1] == tag_content  # source
        assert call_args[0][2] == (13, 19)  # token (start_index, end_index)
        assert call_args[0][3] == filters  # filters
        assert call_args[0][4] == tags  # tags
        assert call_args[0][5] == "my_var"  # var

        # Other resolvers should not be called
        mock_template_string.assert_not_called()
        mock_translation.assert_not_called()
        mock_filter.assert_not_called()
        mock_expr.assert_not_called()

    def test_template_string_resolver(self):
        context: Dict = {}
        tag_content = "{% component '{% lorem w 4 %}' %}"
        (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        ) = self._setup_resolver_test(tag_content, context)

        # Assert template_string resolver was called once with expected arguments
        mock_template_string.assert_called_once()
        call_args = mock_template_string.call_args
        assert call_args[0][0] == context  # context
        assert call_args[0][1] == tag_content  # source
        assert call_args[0][2] == (13, 30)  # token (start_index, end_index)
        assert call_args[0][3] == filters  # filters
        assert call_args[0][4] == tags  # tags
        assert call_args[0][5] == "{% lorem w 4 %}"  # expr

        # Other resolvers should not be called
        mock_variable.assert_not_called()
        mock_translation.assert_not_called()
        mock_filter.assert_not_called()
        mock_expr.assert_not_called()

    def test_translation_resolver(self):
        context: Dict = {}
        tag_content = '{% component _("hello world") %}'
        (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        ) = self._setup_resolver_test(tag_content, context)

        # Assert translation resolver was called once with expected arguments
        mock_translation.assert_called_once()
        call_args = mock_translation.call_args
        assert call_args[0][0] == context  # context
        assert call_args[0][1] == tag_content  # source
        assert call_args[0][2] == (13, 29)  # token (start_index, end_index)
        assert call_args[0][3] == filters  # filters
        assert call_args[0][4] == tags  # tags
        assert call_args[0][5] == "hello world"  # text (inner string without quotes)

        # Other resolvers should not be called
        mock_variable.assert_not_called()
        mock_template_string.assert_not_called()
        mock_filter.assert_not_called()
        mock_expr.assert_not_called()

    def test_expr_resolver(self):
        context: Dict = {}
        tag_content = "{% component (1 + 2) %}"
        (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        ) = self._setup_resolver_test(tag_content, context)

        # Assert expr resolver was called once with expected arguments
        mock_expr.assert_called_once()
        call_args = mock_expr.call_args
        assert call_args[0][0] == context  # context
        assert call_args[0][1] == tag_content  # source
        assert call_args[0][2] == (13, 20)  # token (start_index, end_index)
        assert call_args[0][3] == filters  # filters
        assert call_args[0][4] == tags  # tags
        assert call_args[0][5] == "(1 + 2)"  # code

        # Other resolvers should not be called
        mock_variable.assert_not_called()
        mock_template_string.assert_not_called()
        mock_translation.assert_not_called()
        mock_filter.assert_not_called()

    def test_filter_resolver(self):
        context: Dict = {}
        tag_content = "{% component my_var|upper:arg %}"
        (
            mock_variable,
            mock_template_string,
            mock_translation,
            mock_filter,
            mock_expr,
            filters,
            tags,
        ) = self._setup_resolver_test(tag_content, context)

        # Assert filter resolver was called once with expected arguments
        mock_filter.assert_called_once()
        call_args = mock_filter.call_args
        assert call_args[0][0] == context  # context
        assert call_args[0][1] == tag_content  # source
        assert call_args[0][2] == (
            19,
            29,
        )  # token (start_index, end_index) - filter token |upper:arg
        assert call_args[0][3] == filters  # filters
        assert call_args[0][4] == tags  # tags
        assert call_args[0][5] == "upper"  # name
        assert call_args[0][6] == "test_value"  # value (from variable resolver)
        assert call_args[0][7] == "arg_value"  # arg (from variable resolver)

        # Variable resolver should be called twice (for the value and arg)
        assert mock_variable.call_count == 2

        # Other resolvers should not be called
        mock_template_string.assert_not_called()
        mock_translation.assert_not_called()
        mock_expr.assert_not_called()


class TestTagParser:
    def test_args_kwargs(self):
        tag_content = "{% component 'my_comp' key=val key2='val2 two' %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'my_comp'", 13, 1, 14),
                    key=None,
                    value=plain_string_value("'my_comp'", 13, 1, 14, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key=val", 23, 1, 24),
                    key=token("key", 23, 1, 24),
                    value=plain_variable_value("val", 27, 1, 28, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key2='val2 two'", 31, 1, 32),
                    key=token("key2", 31, 1, 32),
                    value=plain_string_value("'val2 two'", 36, 1, 37, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("val", 27, 1, 28)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val": [1, 2, 3]})

        assert args == ["my_comp"]
        assert kwargs == [("key", [1, 2, 3]), ("key2", "val2 two")]

    def test_nested_quotes(self):
        tag_content = "{% component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'my_comp'", 13, 1, 14),
                    key=None,
                    value=plain_string_value("'my_comp'", 13, 1, 14, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key=val", 23, 1, 24),
                    key=token("key", 23, 1, 24),
                    value=plain_variable_value("val", 27, 1, 28, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key2='val2 \"two\"'", 31, 1, 32),
                    key=token("key2", 31, 1, 32),
                    value=plain_string_value("'val2 \"two\"'", 36, 1, 37, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('text="organisation\'s"', 49, 1, 50),
                    key=token("text", 49, 1, 50),
                    value=plain_string_value('"organisation\'s"', 54, 1, 55, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("val", 27, 1, 28)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val": "some_value"})

        assert args == ["my_comp"]
        assert kwargs == [
            ("key", "some_value"),
            ("key2", 'val2 "two"'),
            ("text", "organisation's"),
        ]

    def test_trailing_quote_single(self):
        # Unclosed quote in positional arg
        with pytest.raises(
            SyntaxError,
            match="expected self_closing_slash, attribute, filter, or COMMENT",
        ):
            parse_tag("{% component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" 'abc %}")

    def test_trailing_quote_double(self):
        # Unclosed double quote in positional arg
        with pytest.raises(
            SyntaxError,
            match="expected self_closing_slash, attribute, filter, or COMMENT",
        ):
            parse_tag('{% component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' "abc %}')

    def test_trailing_quote_as_value_single(self):
        # Unclosed quote in key=value pair
        with pytest.raises(SyntaxError, match="expected value"):
            parse_tag("{% component 'my_comp' key=val key2='val2 \"two\"' text=\"organisation's\" value='abc %}")

    def test_trailing_quote_as_value_double(self):
        # Unclosed double quote in key=value pair
        with pytest.raises(SyntaxError, match="expected value"):
            parse_tag('{% component "my_comp" key=val key2="val2 \'two\'" text=\'organisation"s\' value="abc %}')


class TestTranslation:
    def test_translation(self):
        tag_content = '{% component "my_comp" _("one") key=_("two") %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('"my_comp"', 13, 1, 14),
                    key=None,
                    value=plain_string_value('"my_comp"', 13, 1, 14, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('_("one")', 23, 1, 24),
                    key=None,
                    value=plain_translation_value('_("one")', 23, 1, 24, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('key=_("two")', 32, 1, 33),
                    key=token("key", 32, 1, 33),
                    value=plain_translation_value('_("two")', 36, 1, 37, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["my_comp", "TRANSLATION_RESOLVED:one"]
        assert kwargs == [("key", "TRANSLATION_RESOLVED:two")]

    def test_translation_whitespace(self):
        tag_content = '{% component value=_(  "test"  ) %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('value=_(  "test"  )', 13, 1, 14),
                    key=token("value", 13, 1, 14),
                    value=translation_value(
                        token('_(  "test"  )', 19, 1, 20),
                        Token('_("test")', 19, 32, (1, 20)),
                        None,
                        [],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("value", "TRANSLATION_RESOLVED:test")]

    def test_translation_with_filter(self):
        tag_content = '{% component _("hello")|upper %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('_("hello")|upper', 13, 1, 14),
                    key=None,
                    value=translation_value(
                        token('_("hello")|upper', 13, 1, 14),
                        token('_("hello")', 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|upper", 23, 1, 24),
                                name=token("upper", 24, 1, 25),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["upper(TRANSLATION_RESOLVED:hello, None)"]
        assert kwargs == []

    def test_translation_as_filter_arg(self):
        tag_content = '{% component my_var|default:_("fallback") %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('my_var|default:_("fallback")', 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token('my_var|default:_("fallback")', 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token('|default:_("fallback")', 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_translation_value('_("fallback")', 28, 1, 29, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None})

        assert args == ["default(None, TRANSLATION_RESOLVED:fallback)"]
        assert kwargs == []

    def test_translation_in_list(self):
        tag_content = '{% component [_("one"), _("two"), _("three")] %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('[_("one"), _("two"), _("three")]', 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token('[_("one"), _("two"), _("three")]', 13, 1, 14),
                        [
                            ValueChild(plain_translation_value('_("one")', 14, 1, 15, None)),
                            ValueChild(plain_translation_value('_("two")', 24, 1, 25, None)),
                            ValueChild(plain_translation_value('_("three")', 34, 1, 35, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [
            [
                "TRANSLATION_RESOLVED:one",
                "TRANSLATION_RESOLVED:two",
                "TRANSLATION_RESOLVED:three",
            ]
        ]
        assert kwargs == []

    def test_translation_in_dict(self):
        tag_content = '{% component {key: _("value")|upper} %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('{key: _("value")|upper}', 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token('{key: _("value")|upper}', 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("key", 14, 1, 15, None)),
                            ValueChild(
                                translation_value(
                                    token('_("value")|upper', 19, 1, 20),
                                    token('_("value")', 19, 1, 20),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 29, 1, 30),
                                            name=token("upper", 30, 1, 31),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("key", 14, 1, 15)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"key": "some_key"})

        assert args == [{"some_key": "upper(TRANSLATION_RESOLVED:value, None)"}]
        assert kwargs == []


class TestFilter:
    def test_tag_parser_filters(self):
        tag_content = '{% component "my_comp" value|lower key=val|yesno:"yes,no" key2=val2|default:"N/A"|upper %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('"my_comp"', 13, 1, 14),
                    key=None,
                    value=plain_string_value('"my_comp"', 13, 1, 14, None),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("value|lower", 23, 1, 24),
                    key=None,
                    value=variable_value(
                        token("value|lower", 23, 1, 24),
                        token("value", 23, 1, 24),
                        None,
                        [
                            TagValueFilter(
                                token=token("|lower", 28, 1, 29),
                                name=token("lower", 29, 1, 30),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('key=val|yesno:"yes,no"', 35, 1, 36),
                    key=token("key", 35, 1, 36),
                    value=variable_value(
                        token('val|yesno:"yes,no"', 39, 1, 40),
                        token("val", 39, 1, 40),
                        None,
                        [
                            TagValueFilter(
                                token=token('|yesno:"yes,no"', 42, 1, 43),
                                name=token("yesno", 43, 1, 44),
                                arg=plain_string_value('"yes,no"', 49, 1, 50, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('key2=val2|default:"N/A"|upper', 58, 1, 59),
                    key=token("key2", 58, 1, 59),
                    value=variable_value(
                        token('val2|default:"N/A"|upper', 63, 1, 64),
                        token("val2", 63, 1, 64),
                        None,
                        [
                            TagValueFilter(
                                token=token('|default:"N/A"', 67, 1, 68),
                                name=token("default", 68, 1, 69),
                                arg=plain_string_value('"N/A"', 76, 1, 77, None),
                            ),
                            TagValueFilter(
                                token=token("|upper", 81, 1, 82),
                                name=token("upper", 82, 1, 83),
                                arg=None,
                            ),
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("value", 23, 1, 24),
                token("val", 39, 1, 40),
                token("val2", 63, 1, 64),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"value": "HELLO", "val": True, "val2": None})

        assert args == ["my_comp", "lower(HELLO, None)"]
        assert kwargs == [
            ("key", "yesno(True, yes,no)"),
            ("key2", "upper(default(None, N/A), None)"),
        ]

    def test_filter_whitespace(self):
        tag_content = "{% component value  |  lower    key=val  |  upper    key2=val2 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("value  |  lower", 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token("value  |  lower", 13, 1, 14),
                        token("value", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|  lower", 20, 1, 21),
                                name=token("lower", 23, 1, 24),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key=val  |  upper", 32, 1, 33),
                    key=token("key", 32, 1, 33),
                    value=variable_value(
                        token("val  |  upper", 36, 1, 37),
                        token("val", 36, 1, 37),
                        None,
                        [
                            TagValueFilter(
                                token=token("|  upper", 41, 1, 42),
                                name=token("upper", 44, 1, 45),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token("key2=val2", 53, 1, 54),
                    key=token("key2", 53, 1, 54),
                    value=plain_variable_value("val2", 58, 1, 59, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("value", 13, 1, 14),
                token("val", 36, 1, 37),
                token("val2", 58, 1, 59),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"value": "HELLO", "val": "world", "val2": "test"})

        assert args == ["lower(HELLO, None)"]
        assert kwargs == [
            ("key", "upper(world, None)"),
            ("key2", "test"),
        ]

    def test_filter_argument_must_follow_filter(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected self_closing_slash, filter, or COMMENT"),
        ):
            parse_tag('{% component value=val|yesno:"yes,no":arg %}')


class TestFloat:
    def test_float_simple_as_arg(self):
        tag_content = "{% component -1.5 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("-1.5", 13, 1, 14),
                    key=None,
                    value=plain_float_value("-1.5", 13, 1, 14, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [-1.5]
        assert kwargs == []

    def test_float_simple_as_kwarg(self):
        tag_content = "{% component key=+2. %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("key=+2.", 13, 1, 14),
                    key=token("key", 13, 1, 14),
                    value=plain_float_value("+2.", 17, 1, 18, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("key", 2.0)]

    def test_float_with_filter(self):
        tag_content = "{% component -1.2e2|abs %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("-1.2e2|abs", 13, 1, 14),
                    key=None,
                    value=float_value(
                        token("-1.2e2|abs", 13, 1, 14),
                        token("-1.2e2", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|abs", 19, 1, 20),
                                name=token("abs", 20, 1, 21),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["abs(-120.0, None)"]
        assert kwargs == []

    def test_float_as_filter_arg(self):
        tag_content = "{% component 42.5|add:.2e-02 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("42.5|add:.2e-02", 13, 1, 14),
                    key=None,
                    value=float_value(
                        token("42.5|add:.2e-02", 13, 1, 14),
                        token("42.5", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|add:.2e-02", 17, 1, 18),
                                name=token("add", 18, 1, 19),
                                arg=plain_float_value(".2e-02", 22, 1, 23, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["add(42.5, 0.002)"]
        assert kwargs == []

    def test_float_in_list(self):
        tag_content = "{% component [-1.5, +2., -1.2e2, .2e-02] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[-1.5, +2., -1.2e2, .2e-02]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[-1.5, +2., -1.2e2, .2e-02]", 13, 1, 14),
                        [
                            ValueChild(plain_float_value("-1.5", 14, 1, 15, None)),
                            ValueChild(plain_float_value("+2.", 20, 1, 21, None)),
                            ValueChild(plain_float_value("-1.2e2", 25, 1, 26, None)),
                            ValueChild(plain_float_value(".2e-02", 33, 1, 34, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [[-1.5, 2.0, -120.0, 0.002]]
        assert kwargs == []

    def test_float_in_dict(self):
        tag_content = "{% component {key: -1.5|add:.2e-02} %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("{key: -1.5|add:.2e-02}", 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token("{key: -1.5|add:.2e-02}", 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("key", 14, 1, 15, None)),
                            ValueChild(
                                float_value(
                                    token("-1.5|add:.2e-02", 19, 1, 20),
                                    token("-1.5", 19, 1, 20),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|add:.2e-02", 23, 1, 24),
                                            name=token("add", 24, 1, 25),
                                            arg=plain_float_value(".2e-02", 28, 1, 29, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("key", 14, 1, 15)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"key": "some_key"})

        assert args == [{"some_key": "add(-1.5, 0.002)"}]
        assert kwargs == []


class TestInt:
    def test_int_simple_as_arg(self):
        tag_content = "{% component -42 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("-42", 13, 1, 14),
                    key=None,
                    value=plain_int_value("-42", 13, 1, 14, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [-42]
        assert kwargs == []

    def test_int_simple_as_kwarg(self):
        tag_content = "{% component key=123 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("key=123", 13, 1, 14),
                    key=token("key", 13, 1, 14),
                    value=plain_int_value("123", 17, 1, 18, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("key", 123)]

    def test_int_with_filter(self):
        tag_content = "{% component -42|abs %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("-42|abs", 13, 1, 14),
                    key=None,
                    value=int_value(
                        token("-42|abs", 13, 1, 14),
                        token("-42", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|abs", 16, 1, 17),
                                name=token("abs", 17, 1, 18),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["abs(-42, None)"]
        assert kwargs == []

    def test_int_as_filter_arg(self):
        tag_content = "{% component 42|add:-5 %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("42|add:-5", 13, 1, 14),
                    key=None,
                    value=int_value(
                        token("42|add:-5", 13, 1, 14),
                        token("42", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|add:-5", 15, 1, 16),
                                name=token("add", 16, 1, 17),
                                arg=plain_int_value("-5", 20, 1, 21, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["add(42, -5)"]
        assert kwargs == []

    def test_int_in_list(self):
        tag_content = "{% component [-42, 123, 0, -1] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[-42, 123, 0, -1]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[-42, 123, 0, -1]", 13, 1, 14),
                        [
                            ValueChild(plain_int_value("-42", 14, 1, 15, None)),
                            ValueChild(plain_int_value("123", 19, 1, 20, None)),
                            ValueChild(plain_int_value("0", 24, 1, 25, None)),
                            ValueChild(plain_int_value("-1", 27, 1, 28, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [[-42, 123, 0, -1]]
        assert kwargs == []

    def test_int_in_dict(self):
        tag_content = "{% component {key: -42|add:5} %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("{key: -42|add:5}", 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token("{key: -42|add:5}", 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("key", 14, 1, 15, None)),
                            ValueChild(
                                int_value(
                                    token("-42|add:5", 19, 1, 20),
                                    token("-42", 19, 1, 20),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|add:5", 22, 1, 23),
                                            name=token("add", 23, 1, 24),
                                            arg=plain_int_value("5", 27, 1, 28, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("key", 14, 1, 15)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"key": "some_key"})

        assert args == [{"some_key": "add(-42, 5)"}]
        assert kwargs == []


class TestString:
    def test_string_simple_as_arg(self):
        tag_content = "{% component 'hello' %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'hello'", 13, 1, 14),
                    key=None,
                    value=plain_string_value("'hello'", 13, 1, 14, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["hello"]
        assert kwargs == []

    def test_string_simple_as_kwarg(self):
        tag_content = '{% component key="world" %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('key="world"', 13, 1, 14),
                    key=token("key", 13, 1, 14),
                    value=plain_string_value('"world"', 17, 1, 18, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("key", "world")]

    def test_string_with_filter(self):
        tag_content = "{% component 'hello'|upper %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'hello'|upper", 13, 1, 14),
                    key=None,
                    value=string_value(
                        token("'hello'|upper", 13, 1, 14),
                        token("'hello'", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|upper", 20, 1, 21),
                                name=token("upper", 21, 1, 22),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["upper(hello, None)"]
        assert kwargs == []

    def test_string_as_filter_arg(self):
        tag_content = '{% component "test"|default:"default_value" %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('"test"|default:"default_value"', 13, 1, 14),
                    key=None,
                    value=string_value(
                        token('"test"|default:"default_value"', 13, 1, 14),
                        token('"test"', 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token('|default:"default_value"', 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_string_value('"default_value"', 28, 1, 29, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["default(test, default_value)"]
        assert kwargs == []

    def test_string_in_list(self):
        tag_content = "{% component ['hello', \"world\", 'test'] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("['hello', \"world\", 'test']", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("['hello', \"world\", 'test']", 13, 1, 14),
                        [
                            ValueChild(plain_string_value("'hello'", 14, 1, 15, None)),
                            ValueChild(plain_string_value('"world"', 23, 1, 24, None)),
                            ValueChild(plain_string_value("'test'", 32, 1, 33, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [["hello", "world", "test"]]
        assert kwargs == []

    def test_string_in_dict(self):
        tag_content = '{% component {key: "hello"|upper} %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('{key: "hello"|upper}', 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token('{key: "hello"|upper}', 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("key", 14, 1, 15, None)),
                            ValueChild(
                                string_value(
                                    token('"hello"|upper', 19, 1, 20),
                                    token('"hello"', 19, 1, 20),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 26, 1, 27),
                                            name=token("upper", 27, 1, 28),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("key", 14, 1, 15)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"key": "some_key"})

        assert args == [{"some_key": "upper(hello, None)"}]
        assert kwargs == []


class TestVariable:
    def test_variable_simple_as_arg(self):
        tag_content = "{% component my_var %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("my_var", 13, 1, 14),
                    key=None,
                    value=plain_variable_value("my_var", 13, 1, 14, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": "test_value"})

        assert args == ["test_value"]
        assert kwargs == []

    def test_variable_simple_as_kwarg(self):
        tag_content = "{% component key=my_var %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("key=my_var", 13, 1, 14),
                    key=token("key", 13, 1, 14),
                    value=plain_variable_value("my_var", 17, 1, 18, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 17, 1, 18)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": "test_value"})

        assert args == []
        assert kwargs == [("key", "test_value")]

    def test_variable_with_filter(self):
        tag_content = "{% component my_var|upper %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("my_var|upper", 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token("my_var|upper", 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|upper", 19, 1, 20),
                                name=token("upper", 20, 1, 21),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": "hello"})

        assert args == ["upper(hello, None)"]
        assert kwargs == []

    def test_variable_as_filter_arg(self):
        tag_content = "{% component my_var|default:other_var %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("my_var|default:other_var", 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token("my_var|default:other_var", 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|default:other_var", 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_variable_value("other_var", 28, 1, 29, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("my_var", 13, 1, 14),
                token("other_var", 28, 1, 29),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None, "other_var": "fallback"})

        assert args == ["default(None, fallback)"]
        assert kwargs == []

    def test_variable_in_list(self):
        tag_content = "{% component [var1, var2, var3] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[var1, var2, var3]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[var1, var2, var3]", 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("var1", 14, 1, 15, None)),
                            ValueChild(plain_variable_value("var2", 20, 1, 21, None)),
                            ValueChild(plain_variable_value("var3", 26, 1, 27, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("var1", 14, 1, 15),
                token("var2", 20, 1, 21),
                token("var3", 26, 1, 27),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"var1": "value1", "var2": "value2", "var3": "value3"})

        assert args == [["value1", "value2", "value3"]]
        assert kwargs == []

    def test_variable_in_dict(self):
        tag_content = "{% component {key: my_var|upper} %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("{key: my_var|upper}", 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token("{key: my_var|upper}", 13, 1, 14),
                        [
                            ValueChild(plain_variable_value("key", 14, 1, 15, None)),
                            ValueChild(
                                variable_value(
                                    token("my_var|upper", 19, 1, 20),
                                    token("my_var", 19, 1, 20),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 25, 1, 26),
                                            name=token("upper", 26, 1, 27),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("key", 14, 1, 15),
                token("my_var", 19, 1, 20),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"key": "some_key", "my_var": "hello"})

        assert args == [{"some_key": "upper(hello, None)"}]
        assert kwargs == []


class TestPythonExpr:
    def test_python_expr_as_arg(self):
        tag_content = "{% component ('hello'.append(myvar)) %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("('hello'.append(myvar))", 13, 1, 14),
                    key=None,
                    value=TagValue(
                        token=token("('hello'.append(myvar))", 13, 1, 14),
                        value=token("('hello'.append(myvar))", 13, 1, 14),
                        children=[],
                        kind=ValueKind("python_expr"),
                        spread=None,
                        filters=[],
                        used_variables=[token("myvar", 29, 1, 30)],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("myvar", 29, 1, 30)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["EXPR_RESOLVED:('hello'.append(myvar))"]
        assert kwargs == []

    def test_python_expr_simple_as_kwarg(self):
        tag_content = "{% component key=('world'.append(myvar)) %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("key=('world'.append(myvar))", 13, 1, 14),
                    key=token("key", 13, 1, 14),
                    value=TagValue(
                        token=token("('world'.append(myvar))", 17, 1, 18),
                        value=token("('world'.append(myvar))", 17, 1, 18),
                        children=[],
                        kind=ValueKind("python_expr"),
                        spread=None,
                        filters=[],
                        used_variables=[token("myvar", 33, 1, 34)],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("myvar", 33, 1, 34)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("key", "EXPR_RESOLVED:('world'.append(myvar))")]

    def test_python_expr_with_filter(self):
        tag_content = "{% component ('test'.upper())|lower %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("('test'.upper())|lower", 13, 1, 14),
                    key=None,
                    value=python_expr_value(
                        token("('test'.upper())|lower", 13, 1, 14),
                        token("('test'.upper())", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|lower", 29, 1, 30),
                                name=token("lower", 30, 1, 31),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["lower(EXPR_RESOLVED:('test'.upper()), None)"]
        assert kwargs == []

    def test_python_expr_as_filter_arg(self):
        tag_content = "{% component my_var|default:('fallback'.append(myvar)) %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("my_var|default:('fallback'.append(myvar))", 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token("my_var|default:('fallback'.append(myvar))", 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|default:('fallback'.append(myvar))", 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=TagValue(
                                    token=token("('fallback'.append(myvar))", 28, 1, 29),
                                    value=token("('fallback'.append(myvar))", 28, 1, 29),
                                    children=[],
                                    kind=ValueKind("python_expr"),
                                    spread=None,
                                    filters=[],
                                    used_variables=[token("myvar", 47, 1, 48)],
                                    assigned_variables=[],
                                ),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14), token("myvar", 47, 1, 48)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None})

        assert args == ["default(None, EXPR_RESOLVED:('fallback'.append(myvar)))"]
        assert kwargs == []

    def test_python_expr_in_list(self):
        tag_content = "{% component [('one'.upper()), ('two'.lower())] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token(
                        "[('one'.upper()), ('two'.lower())]",
                        13,
                        1,
                        14,
                    ),
                    key=None,
                    value=plain_list_value(
                        token(
                            "[('one'.upper()), ('two'.lower())]",
                            13,
                            1,
                            14,
                        ),
                        [
                            ValueChild(plain_python_expr_value("('one'.upper())", 14, 1, 15, None)),
                            ValueChild(plain_python_expr_value("('two'.lower())", 31, 1, 32, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [
            [
                "EXPR_RESOLVED:('one'.upper())",
                "EXPR_RESOLVED:('two'.lower())",
            ]
        ]
        assert kwargs == []

    def test_python_expr_in_dict(self):
        tag_content = "{% component {('key'.upper()): ('val'.lower())|upper} %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("{('key'.upper()): ('val'.lower())|upper}", 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token(
                            "{('key'.upper()): ('val'.lower())|upper}",
                            13,
                            1,
                            14,
                        ),
                        [
                            ValueChild(plain_python_expr_value("('key'.upper())", 14, 1, 15, None)),
                            ValueChild(
                                python_expr_value(
                                    token("('val'.lower())|upper", 31, 1, 32),
                                    token("('val'.lower())", 31, 1, 32),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 46, 1, 47),
                                            name=token("upper", 47, 1, 48),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == [{"EXPR_RESOLVED:('key'.upper())": "upper(EXPR_RESOLVED:('val'.lower()), None)"}]
        assert kwargs == []


class TestEndTag:
    def test_endtag_normal(self):
        tag_content = "{% endslot %}"
        tag = parse_tag(tag_content)

        expected_tag = EndTag(
            token=token(tag_content, 0, 1, 1),
            name=token("endslot", 3, 1, 4),
        )

        assert tag == expected_tag

    def test_endtag_just_end(self):
        tag_content = "{% end %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("end", 3, 1, 4),
            attrs=[],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

    def test_endtag_no_whitespace(self):
        tag_content = "{%endslot%}"
        tag = parse_tag(tag_content)

        expected_tag = EndTag(
            token=token(tag_content, 0, 1, 1),
            name=token("endslot", 2, 1, 3),
        )

        assert tag == expected_tag

    def test_endtag_with_comments(self):
        tag_content = "{% {# comment #} endslot {# another #} %}"
        tag = parse_tag(tag_content)

        expected_tag = EndTag(
            token=token(tag_content, 0, 1, 1),
            name=token("endslot", 17, 1, 18),
        )

        assert tag == expected_tag

    def test_endtag_with_attrs_errors(self):
        tag_content = "{% endslot key=val %}"
        with pytest.raises(SyntaxError, match="End tags can only contain the tag name"):
            parse_tag(tag_content)

    def test_endtag_self_closing_errors(self):
        tag_content = "{% endslot / %}"
        with pytest.raises(SyntaxError, match="End tags can only contain the tag name"):
            parse_tag(tag_content)

    def test_endtag_different_names(self):
        tag_content = "{% endif %}"
        tag = parse_tag(tag_content)

        expected_tag = EndTag(
            token=token(tag_content, 0, 1, 1),
            name=token("endif", 3, 1, 4),
        )

        assert tag == expected_tag

        tag_content2 = "{% endfor %}"
        tag2 = parse_tag(tag_content2)

        expected_tag2 = EndTag(
            token=token(tag_content2, 0, 1, 1),
            name=token("endfor", 3, 1, 4),
        )

        assert tag2 == expected_tag2


class TestForLoopTag:
    def test_forloop_basic(self):
        tag_content = "{% for item in items %}"
        tag = parse_tag(tag_content)

        expected_tag = ForLoopTag(
            token=token(tag_content, 0, 1, 1),
            name=token("for", 3, 1, 4),
            targets=[token("item", 7, 1, 8)],
            iterable=plain_variable_value("items", 15, 1, 16, None),
            used_variables=[token("items", 15, 1, 16)],
            assigned_variables=[],
        )

        assert tag == expected_tag

    def test_forloop_multiple_targets(self):
        tag_content = "{% for x, y, z in matrix %}"
        tag = parse_tag(tag_content)

        expected_tag = ForLoopTag(
            token=token(tag_content, 0, 1, 1),
            name=token("for", 3, 1, 4),
            targets=[
                token("x", 7, 1, 8),
                token("y", 10, 1, 11),
                token("z", 13, 1, 14),
            ],
            iterable=plain_variable_value("matrix", 18, 1, 19, None),
            used_variables=[token("matrix", 18, 1, 19)],
            assigned_variables=[],
        )

        assert tag == expected_tag

    def test_forloop_with_filter_on_iterable(self):
        tag_content = "{% for item in items|filter:arg %}"
        tag = parse_tag(tag_content)

        expected_tag = ForLoopTag(
            token=token(tag_content, 0, 1, 1),
            name=token("for", 3, 1, 4),
            targets=[token("item", 7, 1, 8)],
            iterable=variable_value(
                token("items|filter:arg", 15, 1, 16),
                token("items", 15, 1, 16),
                None,
                [
                    TagValueFilter(
                        token=token("|filter:arg", 20, 1, 21),
                        name=token("filter", 21, 1, 22),
                        arg=plain_variable_value("arg", 28, 1, 29, None),
                    )
                ],
                [],
                [],
            ),
            used_variables=[token("items", 15, 1, 16), token("arg", 28, 1, 29)],
            assigned_variables=[],
        )

        assert tag == expected_tag

    def test_forloop_with_python_expr_iterable(self):
        tag_content = "{% for item in (items + other_items) %}"
        tag = parse_tag(tag_content)

        expected_tag = ForLoopTag(
            token=token(tag_content, 0, 1, 1),
            name=token("for", 3, 1, 4),
            targets=[token("item", 7, 1, 8)],
            iterable=TagValue(
                token=token("(items + other_items)", 15, 1, 16),
                value=token("(items + other_items)", 15, 1, 16),
                children=[],
                kind=ValueKind("python_expr"),
                spread=None,
                filters=[],
                used_variables=[
                    token("items", 16, 1, 17),
                    token("other_items", 24, 1, 25),
                ],
                assigned_variables=[],
            ),
            used_variables=[token("items", 16, 1, 17), token("other_items", 24, 1, 25)],
            assigned_variables=[],
        )

        assert tag == expected_tag

    def test_forloop_missing_in_keyword(self):
        tag_content = "{% for item items %}"
        with pytest.raises(SyntaxError):
            parse_tag(tag_content)

    def test_forloop_missing_iterable(self):
        tag_content = "{% for item in %}"
        with pytest.raises(SyntaxError):
            parse_tag(tag_content)

    def test_forloop_missing_targets(self):
        tag_content = "{% for in items %}"
        with pytest.raises(SyntaxError):
            parse_tag(tag_content)

    def test_forloop_self_closing_error(self):
        tag_content = "{% for item in items / %}"
        with pytest.raises(SyntaxError):
            parse_tag(tag_content)


class TestDict:
    def test_dict_simple(self):
        tag_content = '{% component data={ "key": "val" } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('data={ "key": "val" }', 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_dict_value(
                        token('{ "key": "val" }', 18, 1, 19),
                        [
                            ValueChild(plain_string_value('"key"', 20, 1, 21, None)),
                            ValueChild(plain_string_value('"val"', 27, 1, 28, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("data", {"key": "val"})]

    def test_dict_trailing_comma(self):
        tag_content = '{% component data={ "key": "val", } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('data={ "key": "val", }', 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_dict_value(
                        token('{ "key": "val", }', 18, 1, 19),
                        [
                            ValueChild(plain_string_value('"key"', 20, 1, 21, None)),
                            ValueChild(plain_string_value('"val"', 27, 1, 28, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("data", {"key": "val"})]

    def test_dict_with_filter(self):
        tag_content = '{% component data={ "key": "val" }|upper %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('data={ "key": "val" }|upper', 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=TagValue(
                        token=token('{ "key": "val" }|upper', 18, 1, 19),
                        value=token('{ "key": "val" }', 18, 1, 19),
                        children=[
                            ValueChild(plain_string_value('"key"', 20, 1, 21, None)),
                            ValueChild(plain_string_value('"val"', 27, 1, 28, None)),
                        ],
                        kind=ValueKind("dict"),
                        spread=None,
                        filters=[
                            TagValueFilter(
                                token=token("|upper", 34, 1, 35),
                                name=token("upper", 35, 1, 36),
                                arg=None,
                            )
                        ],
                        used_variables=[],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("data", "upper({'key': 'val'}, None)")]

    def test_dict_as_filter_arg(self):
        tag_content = '{% component my_var|default:{ "key": "val" } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('my_var|default:{ "key": "val" }', 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token('my_var|default:{ "key": "val" }', 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token('|default:{ "key": "val" }', 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_dict_value(
                                    token('{ "key": "val" }', 28, 1, 29),
                                    [
                                        ValueChild(plain_string_value('"key"', 30, 1, 31, None)),
                                        ValueChild(plain_string_value('"val"', 37, 1, 38, None)),
                                    ],
                                ),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None})

        assert args == ["default(None, {'key': 'val'})"]
        assert kwargs == []

    def test_dict_missing_colon(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected filter_noarg or COMMENT"),
        ):
            parse_tag('{% component data={ "key" } %}')

    def test_dict_missing_colon_2(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected filter_chain_noarg or COMMENT"),
        ):
            parse_tag('{% component data={ "key", "val" } %}')

    def test_dict_extra_colon(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value or COMMENT"),
        ):
            parse_tag("{% component data={ key:: key } %}")

    def test_dict_spread(self):
        tag_content = "{% component data={ **spread } %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("data={ **spread }", 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_dict_value(
                        token("{ **spread }", 18, 1, 19),
                        [
                            ValueChild(plain_variable_value("spread", 20, 1, 21, "**")),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("spread", 22, 1, 23)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({"spread": {"key": "val"}})
        assert args1 == []
        assert kwargs1 == [("data", {"key": "val"})]

        args2, kwargs2 = tag_func({"spread": {}})
        assert args2 == []
        assert kwargs2 == [("data", {})]

        with pytest.raises(
            TypeError,
            match=re.escape("'list' object is not a mapping"),
        ):
            tag_func({"spread": [1, 2, 3]})

        with pytest.raises(
            TypeError,
            match=re.escape("'int' object is not a mapping"),
        ):
            tag_func({"spread": 3})

        with pytest.raises(
            TypeError,
            match=re.escape("'NoneType' object is not a mapping"),
        ):
            tag_func({"spread": None})

    def test_dict_spread_between_key_value_pairs(self):
        tag_content = '{% component data={ "key": val, **spread, "key2": val2 } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('data={ "key": val, **spread, "key2": val2 }', 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_dict_value(
                        token('{ "key": val, **spread, "key2": val2 }', 18, 1, 19),
                        [
                            ValueChild(plain_string_value('"key"', 20, 1, 21, None)),
                            ValueChild(plain_variable_value("val", 27, 1, 28, None)),
                            ValueChild(plain_variable_value("spread", 32, 1, 33, "**")),
                            ValueChild(plain_string_value('"key2"', 42, 1, 43, None)),
                            ValueChild(plain_variable_value("val2", 50, 1, 51, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("val", 27, 1, 28),
                token("spread", 34, 1, 35),
                token("val2", 50, 1, 51),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({"spread": {"a": 1}, "val": "HELLO", "val2": "WORLD"})
        assert args1 == []
        assert kwargs1 == [("data", {"key": "HELLO", "a": 1, "key2": "WORLD"})]

    # Test that dictionary keys cannot have filter arguments - The `:` is parsed as dictionary key separator
    # So instead, the content below will be parsed as key `"key"|filter`, and value `"arg":"value"'
    # And the latter is invalid because it's missing the `|` separator.
    def test_colon_in_dictionary_keys(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected filter_chain or COMMENT"),
        ):
            parse_tag('{% component data={"key"|filter:"arg": "value"} %}')

    def test_dicts_complex(self):
        # NOTE: In this example, it looks like e.g. `"e"` should be a filter argument
        # to `c|default`. BUT! variables like `c|default` are inside a dictionary,
        # so the `:` is preferentially interpreted as dictionary key separator (`{key: val}`).
        # So e.g. line `{c|default: "e"|yesno:"yes,no"}`
        # actually means `{<key>: <val>}`,
        # where `<key>` is `c|default` and `val` is `"e"|yesno:"yes,no"`.
        tag_content = """
            {% component
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
            %}"""
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content[13:], 13, 2, 13),
            name=token("component", 16, 2, 16),
            attrs=[
                TagAttr(
                    token=token(
                        'simple={\n                "a": 1|add:2\n            }',
                        38,
                        3,
                        13,
                    ),
                    key=token("simple", 38, 3, 13),
                    value=plain_dict_value(
                        token('{\n                "a": 1|add:2\n            }', 45, 3, 20),
                        [
                            ValueChild(plain_string_value('"a"', 63, 4, 17, None)),
                            ValueChild(
                                int_value(
                                    token("1|add:2", 68, 4, 22),
                                    token("1", 68, 4, 22),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|add:2", 69, 4, 23),
                                            name=token("add", 70, 4, 24),
                                            arg=plain_int_value("2", 74, 4, 28, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token(
                        'nested={\n                "key"|upper: val|lower,\n                **spread,\n                "obj": {"x": 1|add:2}\n            }',
                        102,
                        6,
                        13,
                    ),
                    key=token("nested", 102, 6, 13),
                    value=plain_dict_value(
                        token(
                            '{\n                "key"|upper: val|lower,\n                **spread,\n                "obj": {"x": 1|add:2}\n            }',
                            109,
                            6,
                            20,
                        ),
                        [
                            ValueChild(
                                string_value(
                                    token('"key"|upper', 127, 7, 17),
                                    token('"key"', 127, 7, 17),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 132, 7, 22),
                                            name=token("upper", 133, 7, 23),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                variable_value(
                                    token("val|lower", 140, 7, 30),
                                    token("val", 140, 7, 30),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|lower", 143, 7, 33),
                                            name=token("lower", 144, 7, 34),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(plain_variable_value("spread", 167, 8, 17, "**")),
                            ValueChild(plain_string_value('"obj"', 193, 9, 17, None)),
                            ValueChild(
                                plain_dict_value(
                                    token('{"x": 1|add:2}', 200, 9, 24),
                                    [
                                        ValueChild(plain_string_value('"x"', 201, 9, 25, None)),
                                        ValueChild(
                                            int_value(
                                                token("1|add:2", 206, 9, 30),
                                                token("1", 206, 9, 30),
                                                None,
                                                [
                                                    TagValueFilter(
                                                        token=token("|add:2", 207, 9, 31),
                                                        name=token("add", 208, 9, 32),
                                                        arg=plain_int_value("2", 212, 9, 36, None),
                                                    )
                                                ],
                                                [],
                                                [],
                                            )
                                        ),
                                    ],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token(
                        'filters={\n                "a"|lower: "b"|upper,\n                c|default: "e"|yesno:"yes,no"\n            }',
                        241,
                        11,
                        13,
                    ),
                    key=token("filters", 241, 11, 13),
                    value=plain_dict_value(
                        token(
                            '{\n                "a"|lower: "b"|upper,\n                c|default: "e"|yesno:"yes,no"\n            }',
                            249,
                            11,
                            21,
                        ),
                        [
                            ValueChild(
                                string_value(
                                    token('"a"|lower', 267, 12, 17),
                                    token('"a"', 267, 12, 17),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|lower", 270, 12, 20),
                                            name=token("lower", 271, 12, 21),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                string_value(
                                    token('"b"|upper', 278, 12, 28),
                                    token('"b"', 278, 12, 28),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 281, 12, 31),
                                            name=token("upper", 282, 12, 32),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                variable_value(
                                    token("c|default", 305, 13, 17),
                                    token("c", 305, 13, 17),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|default", 306, 13, 18),
                                            name=token("default", 307, 13, 19),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                string_value(
                                    token('"e"|yesno:"yes,no"', 316, 13, 28),
                                    token('"e"', 316, 13, 28),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token('|yesno:"yes,no"', 319, 13, 31),
                                            name=token("yesno", 320, 13, 32),
                                            arg=plain_string_value('"yes,no"', 326, 13, 38, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("val", 140, 7, 30),
                token("spread", 169, 8, 19),
                token("c", 305, 13, 17),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({"spread": {6: 7}, "c": None, "val": "bar"})
        assert args1 == []
        assert kwargs1 == [
            ("simple", {"a": "add(1, 2)"}),
            (
                "nested",
                {
                    "upper(key, None)": "lower(bar, None)",
                    6: 7,
                    "obj": {"x": "add(1, 2)"},
                },
            ),
            (
                "filters",
                {
                    "lower(a, None)": "upper(b, None)",
                    "default(None, None)": "yesno(e, yes,no)",
                },
            ),
        ]


class TestList:
    def test_list_simple(self):
        tag_content = "{% component data=[1, 2, 3] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("data=[1, 2, 3]", 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_list_value(
                        token("[1, 2, 3]", 18, 1, 19),
                        [
                            ValueChild(plain_int_value("1", 19, 1, 20, None)),
                            ValueChild(plain_int_value("2", 22, 1, 23, None)),
                            ValueChild(plain_int_value("3", 25, 1, 26, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({})
        assert args1 == []
        assert kwargs1 == [("data", [1, 2, 3])]

    def test_list_trailing_comma(self):
        tag_content = "{% component data=[1, 2, 3, ] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("data=[1, 2, 3, ]", 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_list_value(
                        token("[1, 2, 3, ]", 18, 1, 19),
                        [
                            ValueChild(plain_int_value("1", 19, 1, 20, None)),
                            ValueChild(plain_int_value("2", 22, 1, 23, None)),
                            ValueChild(plain_int_value("3", 25, 1, 26, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({})
        assert args1 == []
        assert kwargs1 == [("data", [1, 2, 3])]

    def test_list_with_filter(self):
        tag_content = "{% component data=[1, 2, 3]|upper %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("data=[1, 2, 3]|upper", 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=TagValue(
                        token=token("[1, 2, 3]|upper", 18, 1, 19),
                        value=token("[1, 2, 3]", 18, 1, 19),
                        children=[
                            ValueChild(plain_int_value("1", 19, 1, 20, None)),
                            ValueChild(plain_int_value("2", 22, 1, 23, None)),
                            ValueChild(plain_int_value("3", 25, 1, 26, None)),
                        ],
                        kind=ValueKind("list"),
                        spread=None,
                        filters=[
                            TagValueFilter(
                                token=token("|upper", 27, 1, 28),
                                name=token("upper", 28, 1, 29),
                                arg=None,
                            )
                        ],
                        used_variables=[],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == []
        assert kwargs == [("data", "upper([1, 2, 3], None)")]

    def test_list_as_filter_arg(self):
        tag_content = "{% component my_var|default:[1, 2, 3] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("my_var|default:[1, 2, 3]", 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token("my_var|default:[1, 2, 3]", 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|default:[1, 2, 3]", 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_list_value(
                                    token("[1, 2, 3]", 28, 1, 29),
                                    [
                                        ValueChild(plain_int_value("1", 29, 1, 30, None)),
                                        ValueChild(plain_int_value("2", 32, 1, 33, None)),
                                        ValueChild(plain_int_value("3", 35, 1, 36, None)),
                                    ],
                                ),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None})

        assert args == ["default(None, [1, 2, 3])"]
        assert kwargs == []

    def test_lists_complex(self):
        tag_content = """
                {% component
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
            %}"""
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content[17:], 17, 2, 17),
            name=token("component", 20, 2, 20),
            attrs=[
                TagAttr(
                    token=token(
                        "nums=[\n                    1,\n                    2|add:3,\n                    *spread\n                ]",
                        46,
                        3,
                        17,
                    ),
                    key=token("nums", 46, 3, 17),
                    value=plain_list_value(
                        token(
                            "[\n                    1,\n                    2|add:3,\n                    *spread\n                ]",
                            51,
                            3,
                            22,
                        ),
                        [
                            ValueChild(plain_int_value("1", 73, 4, 21, None)),
                            ValueChild(
                                int_value(
                                    token("2|add:3", 96, 5, 21),
                                    token("2", 96, 5, 21),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|add:3", 97, 5, 22),
                                            name=token("add", 98, 5, 23),
                                            arg=plain_int_value("3", 102, 5, 27, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(plain_variable_value("spread", 125, 6, 21, "*")),
                        ],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token(
                        'items=[\n                    "a"|upper,\n                    \'b\'|lower,\n                    c|default:"d"\n                ]',
                        167,
                        8,
                        17,
                    ),
                    key=token("items", 167, 8, 17),
                    value=plain_list_value(
                        token(
                            '[\n                    "a"|upper,\n                    \'b\'|lower,\n                    c|default:"d"\n                ]',
                            173,
                            8,
                            23,
                        ),
                        [
                            ValueChild(
                                string_value(
                                    token('"a"|upper', 195, 9, 21),
                                    token('"a"', 195, 9, 21),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 198, 9, 24),
                                            name=token("upper", 199, 9, 25),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                string_value(
                                    token("'b'|lower", 226, 10, 21),
                                    token("'b'", 226, 10, 21),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|lower", 229, 10, 24),
                                            name=token("lower", 230, 10, 25),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(
                                variable_value(
                                    token('c|default:"d"', 257, 11, 21),
                                    token("c", 257, 11, 21),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token('|default:"d"', 258, 11, 22),
                                            name=token("default", 259, 11, 23),
                                            arg=plain_string_value('"d"', 267, 11, 31, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token(
                        'mixed=[\n                    1,\n                    [*nested],\n                    {"key": "val"}\n                ]',
                        305,
                        13,
                        17,
                    ),
                    key=token("mixed", 305, 13, 17),
                    value=plain_list_value(
                        token(
                            '[\n                    1,\n                    [*nested],\n                    {"key": "val"}\n                ]',
                            311,
                            13,
                            23,
                        ),
                        [
                            ValueChild(plain_int_value("1", 333, 14, 21, None)),
                            ValueChild(
                                plain_list_value(
                                    token("[*nested]", 356, 15, 21),
                                    [ValueChild(plain_variable_value("nested", 357, 15, 22, "*"))],
                                )
                            ),
                            ValueChild(
                                plain_dict_value(
                                    token('{"key": "val"}', 387, 16, 21),
                                    [
                                        ValueChild(plain_string_value('"key"', 388, 16, 22, None)),
                                        ValueChild(plain_string_value('"val"', 395, 16, 29, None)),
                                    ],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("spread", 126, 6, 22),
                token("c", 257, 11, 21),
                token("nested", 358, 15, 23),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({"nested": [1, 2, 3], "spread": [5, 6], "c": None})
        assert args1 == []
        assert kwargs1 == [
            ("nums", [1, "add(2, 3)", 5, 6]),
            ("items", ["upper(a, None)", "lower(b, None)", "default(None, d)"]),
            ("mixed", [1, [1, 2, 3], {"key": "val"}]),
        ]

    def test_mixed_complex(self):
        tag_content = """
            {% component
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
                **rest|injectd,
                "key": _('value')|upper
            }
            %}"""
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content[13:], 13, 2, 13),
            name=token("component", 16, 2, 16),
            attrs=[
                TagAttr(
                    token=token(
                        'data={\n                "items": [\n                    1|add:2,\n                    {"x"|upper: 2|add:3},\n                    *spread_items|default:""\n                ],\n                "nested": {\n                    "a": [\n                        1|add:2,\n                        *nums|default:""\n                    ],\n                    "b": {\n                        "x": [\n                            *more|default:""\n                        ]\n                    }\n                },\n                **rest|injectd,\n                "key": _(\'value\')|upper\n            }',
                        38,
                        3,
                        13,
                    ),
                    key=token("data", 38, 3, 13),
                    value=plain_dict_value(
                        token(
                            '{\n                "items": [\n                    1|add:2,\n                    {"x"|upper: 2|add:3},\n                    *spread_items|default:""\n                ],\n                "nested": {\n                    "a": [\n                        1|add:2,\n                        *nums|default:""\n                    ],\n                    "b": {\n                        "x": [\n                            *more|default:""\n                        ]\n                    }\n                },\n                **rest|injectd,\n                "key": _(\'value\')|upper\n            }',
                            43,
                            3,
                            18,
                        ),
                        [
                            ValueChild(plain_string_value('"items"', 61, 4, 17, None)),
                            ValueChild(
                                plain_list_value(
                                    token(
                                        '[\n                    1|add:2,\n                    {"x"|upper: 2|add:3},\n                    *spread_items|default:""\n                ]',
                                        70,
                                        4,
                                        26,
                                    ),
                                    [
                                        ValueChild(
                                            int_value(
                                                token("1|add:2", 92, 5, 21),
                                                token("1", 92, 5, 21),
                                                None,
                                                [
                                                    TagValueFilter(
                                                        token=token("|add:2", 93, 5, 22),
                                                        name=token("add", 94, 5, 23),
                                                        arg=plain_int_value("2", 98, 5, 27, None),
                                                    )
                                                ],
                                                [],
                                                [],
                                            )
                                        ),
                                        ValueChild(
                                            plain_dict_value(
                                                token('{"x"|upper: 2|add:3}', 121, 6, 21),
                                                [
                                                    ValueChild(
                                                        string_value(
                                                            token('"x"|upper', 122, 6, 22),
                                                            token('"x"', 122, 6, 22),
                                                            None,
                                                            [
                                                                TagValueFilter(
                                                                    token=token(
                                                                        "|upper",
                                                                        125,
                                                                        6,
                                                                        25,
                                                                    ),
                                                                    name=token(
                                                                        "upper",
                                                                        126,
                                                                        6,
                                                                        26,
                                                                    ),
                                                                    arg=None,
                                                                )
                                                            ],
                                                            [],
                                                            [],
                                                        )
                                                    ),
                                                    ValueChild(
                                                        int_value(
                                                            token("2|add:3", 133, 6, 33),
                                                            token("2", 133, 6, 33),
                                                            None,
                                                            [
                                                                TagValueFilter(
                                                                    token=token(
                                                                        "|add:3",
                                                                        134,
                                                                        6,
                                                                        34,
                                                                    ),
                                                                    name=token(
                                                                        "add",
                                                                        135,
                                                                        6,
                                                                        35,
                                                                    ),
                                                                    arg=plain_int_value(
                                                                        "3",
                                                                        139,
                                                                        6,
                                                                        39,
                                                                        None,
                                                                    ),
                                                                )
                                                            ],
                                                            [],
                                                            [],
                                                        )
                                                    ),
                                                ],
                                            )
                                        ),
                                        ValueChild(
                                            variable_value(
                                                token(
                                                    '*spread_items|default:""',
                                                    163,
                                                    7,
                                                    21,
                                                ),
                                                token("spread_items", 164, 7, 22),
                                                "*",
                                                [
                                                    TagValueFilter(
                                                        token=token('|default:""', 176, 7, 34),
                                                        name=token("default", 177, 7, 35),
                                                        arg=plain_string_value('""', 185, 7, 43, None),
                                                    )
                                                ],
                                                [],
                                                [],
                                            )
                                        ),
                                    ],
                                )
                            ),
                            ValueChild(plain_string_value('"nested"', 223, 9, 17, None)),
                            ValueChild(
                                plain_dict_value(
                                    token(
                                        '{\n                    "a": [\n                        1|add:2,\n                        *nums|default:""\n                    ],\n                    "b": {\n                        "x": [\n                            *more|default:""\n                        ]\n                    }\n                }',
                                        233,
                                        9,
                                        27,
                                    ),
                                    [
                                        ValueChild(plain_string_value('"a"', 255, 10, 21, None)),
                                        ValueChild(
                                            plain_list_value(
                                                token(
                                                    '[\n                        1|add:2,\n                        *nums|default:""\n                    ]',
                                                    260,
                                                    10,
                                                    26,
                                                ),
                                                [
                                                    ValueChild(
                                                        int_value(
                                                            token("1|add:2", 286, 11, 25),
                                                            token("1", 286, 11, 25),
                                                            None,
                                                            [
                                                                TagValueFilter(
                                                                    token=token(
                                                                        "|add:2",
                                                                        287,
                                                                        11,
                                                                        26,
                                                                    ),
                                                                    name=token(
                                                                        "add",
                                                                        288,
                                                                        11,
                                                                        27,
                                                                    ),
                                                                    arg=plain_int_value(
                                                                        "2",
                                                                        292,
                                                                        11,
                                                                        31,
                                                                        None,
                                                                    ),
                                                                )
                                                            ],
                                                            [],
                                                            [],
                                                        )
                                                    ),
                                                    ValueChild(
                                                        variable_value(
                                                            token(
                                                                '*nums|default:""',
                                                                319,
                                                                12,
                                                                25,
                                                            ),
                                                            token("nums", 320, 12, 26),
                                                            "*",
                                                            [
                                                                TagValueFilter(
                                                                    token=token(
                                                                        '|default:""',
                                                                        324,
                                                                        12,
                                                                        30,
                                                                    ),
                                                                    name=token(
                                                                        "default",
                                                                        325,
                                                                        12,
                                                                        31,
                                                                    ),
                                                                    arg=plain_string_value(
                                                                        '""',
                                                                        333,
                                                                        12,
                                                                        39,
                                                                        None,
                                                                    ),
                                                                )
                                                            ],
                                                            [],
                                                            [],
                                                        )
                                                    ),
                                                ],
                                            )
                                        ),
                                        ValueChild(plain_string_value('"b"', 379, 14, 21, None)),
                                        ValueChild(
                                            plain_dict_value(
                                                token(
                                                    '{\n                        "x": [\n                            *more|default:""\n                        ]\n                    }',
                                                    384,
                                                    14,
                                                    26,
                                                ),
                                                [
                                                    ValueChild(plain_string_value('"x"', 410, 15, 25, None)),
                                                    ValueChild(
                                                        plain_list_value(
                                                            token(
                                                                '[\n                            *more|default:""\n                        ]',
                                                                415,
                                                                15,
                                                                30,
                                                            ),
                                                            [
                                                                ValueChild(
                                                                    variable_value(
                                                                        token(
                                                                            '*more|default:""',
                                                                            445,
                                                                            16,
                                                                            29,
                                                                        ),
                                                                        token(
                                                                            "more",
                                                                            446,
                                                                            16,
                                                                            30,
                                                                        ),
                                                                        "*",
                                                                        [
                                                                            TagValueFilter(
                                                                                token=token(
                                                                                    '|default:""',
                                                                                    450,
                                                                                    16,
                                                                                    34,
                                                                                ),
                                                                                name=token(
                                                                                    "default",
                                                                                    451,
                                                                                    16,
                                                                                    35,
                                                                                ),
                                                                                arg=plain_string_value(
                                                                                    '""',
                                                                                    459,
                                                                                    16,
                                                                                    43,
                                                                                    None,
                                                                                ),
                                                                            )
                                                                        ],
                                                                        [],
                                                                        [],
                                                                    )
                                                                ),
                                                            ],
                                                        )
                                                    ),
                                                ],
                                            )
                                        ),
                                    ],
                                )
                            ),
                            ValueChild(
                                variable_value(
                                    token("**rest|injectd", 545, 20, 17),
                                    token("rest", 547, 20, 19),
                                    "**",
                                    [
                                        TagValueFilter(
                                            token=token("|injectd", 551, 20, 23),
                                            name=token("injectd", 552, 20, 24),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                            ValueChild(plain_string_value('"key"', 577, 21, 17, None)),
                            ValueChild(
                                translation_value(
                                    token("_('value')|upper", 584, 21, 24),
                                    token("_('value')", 584, 21, 24),
                                    None,
                                    [
                                        TagValueFilter(
                                            token=token("|upper", 594, 21, 34),
                                            name=token("upper", 595, 21, 35),
                                            arg=None,
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("spread_items", 164, 7, 22),
                token("nums", 320, 12, 26),
                token("more", 446, 16, 30),
                token("rest", 547, 20, 19),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        def custom_filter(ctx, src, token, filters, tags, name, value, arg=None):
            if name == "injectd":
                return {**value, "injected": True}
            else:
                return f"{name}({value}, {arg})"

        tag_func = compile_tag(
            tag,  # type: ignore[arg-type]
            tag_content,
            filters={},
            tags={},
            template_string=template_resolver,
            expr=expr_resolver,
            translation=translation_resolver,
            filter=custom_filter,
            variable=variable_resolver,
        )
        args1, kwargs1 = tag_func(
            {
                "spread_items": None,
                "nums": [1, 2, 3],
                "more": "x",
                "rest": {"a": "b"},
            }
        )
        assert args1 == []
        assert kwargs1 == [
            (
                "data",
                {
                    "items": [
                        "add(1, 2)",
                        {"upper(x, None)": "add(2, 3)"},
                        *list("default(None, )"),
                    ],
                    "nested": {
                        "a": ["add(1, 2)", *list("default([1, 2, 3], )")],
                        "b": {"x": [*list("default(x, )")]},
                    },
                    "a": "b",
                    "injected": True,
                    "key": "upper(TRANSLATION_RESOLVED:value, None)",
                },
            ),
        ]


class TestSpread:
    # Test that spread operator cannot be used as dictionary value
    def test_spread_as_dictionary_value(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value or COMMENT"),
        ):
            parse_tag('{% component data={"key": **spread} %}')

    # NOTE: The Rust parser actually parses this successfully,
    # treating `**spread|abc: 123` as a `spread` variable with a filter `abc`
    # that has an argument `123`.
    def test_spread_with_colon_interpreted_as_key(self):
        tag_content = "{% component data={**spread|abc: 123 } %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component data={**spread|abc: 123 } %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("data={**spread|abc: 123 }", 13, 1, 14),
                    key=token("data", 13, 1, 14),
                    value=plain_dict_value(
                        token("{**spread|abc: 123 }", 18, 1, 19),
                        [
                            ValueChild(
                                variable_value(
                                    token("**spread|abc: 123", 19, 1, 20),
                                    token("spread", 21, 1, 22),
                                    "**",
                                    [
                                        TagValueFilter(
                                            token=token("|abc: 123", 27, 1, 28),
                                            name=token("abc", 28, 1, 29),
                                            arg=plain_int_value("123", 33, 1, 34, None),
                                        )
                                    ],
                                    [],
                                    [],
                                )
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("spread", 21, 1, 22)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        # Override the filter resolver for this test
        def custom_filter(ctx, src, token, filters, tags, name, value, arg=None):
            if name == "abc":
                return {
                    **value,
                    "ABC": arg,
                }
            else:
                return f"{name}({value}, {arg})"

        tag_func = compile_tag(
            tag,  # type: ignore[arg-type]
            tag_content,
            filters={},
            tags={},
            template_string=template_resolver,
            expr=expr_resolver,
            translation=translation_resolver,
            filter=custom_filter,
            variable=variable_resolver,
        )
        args1, kwargs1 = tag_func({"spread": {6: 7}})
        assert args1 == []
        assert kwargs1 == [
            ("data", {6: 7, "ABC": 123}),
        ]

    def test_spread_in_filter_position(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected filter_name or COMMENT"),
        ):
            parse_tag("{% component data=val|...spread|abc } %}")

    def test_spread_whitespace_1(self):
        # NOTE: Separating `...` from its variable is NOT valid, and will result in error.
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            parse_tag("{% component ... attrs %}")

    # NOTE: But there CAN be whitespace between `*` / `**` and the value,
    #       because we're scoped inside `{ ... }` dict or `[ ... ]` list.
    def test_spread_whitespace_2(self):
        tag_content = '{% component dict={"a": "b", ** my_attr} list=["a", * my_list] %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(
                '{% component dict={"a": "b", ** my_attr} list=["a", * my_list] %}',
                0,
                1,
                1,
            ),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('dict={"a": "b", ** my_attr}', 13, 1, 14),
                    key=token("dict", 13, 1, 14),
                    value=plain_dict_value(
                        token('{"a": "b", ** my_attr}', 18, 1, 19),
                        [
                            ValueChild(plain_string_value('"a"', 19, 1, 20, None)),
                            ValueChild(plain_string_value('"b"', 24, 1, 25, None)),
                            ValueChild(
                                TagValue(
                                    token=token("** my_attr", 29, 1, 30),
                                    value=token("my_attr", 32, 1, 33),
                                    children=[],
                                    kind=ValueKind("variable"),
                                    spread="**",
                                    filters=[],
                                    used_variables=[token("my_attr", 32, 1, 33)],
                                    assigned_variables=[],
                                ),
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
                TagAttr(
                    token=token('list=["a", * my_list]', 41, 1, 42),
                    key=token("list", 41, 1, 42),
                    value=plain_list_value(
                        token('["a", * my_list]', 46, 1, 47),
                        [
                            ValueChild(plain_string_value('"a"', 47, 1, 48, None)),
                            ValueChild(
                                TagValue(
                                    token=token("* my_list", 52, 1, 53),
                                    value=token("my_list", 54, 1, 55),
                                    children=[],
                                    kind=ValueKind("variable"),
                                    spread="*",
                                    filters=[],
                                    used_variables=[token("my_list", 54, 1, 55)],
                                    assigned_variables=[],
                                ),
                            ),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("my_attr", 32, 1, 33),
                token("my_list", 54, 1, 55),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args1, kwargs1 = tag_func({"my_attr": {6: 7}, "my_list": [8, 9]})
        assert args1 == []
        assert kwargs1 == [
            ("dict", {"a": "b", 6: 7}),
            ("list", ["a", 8, 9]),
        ]

        with pytest.raises(
            TypeError,
            match=re.escape("list' object is not a mapping"),
        ):
            tag_func({"my_attr": [6, 7], "my_list": [8, 9]})

        # NOTE: This still works because even tho my_list is not a list,
        #       dictionaries are still iterable (same as dict.keys()).
        args2, kwargs2 = tag_func({"my_attr": {6: 7}, "my_list": {8: 9}})
        assert args2 == []
        assert kwargs2 == [
            ("dict", {"a": "b", 6: 7}),
            ("list", ["a", 8]),
        ]

    # Test that one cannot use e.g. `...`, `**`, `*` in wrong places
    def test_spread_incorrect_syntax(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected dict_item_spread_op, dict_key, or COMMENT"),
        ):
            parse_tag('{% component dict={"a": "b", *my_attr} %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected dict_item_spread_op, dict_key, or COMMENT"),
        ):
            _ = parse_tag('{% component dict={"a": "b", ...my_attr} %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value or COMMENT"),
        ):
            _ = parse_tag('{% component list=["a", "b", **my_list] %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected list_item or COMMENT"),
        ):
            _ = parse_tag('{% component list=["a", "b", ...my_list] %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected self_closing_slash, attribute, or COMMENT"),
        ):
            _ = parse_tag("{% component *attrs %}")

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected self_closing_slash, attribute, or COMMENT"),
        ):
            _ = parse_tag("{% component **attrs %}")

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            _ = parse_tag("{% component key=*attrs %}")

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            _ = parse_tag("{% component key=**attrs %}")

    # Test that one cannot do `key=...{"a": "b"}`
    def test_spread_onto_key(self):
        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            parse_tag('{% component key=...{"a": "b"} %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            parse_tag('{% component key=...["a", "b"] %}')

        with pytest.raises(
            SyntaxError,
            match=re.escape("expected value"),
        ):
            parse_tag("{% component key=...attrs %}")

    def test_spread_dict_literal_nested(self):
        tag_content = '{% component { **{"key": val2}, "key": val1 } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token('{% component { **{"key": val2}, "key": val1 } %}', 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('{ **{"key": val2}, "key": val1 }', 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token('{ **{"key": val2}, "key": val1 }', 13, 1, 14),
                        [
                            ValueChild(
                                TagValue(
                                    token=token('**{"key": val2}', 15, 1, 16),
                                    value=token('{"key": val2}', 17, 1, 18),
                                    children=[
                                        ValueChild(plain_string_value('"key"', 18, 1, 19, None)),
                                        ValueChild(plain_variable_value("val2", 25, 1, 26, None)),
                                    ],
                                    kind=ValueKind("dict"),
                                    spread="**",
                                    filters=[],
                                    used_variables=[],
                                    assigned_variables=[],
                                )
                            ),
                            ValueChild(plain_string_value('"key"', 32, 1, 33, None)),
                            ValueChild(plain_variable_value("val1", 39, 1, 40, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("val2", 25, 1, 26),
                token("val1", 39, 1, 40),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [{"key": 1}]
        assert kwargs == []

    def test_spread_dict_literal_as_attribute(self):
        tag_content = '{% component ...{"key": val2} %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token('{% component ...{"key": val2} %}', 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('...{"key": val2}', 13, 1, 14),
                    key=None,
                    value=TagValue(
                        token=token('...{"key": val2}', 13, 1, 14),
                        value=token('{"key": val2}', 16, 1, 17),
                        children=[
                            ValueChild(plain_string_value('"key"', 17, 1, 18, None)),
                            ValueChild(plain_variable_value("val2", 24, 1, 25, None)),
                        ],
                        kind=ValueKind("dict"),
                        spread="...",
                        filters=[],
                        used_variables=[],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("val2", 24, 1, 25)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == []
        assert kwargs == [("key", 2)]

    def test_spread_list_literal_nested(self):
        tag_content = "{% component [ *[val1], val2 ] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component [ *[val1], val2 ] %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[ *[val1], val2 ]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[ *[val1], val2 ]", 13, 1, 14),
                        [
                            ValueChild(
                                TagValue(
                                    token=token("*[val1]", 15, 1, 16),
                                    value=token("[val1]", 16, 1, 17),
                                    children=[
                                        ValueChild(plain_variable_value("val1", 17, 1, 18, None)),
                                    ],
                                    kind=ValueKind("list"),
                                    spread="*",
                                    filters=[],
                                    used_variables=[],
                                    assigned_variables=[],
                                )
                            ),
                            ValueChild(plain_variable_value("val2", 24, 1, 25, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("val1", 17, 1, 18),
                token("val2", 24, 1, 25),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [[1, 2]]
        assert kwargs == []

    def test_spread_list_literal_as_attribute(self):
        tag_content = "{% component ...[val1] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component ...[val1] %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("...[val1]", 13, 1, 14),
                    key=None,
                    value=TagValue(
                        token=token("...[val1]", 13, 1, 14),
                        value=token("[val1]", 16, 1, 17),
                        children=[
                            ValueChild(plain_variable_value("val1", 17, 1, 18, None)),
                        ],
                        kind=ValueKind("list"),
                        spread="...",
                        filters=[],
                        used_variables=[],
                        assigned_variables=[],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("val1", 17, 1, 18)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [1]
        assert kwargs == []


class TestTemplateString:
    def test_template_string(self):
        tag_content = "{% component '{% lorem w 4 %}' %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component '{% lorem w 4 %}' %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'{% lorem w 4 %}'", 13, 1, 14),
                    key=None,
                    value=plain_template_string_value("'{% lorem w 4 %}'", 13, 1, 14, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == ["TEMPLATE_RESOLVED:{% lorem w 4 %}"]
        assert kwargs == []

    def test_template_string_in_dict(self):
        tag_content = '{% component { "key": "{% lorem w 4 %}" } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token('{% component { "key": "{% lorem w 4 %}" } %}', 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('{ "key": "{% lorem w 4 %}" }', 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token('{ "key": "{% lorem w 4 %}" }', 13, 1, 14),
                        [
                            ValueChild(plain_string_value('"key"', 15, 1, 16, None)),
                            ValueChild(plain_template_string_value('"{% lorem w 4 %}"', 22, 1, 23, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [{"key": "TEMPLATE_RESOLVED:{% lorem w 4 %}"}]
        assert kwargs == []

    def test_template_string_in_list(self):
        tag_content = "{% component [ '{% lorem w 4 %}' ] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component [ '{% lorem w 4 %}' ] %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[ '{% lorem w 4 %}' ]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[ '{% lorem w 4 %}' ]", 13, 1, 14),
                        [
                            ValueChild(plain_template_string_value("'{% lorem w 4 %}'", 15, 1, 16, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [["TEMPLATE_RESOLVED:{% lorem w 4 %}"]]
        assert kwargs == []

    def test_template_string_with_filter(self):
        tag_content = "{% component '{% lorem w 4 %}'|upper %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("'{% lorem w 4 %}'|upper", 13, 1, 14),
                    key=None,
                    value=template_string_value(
                        token("'{% lorem w 4 %}'|upper", 13, 1, 14),
                        token("'{% lorem w 4 %}'", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token("|upper", 30, 1, 31),
                                name=token("upper", 31, 1, 32),
                                arg=None,
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({})

        assert args == ["upper(TEMPLATE_RESOLVED:{% lorem w 4 %}, None)"]
        assert kwargs == []

    def test_template_string_as_filter_arg(self):
        tag_content = '{% component my_var|default:"{% lorem w 4 %}" %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token(tag_content, 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('my_var|default:"{% lorem w 4 %}"', 13, 1, 14),
                    key=None,
                    value=variable_value(
                        token('my_var|default:"{% lorem w 4 %}"', 13, 1, 14),
                        token("my_var", 13, 1, 14),
                        None,
                        [
                            TagValueFilter(
                                token=token('|default:"{% lorem w 4 %}"', 19, 1, 20),
                                name=token("default", 20, 1, 21),
                                arg=plain_template_string_value('"{% lorem w 4 %}"', 28, 1, 29, None),
                            )
                        ],
                        [],
                        [],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("my_var", 13, 1, 14)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"my_var": None})

        assert args == ["default(None, TEMPLATE_RESOLVED:{% lorem w 4 %})"]
        assert kwargs == []


class TestComments:
    def test_comments(self):
        tag_content = "{% component {# comment #} val %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component {# comment #} val %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("val", 27, 1, 28),
                    key=None,
                    value=plain_variable_value("val", 27, 1, 28, None),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[token("val", 27, 1, 28)],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val": 1, "val2": 2})
        assert args == [1]
        assert kwargs == []

    def test_comments_within_list(self):
        tag_content = "{% component [ *[val1], {# comment #} val2 ] %}"
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token("{% component [ *[val1], {# comment #} val2 ] %}", 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token("[ *[val1], {# comment #} val2 ]", 13, 1, 14),
                    key=None,
                    value=plain_list_value(
                        token("[ *[val1], {# comment #} val2 ]", 13, 1, 14),
                        [
                            ValueChild(
                                TagValue(
                                    token=token("*[val1]", 15, 1, 16),
                                    value=token("[val1]", 16, 1, 17),
                                    children=[
                                        ValueChild(plain_variable_value("val1", 17, 1, 18, None)),
                                    ],
                                    kind=ValueKind("list"),
                                    spread="*",
                                    filters=[],
                                    used_variables=[],
                                    assigned_variables=[],
                                )
                            ),
                            ValueChild(plain_variable_value("val2", 38, 1, 39, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[
                token("val1", 17, 1, 18),
                token("val2", 38, 1, 39),
            ],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [[1, 2]]
        assert kwargs == []

    def test_comments_within_dict(self):
        tag_content = '{% component { "key": "123" {# comment #} } %}'
        tag = parse_tag(tag_content)

        expected_tag = GenericTag(
            token=token('{% component { "key": "123" {# comment #} } %}', 0, 1, 1),
            name=token("component", 3, 1, 4),
            attrs=[
                TagAttr(
                    token=token('{ "key": "123" {# comment #} }', 13, 1, 14),
                    key=None,
                    value=plain_dict_value(
                        token('{ "key": "123" {# comment #} }', 13, 1, 14),
                        children=[
                            ValueChild(plain_string_value('"key"', 15, 1, 16, None)),
                            ValueChild(plain_string_value('"123"', 22, 1, 23, None)),
                        ],
                    ),
                    is_flag=False,
                ),
            ],
            is_self_closing=False,
            used_variables=[],
            assigned_variables=[],
        )

        assert tag == expected_tag

        tag_func = _simple_compile_tag(tag, tag_content)
        args, kwargs = tag_func({"val1": 1, "val2": 2})
        assert args == [{"key": "123"}]
        assert kwargs == []


class TestParamsOrder:
    def test_arg_after_kwarg_is_error(self):
        tag_content = "{% my_tag key='value' positional_arg %}"
        ast = parse_tag(input=tag_content)
        with pytest.raises(SyntaxError, match="positional argument follows keyword argument"):
            _simple_compile_tag(ast, tag_content)

    def test_arg_after_dict_spread_is_error(self):
        tag_content = "{% my_tag ...{'key': 'value'} positional_arg %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)

        with pytest.raises(SyntaxError, match="positional argument follows keyword argument"):
            tag_func({})

    def test_arg_after_list_spread_is_ok(self):
        tag_content = "{% my_tag ...[1, 2, 3] positional_arg %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({"positional_arg": 4})
        assert args == [1, 2, 3, 4]
        assert kwargs == []

    def test_dict_spread_after_arg_is_ok(self):
        tag_content = "{% my_tag positional_arg ...{'key': 'value'} %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({"positional_arg": 1})
        assert args == [1]
        assert kwargs == [("key", "value")]

    def test_dict_spread_after_kwarg_is_ok(self):
        tag_content = "{% my_tag key='value' ...{'key2': 'value2'} %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({})
        assert args == []
        assert kwargs == [("key", "value"), ("key2", "value2")]

    def test_list_spread_after_arg_is_ok(self):
        tag_content = "{% my_tag positional_arg ...[1, 2, 3] %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({"positional_arg": 4})
        assert args == [4, 1, 2, 3]
        assert kwargs == []

    def test_list_spread_after_kwarg_is_error(self):
        tag_content = "{% my_tag key='value' ...[1, 2, 3] %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        with pytest.raises(SyntaxError, match="positional argument follows keyword argument"):
            tag_func({})

    def test_list_spread_after_list_spread_is_ok(self):
        tag_content = "{% my_tag ...[1, 2, 3] ...[4, 5, 6] %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({})
        assert args == [1, 2, 3, 4, 5, 6]
        assert kwargs == []

    def test_dict_spread_after_dict_spread_is_ok(self):
        tag_content = "{% my_tag ...{'key': 'value'} ...{'key2': 'value2'} %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({})
        assert args == []
        assert kwargs == [("key", "value"), ("key2", "value2")]

    def test_list_spread_after_dict_spread_is_error(self):
        tag_content = "{% my_tag ...{'key': 'value'} ...[1, 2, 3] %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        with pytest.raises(SyntaxError, match="positional argument follows keyword argument"):
            tag_func({})

    def test_dict_spread_after_list_spread_is_ok(self):
        tag_content = "{% my_tag ...[1, 2, 3] ...{'key': 'value'} %}"
        ast = parse_tag(input=tag_content)
        tag_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = tag_func({})
        assert args == [1, 2, 3]
        assert kwargs == [("key", "value")]


class TestFlags:
    def test_flag(self):
        tag_content = "{% my_tag 123 my_flag key='val' %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"my_flag"}), sections=None))
        ast = cast("GenericTag", parse_tag(tag_content, config))

        assert ast.attrs[1].value.token.content == "my_flag"
        assert ast.attrs[1].is_flag

        # The compiled function should omit the flag
        compiled_func = _simple_compile_tag(ast, tag_content)
        args, kwargs = compiled_func({})

        assert args == [123]
        assert kwargs == [("key", "val")]

        # Same as before, but with flags=None
        ast2 = cast("GenericTag", parse_tag(tag_content, config=None))
        assert ast2.attrs[1].value.token.content == "my_flag"
        assert not ast2.attrs[1].is_flag

        # The compiled function should omit the flag
        compiled_func2 = _simple_compile_tag(ast2, tag_content)
        args2, kwargs2 = compiled_func2({"my_flag": "x"})

        assert args2 == [123, "x"]
        assert kwargs2 == [("key", "val")]

    # Since flags are NOT treated as args, this should be OK
    def test_flag_after_kwarg(self):
        tag_content = "{% my_tag key='value' my_flag %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"my_flag"}), sections=None))
        ast1 = cast("GenericTag", parse_tag(tag_content, config))

        assert ast1.attrs[1].value.token.content == "my_flag"
        assert ast1.attrs[1].is_flag

        compiled_func1 = _simple_compile_tag(ast1, tag_content)
        args1, kwargs1 = compiled_func1({})
        assert args1 == []
        assert kwargs1 == [("key", "value")]

        # Same as before, but with flags=None
        ast2 = cast("GenericTag", parse_tag(tag_content, config=None))
        assert ast2.attrs[1].value.token.content == "my_flag"
        assert not ast2.attrs[1].is_flag

        with pytest.raises(SyntaxError, match="positional argument follows keyword argument"):
            _simple_compile_tag(ast2, tag_content)

    # my_flag is NOT treated as flag because it's used as spread
    def test_flag_as_spread(self):
        tag_content = "{% my_tag ...my_flag %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"my_flag"}), sections=None))
        ast1 = cast("GenericTag", parse_tag(tag_content, config))

        assert ast1.attrs[0].value.token.content == "...my_flag"
        assert not ast1.attrs[0].is_flag

        compiled_func1 = _simple_compile_tag(ast1, tag_content)
        args1, kwargs1 = compiled_func1({"my_flag": ["arg1", "arg2"]})

        assert args1 == ["arg1", "arg2"]
        assert kwargs1 == []

        # Same as before, but with flags=None
        ast2 = cast("GenericTag", parse_tag(tag_content, config=None))
        assert ast2.attrs[0].value.token.content == "...my_flag"
        assert not ast2.attrs[0].is_flag

        compiled_func2 = _simple_compile_tag(ast2, tag_content)
        args2, kwargs2 = compiled_func2({"my_flag": ["arg1", "arg2"]})

        assert args2 == ["arg1", "arg2"]
        assert kwargs2 == []

    # my_flag is NOT treated as flag because it's used as kwarg
    def test_flag_as_kwarg(self):
        tag_content = "{% my_tag my_flag=123 %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"my_flag"}), sections=None))
        ast1 = cast("GenericTag", parse_tag(tag_content, config))

        assert ast1.attrs[0].key
        assert ast1.attrs[0].key.content == "my_flag"
        assert not ast1.attrs[0].is_flag

        compiled_func1 = _simple_compile_tag(ast1, tag_content)
        args1, kwargs1 = compiled_func1({})
        assert args1 == []
        assert kwargs1 == [("my_flag", 123)]

        # Same as before, but with no flags
        ast2 = cast("GenericTag", parse_tag(tag_content, config=None))
        assert ast2.attrs[0].key
        assert ast2.attrs[0].key.content == "my_flag"
        assert not ast2.attrs[0].is_flag

        compiled_func2 = _simple_compile_tag(ast2, tag_content)
        args2, kwargs2 = compiled_func2({})
        assert args2 == []
        assert kwargs2 == [("my_flag", 123)]

    def test_flag_duplicate(self):
        tag_content = "{% my_tag my_flag my_flag %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"my_flag"}), sections=None))
        with pytest.raises(SyntaxError, match=r"Flag 'my_flag' may be specified only once."):
            parse_tag(tag_content, config)

    def test_flag_case_sensitive(self):
        tag_content = "{% my_tag my_flag %}"
        config = ParserConfig(version=TemplateVersion.v1)
        config.set_tag(TagConfig(tag=TagSpec("my_tag", flags={"MY_FLAG"}), sections=None))
        ast = cast("GenericTag", parse_tag(tag_content, config))
        assert ast.attrs[0].value.token.content == "my_flag"
        assert not ast.attrs[0].is_flag


class TestSelfClosing:
    def test_self_closing_simple(self):
        ast = cast("GenericTag", parse_tag("{% my_tag / %}"))
        assert ast.meta.name.content == "my_tag"
        assert ast.is_self_closing is True
        assert ast.attrs == []

    def test_self_closing_with_args(self):
        ast = cast("GenericTag", parse_tag("{% my_tag key=val / %}"))
        assert ast.meta.name.content == "my_tag"
        assert ast.is_self_closing is True
        assert len(ast.attrs) == 1
        assert ast.attrs[0].key
        assert ast.attrs[0].key.content == "key"
        assert ast.attrs[0].value.token.content == "val"

    def test_self_closing_in_middle_errors(self):
        with pytest.raises(
            SyntaxError,
            match=r"Parse error:  --> 1:13\n  |\n1 | {% my_tag / key=val %}\n  |             ^---\n  |\n  = expected COMMENT",
        ):
            parse_tag("{% my_tag / key=val %}")
