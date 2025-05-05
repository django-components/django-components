from typing import Any, Type

from django.template import Context, NodeList, Template
from django.template.base import Parser

from django_components.context import _COMPONENT_CONTEXT_KEY, _STRATEGY_CONTEXT_KEY
from django_components.dependencies import render_dependencies
from django_components.util.template_parser import parse_template


# In some cases we can't work around Django's design, and need to patch the template class.
def monkeypatch_template_cls(template_cls: Type[Template]) -> None:
    monkeypatch_template_compile_nodelist(template_cls)
    monkeypatch_template_render(template_cls)
    template_cls._djc_patched = True


# Patch `Template.compile_nodelist` to use our custom parser. Our parser makes it possible
# to use template tags as inputs to the component tag:
#
# {% component "my-component" description="{% lorem 3 w %}" / %}
def monkeypatch_template_compile_nodelist(template_cls: Type[Template]) -> None:
    def _compile_nodelist(self: Template) -> NodeList:
        """
        Parse and compile the template source into a nodelist. If debug
        is True and an exception occurs during parsing, the exception is
        annotated with contextual line information where it occurred in the
        template source.
        """
        #  ---------------- ORIGINAL (Django v5.1.3) ----------------
        # if self.engine.debug:
        #     lexer = DebugLexer(self.source)
        # else:
        #     lexer = Lexer(self.source)

        # tokens = lexer.tokenize()
        #  ---------------- OUR CHANGES START ----------------
        tokens = parse_template(self.source)
        #  ---------------- OUR CHANGES END ----------------
        parser = Parser(
            tokens,
            self.engine.template_libraries,
            self.engine.template_builtins,
            self.origin,
        )

        try:
            #  ---------------- ADDED IN Django v5.1 - See https://github.com/django/django/commit/35bbb2c9c01882b1d77b0b8c737ac646144833d4  # noqa: E501
            nodelist = parser.parse()
            self.extra_data = getattr(parser, "extra_data", {})
            #  ---------------- END OF ADDED IN Django v5.1 ----------------
            return nodelist
        except Exception as e:
            if self.engine.debug:
                e.template_debug = self.get_exception_info(e, e.token)  # type: ignore
            raise

    template_cls.compile_nodelist = _compile_nodelist


def monkeypatch_template_render(template_cls: Type[Template]) -> None:
    # Modify `Template.render` to set `isolated_context` kwarg of `push_state`
    # based on our custom `Template._djc_is_component_nested`.
    #
    # Part of fix for https://github.com/django-components/django-components/issues/508
    #
    # NOTE 1: While we could've subclassed Template, then we would need to either
    # 1) ask the user to change the backend, so all templates are of our subclass, or
    # 2) copy the data from user's Template class instance to our subclass instance,
    # which could lead to doubly parsing the source, and could be problematic if users
    # used more exotic subclasses of Template.
    #
    # Instead, modifying only the `render` method of an already-existing instance
    # should work well with any user-provided custom subclasses of Template, and it
    # doesn't require the source to be parsed multiple times. User can pass extra args/kwargs,
    # and can modify the rendering behavior by overriding the `_render` method.
    #
    # NOTE 2: Instead of setting `Template._djc_is_component_nested`, alternatively we could
    # have passed the value to `monkeypatch_template_render` directly. However, we intentionally
    # did NOT do that, so the monkey-patched method is more robust, and can be e.g. copied
    # to other.
    if is_template_cls_patched(template_cls):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    def _template_render(self: Template, context: Context, *args: Any, **kwargs: Any) -> str:
        "Display stage -- can be called many times"
        #  ---------------- ORIGINAL (Django v5.1.3) ----------------
        # with context.render_context.push_state(self):
        #  ---------------- OUR CHANGES START ----------------
        # We parametrized `isolated_context`, which was `True` in the original method.
        if not hasattr(self, "_djc_is_component_nested"):
            isolated_context = True
        else:
            # MUST be `True` for templates that are NOT import with `{% extends %}` tag,
            # and `False` otherwise.
            isolated_context = not self._djc_is_component_nested

        with context.render_context.push_state(self, isolated_context=isolated_context):
            #  ---------------- OUR CHANGES END ----------------
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    result = self._render(context, *args, **kwargs)
            else:
                result = self._render(context, *args, **kwargs)

        # If the key is present, that means this Template is rendered as part of `Component.render()`
        # or `{% component %}`. In that case the parent component will take care of rendering the
        # dependencies, so we don't need to do that here.
        if _COMPONENT_CONTEXT_KEY in context:
            return result

        # Allow users to configure the `deps_strategy` kwarg of `render_dependencies()`, even if
        # they render a Template directly with `Template.render()` or Django's `django.shortcuts.render()`.
        #
        # Example:
        # ```
        # result = render_dependencies(
        #     result,
        #     Context({ "DJC_DEPS_STRATEGY": "fragment" }),
        # )
        # ```
        if _STRATEGY_CONTEXT_KEY in context and context[_STRATEGY_CONTEXT_KEY] is not None:
            strategy = context[_STRATEGY_CONTEXT_KEY]
            result = render_dependencies(result, strategy)
        else:
            result = render_dependencies(result)
        return result

    template_cls.render = _template_render


def is_template_cls_patched(template_cls: Type[Template]) -> bool:
    return getattr(template_cls, "_djc_patched", False)
