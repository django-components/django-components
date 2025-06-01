import inspect
import os
import re
from typing import cast

import pytest
from django.template import Context, Template
from django.template.base import TextNode, VariableNode
from django.template.defaulttags import IfNode, LoremNode
from django.template.exceptions import TemplateSyntaxError

from django_components import Component, types
from django_components.node import BaseNode, template_tag
from django_components.templatetags import component_tags
from django_components.util.tag_parser import TagAttr

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestNode:
    def test_node_class_requires_tag(self):
        with pytest.raises(ValueError):

            class CaptureNode(BaseNode):
                pass

    # Test that the template tag can be used within the template under the registered tag
    def test_node_class_tags(self):
        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"

            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Works with end tag and self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert rendered.strip() == "Hello, John!\n            Shorthand: Hello, Mary!"

        # But raises if missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        with pytest.raises(TemplateSyntaxError, match=re.escape("Unclosed tag on line 3: 'mytag'")):
            Template(template_str2)

        TestNode.unregister(component_tags.register)

    def test_node_class_no_end_tag(self):
        class TestNode(BaseNode):
            tag = "mytag"

            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Raises with end tag or self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        with pytest.raises(TemplateSyntaxError, match=re.escape("Invalid block tag on line 4: 'endmytag'")):
            Template(template_str)

        # Works when missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        assert rendered2.strip() == "Hello, John!"

        TestNode.unregister(component_tags.register)

    def test_node_class_flags(self):
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, **kwargs) -> str:
                nonlocal captured
                captured = self.allowed_flags, self.flags, self.active_flags

                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag 'John' required / %}
        """
        template = Template(template_str)
        template.render(Context({}))

        allowed_flags, flags, active_flags = captured  # type: ignore
        assert allowed_flags == ["required", "default"]
        assert flags == {"required": True, "default": False}
        assert active_flags == ["required"]

        TestNode.unregister(component_tags.register)

    def test_node_render(self):
        # Check that the render function is called with the context
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"

            def render(self, context: Context) -> str:
                nonlocal captured
                captured = context.flatten()

                return f"Hello, {context['name']}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John"}))

        assert captured == {"False": False, "None": None, "True": True, "name": "John"}
        assert rendered.strip() == "Hello, John!"

        TestNode.unregister(component_tags.register)

    def test_node_render_raises_if_no_context_arg(self):
        with pytest.raises(
            TypeError,
            match=re.escape("`render()` method of TestNode must have at least two parameters"),
        ):

            class TestNode(BaseNode):
                tag = "mytag"

                def render(self) -> str:  # type: ignore
                    return ""

    def test_node_render_accepted_params_set_by_render_signature(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, count: int = 1, *, msg: str, mode: str = "default") -> str:
                nonlocal captured
                captured = name, count, msg, mode
                return ""

        TestNode1.register(component_tags.register)

        # Set only required params
        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' required %}
        """
        )
        template1.render(Context({}))
        assert captured == ("John", 1, "Hello", "default")

        # Set all params
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag 'John2' count=2 msg='Hello' mode='custom' required %}
        """
        )
        template2.render(Context({}))
        assert captured == ("John2", 2, "Hello", "custom")

        # Set no params
        template3 = Template(
            """
            {% load component_tags %}
            {% mytag %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template3.render(Context({}))

        # Omit required arg
        template4 = Template(
            """
            {% load component_tags %}
            {% mytag msg='Hello' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template4.render(Context({}))

        # Omit required kwarg
        template5 = Template(
            """
            {% load component_tags %}
            {% mytag name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'msg'"),
        ):
            template5.render(Context({}))

        # Extra args
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag 123 count=1 name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got multiple values for argument 'name'"),
        ):
            template6.render(Context({}))

        # Extra args after kwargs
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag count=1 name='John' 123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template6.render(Context({}))

        # Extra kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' var=123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'var'"),
        ):
            template7.render(Context({}))

        # Extra kwargs - non-identifier or kwargs
        template8 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' data-id=123 class="pa-4" @click.once="myVar" %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'data-id'"),
        ):
            template8.render(Context({}))

        # Extra arg after special kwargs
        template9 = Template(
            """
            {% load component_tags %}
            {% mytag data-id=123 'John' msg='Hello' %}
        """
        )
        with pytest.raises(
            SyntaxError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template9.render(Context({}))

        TestNode1.unregister(component_tags.register)

    def test_node_render_extra_args_and_kwargs(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            def render(self, context: Context, name: str, *args, msg: str, **kwargs) -> str:
                nonlocal captured
                captured = name, args, msg, kwargs
                return ""

        TestNode1.register(component_tags.register)

        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John'
                123 456 789 msg='Hello' a=1 b=2 c=3 required
                data-id=123 class="pa-4" @click.once="myVar"
            %}
        """
        )
        template1.render(Context({}))
        assert captured == (
            "John",
            (123, 456, 789),
            "Hello",
            {"a": 1, "b": 2, "c": 3, "data-id": 123, "class": "pa-4", "@click.once": "myVar"},
        )

        TestNode1.unregister(component_tags.register)

    def test_node_render_kwargs_only(self):
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"

            def render(self, context: Context, **kwargs) -> str:
                nonlocal captured
                captured = kwargs
                return ""

        TestNode.register(component_tags.register)

        # Test with various kwargs including non-identifier keys
        template = Template(
            """
            {% load component_tags %}
            {% mytag
                name='John'
                age=25
                data-id=123
                class="header"
                @click="handleClick"
                v-if="isVisible"
            %}
            """
        )
        template.render(Context({}))

        # All kwargs should be accepted since the function accepts **kwargs
        assert captured == {
            "name": "John",
            "age": 25,
            "data-id": 123,
            "class": "header",
            "@click": "handleClick",
            "v-if": "isVisible",
        }

        # Test with positional args (should fail since function only accepts kwargs)
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag "John" name="Mary" %}
            """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': takes 0 positional arguments but 1 was given"),
        ):
            template2.render(Context({}))

        TestNode.unregister(component_tags.register)


@djc_test
class TestDecorator:
    def test_decorator_requires_tag(self):
        with pytest.raises(
            TypeError,
            match=re.escape("template_tag() missing 1 required positional argument: 'tag'"),
        ):

            @template_tag(component_tags.register)  # type: ignore
            def mytag(node: BaseNode, context: Context) -> str:
                return ""

    # Test that the template tag can be used within the template under the registered tag
    def test_decorator_tags(self):
        @template_tag(component_tags.register, tag="mytag", end_tag="endmytag")
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return f"Hello, {name}!"

        # Works with end tag and self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert rendered.strip() == "Hello, John!\n            Shorthand: Hello, Mary!"

        # But raises if missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Unclosed tag on line 3: 'mytag'"),
        ):
            Template(template_str2)

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_no_end_tag(self):
        @template_tag(component_tags.register, tag="mytag")  # type: ignore
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return f"Hello, {name}!"

        # Raises with end tag or self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Invalid block tag on line 4: 'endmytag'"),
        ):
            Template(template_str)

        # Works when missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        assert rendered2.strip() == "Hello, John!"

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_flags(self):
        @template_tag(component_tags.register, tag="mytag", end_tag="endmytag", allowed_flags=["required", "default"])
        def render(node: BaseNode, context: Context, name: str, **kwargs) -> str:
            return ""

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render(self):
        # Check that the render function is called with the context
        captured = None

        @template_tag(component_tags.register, tag="mytag")  # type: ignore
        def render(node: BaseNode, context: Context) -> str:
            nonlocal captured
            captured = context.flatten()
            return f"Hello, {context['name']}!"

        template_str = """
            {% load component_tags %}
            {% mytag / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John"}))

        assert captured == {"False": False, "None": None, "True": True, "name": "John"}
        assert rendered.strip() == "Hello, John!"

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render_raises_if_no_context_arg(self):
        with pytest.raises(
            TypeError,
            match=re.escape("Failed to create node class in 'template_tag()' for 'render'"),
        ):

            @template_tag(component_tags.register, tag="mytag")  # type: ignore
            def render(node: BaseNode) -> str:  # type: ignore
                return ""

    def test_decorator_render_accepted_params_set_by_render_signature(self):
        captured = None

        @template_tag(component_tags.register, tag="mytag", allowed_flags=["required", "default"])  # type: ignore
        def render(
            node: BaseNode, context: Context, name: str, count: int = 1, *, msg: str, mode: str = "default"
        ) -> str:
            nonlocal captured
            captured = name, count, msg, mode
            return ""

        # Set only required params
        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' required %}
        """
        )
        template1.render(Context({}))
        assert captured == ("John", 1, "Hello", "default")

        # Set all params
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag 'John2' count=2 msg='Hello' mode='custom' required %}
        """
        )
        template2.render(Context({}))
        assert captured == ("John2", 2, "Hello", "custom")

        # Set no params
        template3 = Template(
            """
            {% load component_tags %}
            {% mytag %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template3.render(Context({}))

        # Omit required arg
        template4 = Template(
            """
            {% load component_tags %}
            {% mytag msg='Hello' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template4.render(Context({}))

        # Omit required kwarg
        template5 = Template(
            """
            {% load component_tags %}
            {% mytag name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'msg'"),
        ):
            template5.render(Context({}))

        # Extra args
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag 123 count=1 name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got multiple values for argument 'name'"),
        ):
            template6.render(Context({}))

        # Extra args after kwargs
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag count=1 name='John' 123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template6.render(Context({}))

        # Extra kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' var=123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'var'"),
        ):
            template7.render(Context({}))

        # Extra kwargs - non-identifier or kwargs
        template8 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' data-id=123 class="pa-4" @click.once="myVar" %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'data-id'"),
        ):
            template8.render(Context({}))

        # Extra arg after special kwargs
        template9 = Template(
            """
            {% load component_tags %}
            {% mytag data-id=123 'John' msg='Hello' %}
        """
        )
        with pytest.raises(
            SyntaxError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template9.render(Context({}))

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render_extra_args_and_kwargs(self):
        captured = None

        @template_tag(component_tags.register, tag="mytag", allowed_flags=["required", "default"])  # type: ignore
        def render(node: BaseNode, context: Context, name: str, *args, msg: str, **kwargs) -> str:
            nonlocal captured
            captured = name, args, msg, kwargs
            return ""

        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John'
                123 456 789 msg='Hello' a=1 b=2 c=3 required
                data-id=123 class="pa-4" @click.once="myVar"
            %}
        """
        )
        template1.render(Context({}))
        assert captured == (
            "John",
            (123, 456, 789),
            "Hello",
            {"a": 1, "b": 2, "c": 3, "data-id": 123, "class": "pa-4", "@click.once": "myVar"},
        )

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]

    def test_decorator_render_kwargs_only(self):
        captured = None

        @template_tag(component_tags.register, tag="mytag")  # type: ignore
        def render(node: BaseNode, context: Context, **kwargs) -> str:
            nonlocal captured
            captured = kwargs
            return ""

        # Test with various kwargs including non-identifier keys
        template = Template(
            """
            {% load component_tags %}
            {% mytag
                name='John'
                age=25
                data-id=123
                class="header"
                @click="handleClick"
                v-if="isVisible"
            %}
            """
        )
        template.render(Context({}))

        # All kwargs should be accepted since the function accepts **kwargs
        assert captured == {
            "name": "John",
            "age": 25,
            "data-id": 123,
            "class": "header",
            "@click": "handleClick",
            "v-if": "isVisible",
        }

        # Test with positional args (should fail since function only accepts kwargs)
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag "John" name="Mary" %}
            """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': takes 0 positional arguments but 1 was given"),
        ):
            template2.render(Context({}))

        render._node.unregister(component_tags.register)  # type: ignore[attr-defined]


def force_signature_validation(fn):
    """
    Creates a proxy around a function that makes __code__ inaccessible,
    forcing the use of signature-based validation.
    """

    class SignatureOnlyFunction:
        def __init__(self, fn):
            self.__wrapped__ = fn
            self.__signature__ = inspect.signature(fn)

        def __call__(self, *args, **kwargs):
            return self.__wrapped__(*args, **kwargs)

        def __getattr__(self, name):
            # Return None for __code__ to force signature-based validation
            if name == "__code__":
                return None
            # For all other attributes, delegate to the wrapped function
            return getattr(self.__wrapped__, name)

    return SignatureOnlyFunction(fn)


@djc_test
class TestSignatureBasedValidation:
    # Test that the template tag can be used within the template under the registered tag
    def test_node_class_tags(self):
        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"

            @force_signature_validation
            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Works with end tag and self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert rendered.strip() == "Hello, John!\n            Shorthand: Hello, Mary!"

        # But raises if missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Unclosed tag on line 3: 'mytag'"),
        ):
            Template(template_str2)

        TestNode.unregister(component_tags.register)

    def test_node_class_no_end_tag(self):
        class TestNode(BaseNode):
            tag = "mytag"

            @force_signature_validation
            def render(self, context: Context, name: str, **kwargs) -> str:
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        # Raises with end tag or self-closing
        template_str: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
            {% endmytag %}
            Shorthand: {% mytag 'Mary' / %}
        """
        with pytest.raises(
            TemplateSyntaxError,
            match=re.escape("Invalid block tag on line 4: 'endmytag'"),
        ):
            Template(template_str)

        # Works when missing end tag
        template_str2: types.django_html = """
            {% load component_tags %}
            {% mytag 'John' %}
        """
        template2 = Template(template_str2)
        rendered2 = template2.render(Context({}))
        assert rendered2.strip() == "Hello, John!"

        TestNode.unregister(component_tags.register)

    def test_node_class_flags(self):
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"
            allowed_flags = ["required", "default"]

            @force_signature_validation
            def render(self, context: Context, name: str, **kwargs) -> str:
                nonlocal captured
                captured = self.allowed_flags, self.flags, self.active_flags
                return f"Hello, {name}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag 'John' required / %}
        """
        template = Template(template_str)
        template.render(Context({}))

        allowed_flags, flags, active_flags = captured  # type: ignore
        assert allowed_flags == ["required", "default"]
        assert flags == {"required": True, "default": False}
        assert active_flags == ["required"]

        TestNode.unregister(component_tags.register)

    def test_node_class_attributes(self):
        captured = None

        class TestNodeWithEndTag(BaseNode):
            tag = "mytag"
            end_tag = "endmytag"

            @force_signature_validation
            def render(self, context: Context, name: str, **kwargs) -> str:
                nonlocal captured
                captured = (
                    self.params,
                    self.nodelist,
                    self.node_id,
                    self.contents,
                    self.template_name,
                    self.template_component,
                )
                return f"Hello, {name}!"

        # Case 1 - Node with end tag and NOT self-closing
        TestNodeWithEndTag.register(component_tags.register)

        template_str1 = """
            {% load component_tags %}
            {% mytag 'John' %}
              INSIDE TAG {{ my_var }} {# comment #} {% lorem 1 w %} {% if True %} henlo {% endif %}
            {% endmytag %}
        """
        template1 = Template(template_str1)
        template1.render(Context({}))

        params1, nodelist1, node_id1, contents1, template_name1, template_component1 = captured  # type: ignore
        assert len(params1) == 1
        assert isinstance(params1[0], TagAttr)
        # NOTE: The comment node is not included in the nodelist
        assert len(nodelist1) == 8
        assert isinstance(nodelist1[0], TextNode)
        assert isinstance(nodelist1[1], VariableNode)
        assert isinstance(nodelist1[2], TextNode)
        assert isinstance(nodelist1[3], TextNode)
        assert isinstance(nodelist1[4], LoremNode)
        assert isinstance(nodelist1[5], TextNode)
        assert isinstance(nodelist1[6], IfNode)
        assert isinstance(nodelist1[7], TextNode)
        assert contents1 == "\n              INSIDE TAG {{ my_var }} {# comment #} {% lorem 1 w %} {% if True %} henlo {% endif %}\n            "  # noqa: E501
        assert node_id1 == "a1bc3e"
        assert template_name1 == '<unknown source>'
        assert template_component1 is None

        captured = None  # Reset captured

        # Case 2 - Node with end tag and NOT self-closing
        template_str2 = """
            {% load component_tags %}
            {% mytag 'John' / %}
        """
        template2 = Template(template_str2)
        template2.render(Context({}))

        params2, nodelist2, node_id2, contents2, template_name2, template_component2 = captured  # type: ignore
        assert len(params2) == 1  # type: ignore
        assert isinstance(params2[0], TagAttr)  # type: ignore
        assert len(nodelist2) == 0  # type: ignore
        assert contents2 is None  # type: ignore
        assert node_id2 == "a1bc3f"  # type: ignore
        assert template_name2 == '<unknown source>'  # type: ignore
        assert template_component2 is None  # type: ignore

        captured = None  # Reset captured

        # Case 3 - Node without end tag
        class TestNodeWithoutEndTag(BaseNode):
            tag = "mytag2"

            @force_signature_validation
            def render(self, context: Context, name: str, **kwargs) -> str:
                nonlocal captured
                captured = self.params, self.nodelist, self.node_id, self.contents, self.template_name, self.template_component  # noqa: E501
                return f"Hello, {name}!"

        TestNodeWithoutEndTag.register(component_tags.register)

        template_str3 = """
            {% load component_tags %}
            {% mytag2 'John' %}
        """
        template3 = Template(template_str3)
        template3.render(Context({}))

        params3, nodelist3, node_id3, contents3, template_name3, template_component3 = captured  # type: ignore
        assert len(params3) == 1  # type: ignore
        assert isinstance(params3[0], TagAttr)  # type: ignore
        assert len(nodelist3) == 0  # type: ignore
        assert contents3 is None  # type: ignore
        assert node_id3 == "a1bc40"  # type: ignore
        assert template_name3 == '<unknown source>'  # type: ignore
        assert template_component3 is None  # type: ignore

        # Case 4 - Node nested in Component end tag
        class TestComponent(Component):
            template = """
                {% load component_tags %}
                {% mytag2 'John' %}
            """

        TestComponent.render(Context({}))

        params4, nodelist4, node_id4, contents4, template_name4, template_component4 = captured  # type: ignore
        assert len(params4) == 1  # type: ignore
        assert isinstance(params4[0], TagAttr)  # type: ignore
        assert len(nodelist4) == 0  # type: ignore
        assert contents4 is None  # type: ignore
        assert node_id4 == "a1bc42"  # type: ignore

        if os.name == 'nt':
            assert cast(str, template_name4).endswith("\\tests\\test_node.py::TestComponent")  # type: ignore
        else:
            assert cast(str, template_name4).endswith("/tests/test_node.py::TestComponent")  # type: ignore

        assert template_name4 == f"{__file__}::TestComponent"  # type: ignore
        assert template_component4 is TestComponent  # type: ignore

        # Cleanup
        TestNodeWithEndTag.unregister(component_tags.register)
        TestNodeWithoutEndTag.unregister(component_tags.register)

    def test_node_render(self):
        # Check that the render function is called with the context
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"

            @force_signature_validation
            def render(self, context: Context) -> str:
                nonlocal captured
                captured = context.flatten()
                return f"Hello, {context['name']}!"

        TestNode.register(component_tags.register)

        template_str = """
            {% load component_tags %}
            {% mytag / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({"name": "John"}))

        assert captured == {"False": False, "None": None, "True": True, "name": "John"}
        assert rendered.strip() == "Hello, John!"

        TestNode.unregister(component_tags.register)

    def test_node_render_raises_if_no_context_arg(self):
        with pytest.raises(
            TypeError,
            match=re.escape("`render()` method of TestNode must have at least two parameters"),
        ):

            class TestNode(BaseNode):
                tag = "mytag"

                def render(self) -> str:  # type: ignore
                    return ""

    def test_node_render_accepted_params_set_by_render_signature(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            @force_signature_validation
            def render(self, context: Context, name: str, count: int = 1, *, msg: str, mode: str = "default") -> str:
                nonlocal captured
                captured = name, count, msg, mode
                return ""

        TestNode1.register(component_tags.register)

        # Set only required params
        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' required %}
        """
        )
        template1.render(Context({}))
        assert captured == ("John", 1, "Hello", "default")

        # Set all params
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag 'John2' count=2 msg='Hello' mode='custom' required %}
        """
        )
        template2.render(Context({}))
        assert captured == ("John2", 2, "Hello", "custom")

        # Set no params
        template3 = Template(
            """
            {% load component_tags %}
            {% mytag %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template3.render(Context({}))

        # Omit required arg
        template4 = Template(
            """
            {% load component_tags %}
            {% mytag msg='Hello' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'name'"),
        ):
            template4.render(Context({}))

        # Omit required kwarg
        template5 = Template(
            """
            {% load component_tags %}
            {% mytag name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': missing a required argument: 'msg'"),
        ):
            template5.render(Context({}))

        # Extra args
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag 123 count=1 name='John' %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got multiple values for argument 'name'"),
        ):
            template6.render(Context({}))

        # Extra args after kwargs
        template6 = Template(
            """
            {% load component_tags %}
            {% mytag count=1 name='John' 123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template6.render(Context({}))

        # Extra kwargs
        template7 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' var=123 %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'var'"),
        ):
            template7.render(Context({}))

        # Extra kwargs - non-identifier or kwargs
        template8 = Template(
            """
            {% load component_tags %}
            {% mytag 'John' msg='Hello' mode='custom' data-id=123 class="pa-4" @click.once="myVar" %}
        """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': got an unexpected keyword argument 'data-id'"),
        ):
            template8.render(Context({}))

        # Extra arg after special kwargs
        template9 = Template(
            """
            {% load component_tags %}
            {% mytag data-id=123 'John' msg='Hello' %}
        """
        )
        with pytest.raises(
            SyntaxError,
            match=re.escape("positional argument follows keyword argument"),
        ):
            template9.render(Context({}))

        TestNode1.unregister(component_tags.register)

    def test_node_render_extra_args_and_kwargs(self):
        captured = None

        class TestNode1(BaseNode):
            tag = "mytag"
            allowed_flags = ["required", "default"]

            @force_signature_validation
            def render(self, context: Context, name: str, *args, msg: str, **kwargs) -> str:
                nonlocal captured
                captured = name, args, msg, kwargs
                return ""

        TestNode1.register(component_tags.register)

        template1 = Template(
            """
            {% load component_tags %}
            {% mytag 'John'
                123 456 789 msg='Hello' a=1 b=2 c=3 required
                data-id=123 class="pa-4" @click.once="myVar"
            %}
        """
        )
        template1.render(Context({}))
        assert captured == (
            "John",
            (123, 456, 789),
            "Hello",
            {"a": 1, "b": 2, "c": 3, "data-id": 123, "class": "pa-4", "@click.once": "myVar"},
        )

        TestNode1.unregister(component_tags.register)

    def test_node_render_kwargs_only(self):
        captured = None

        class TestNode(BaseNode):
            tag = "mytag"

            @force_signature_validation
            def render(self, context: Context, **kwargs) -> str:
                nonlocal captured
                captured = kwargs
                return ""

        TestNode.register(component_tags.register)

        # Test with various kwargs including non-identifier keys
        template = Template(
            """
            {% load component_tags %}
            {% mytag
                name='John'
                age=25
                data-id=123
                class="header"
                @click="handleClick"
                v-if="isVisible"
            %}
            """
        )
        template.render(Context({}))

        # All kwargs should be accepted since the function accepts **kwargs
        assert captured == {
            "name": "John",
            "age": 25,
            "data-id": 123,
            "class": "header",
            "@click": "handleClick",
            "v-if": "isVisible",
        }

        # Test with positional args (should fail since function only accepts kwargs)
        template2 = Template(
            """
            {% load component_tags %}
            {% mytag "John" name="Mary" %}
            """
        )
        with pytest.raises(
            TypeError,
            match=re.escape("Invalid parameters for tag 'mytag': takes 0 positional arguments but 1 was given"),
        ):
            template2.render(Context({}))

        TestNode.unregister(component_tags.register)
