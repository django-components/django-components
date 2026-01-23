from typing import Any

from django import VERSION as DJANGO_VERSION
from django.template import Context, NodeList, Template
from django.template.base import Node, Origin, Parser
from django.template.library import InclusionNode
from django.template.loader_tags import IncludeNode

from django_components.context import _COMPONENT_CONTEXT_KEY, _STRATEGY_CONTEXT_KEY, COMPONENT_IS_NESTED_KEY
from django_components.dependencies import COMPONENT_COMMENT_REGEX, render_dependencies
from django_components.extension import OnTemplateCompiledContext, OnTemplateLoadedContext, extensions
from django_components.util.template_parser import parse_template


# In some cases we can't work around Django's design, and need to patch the template class.
def monkeypatch_template_cls(template_cls: type[Template]) -> None:
    if is_cls_patched(template_cls):
        return

    monkeypatch_template_init(template_cls)
    monkeypatch_template_compile_nodelist(template_cls)
    monkeypatch_template_render(template_cls)
    template_cls._djc_patched = True


# Patch `Template.__init__` to apply `on_template_loaded()` and `on_template_compiled()`
# extension hooks if the template belongs to a Component.
def monkeypatch_template_init(template_cls: type[Template]) -> None:
    original_init = template_cls.__init__

    # NOTE: Function signature of Template.__init__ hasn't changed in 11 years, so we can safely patch it.
    #       See https://github.com/django/django/blame/main/django/template/base.py#L139
    def __init__(  # noqa: N807
        self: Template,
        template_string: Any,
        origin: Origin | None = None,
        name: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # NOTE: Avoids circular import
        from django_components.template import (  # noqa: PLC0415
            get_component_by_template_file,
            get_component_from_origin,
            set_component_to_origin,
        )

        # If this Template instance was created by us when loading a template file for a component
        # with `load_component_template()`, then we do 2 things:
        #
        # 1. Associate the Component class with the template by setting it on the `Origin` instance
        #    (`template.origin.component_cls`). This way the `{% component%}` and `{% slot %}` tags
        #    will know inside which Component class they were defined.
        #
        # 2. Apply `extensions.on_template_preprocess()` to the template, so extensions can modify
        #    the template string before it's compiled into a nodelist.
        if get_component_from_origin(origin) is not None:
            component_cls = get_component_from_origin(origin)
        elif origin is not None and origin.template_name is not None:
            component_cls = get_component_by_template_file(origin.template_name)
            if component_cls is not None:
                set_component_to_origin(origin, component_cls)
        else:
            component_cls = None

        if component_cls is not None:
            template_string = str(template_string)
            template_string = extensions.on_template_loaded(
                OnTemplateLoadedContext(
                    component_cls=component_cls,
                    content=template_string,
                    origin=origin,
                    name=name,
                ),
            )

        # Calling original `Template.__init__` should also compile the template into a Nodelist
        # via `Template.compile_nodelist()`.
        original_init(self, template_string, origin, name, *args, **kwargs)  # type: ignore[misc]

        if component_cls is not None:
            extensions.on_template_compiled(
                OnTemplateCompiledContext(
                    component_cls=component_cls,
                    template=self,
                ),
            )

    template_cls.__init__ = __init__


# Patch `Template.compile_nodelist` to use our custom parser. Our parser makes it possible
# to use template tags as inputs to the component tag:
#
# {% component "my-component" description="{% lorem 3 w %}" / %}
def monkeypatch_template_compile_nodelist(template_cls: type[Template]) -> None:
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
            nodelist = parser.parse()
            if DJANGO_VERSION >= (5, 1):
                #  ---------------- ADDED IN Django v5.1 - See https://github.com/django/django/commit/35bbb2c9c01882b1d77b0b8c737ac646144833d4  # noqa: E501
                # NOTE: This must be enabled ONLY for 5.1 and later. Previously it was also for older
                #       Django versions, and this led to compatibility issue with django-template-partials.
                #       See https://github.com/carltongibson/django-template-partials/pull/85#issuecomment-3187354790
                self.extra_data = getattr(parser, "extra_data", {})
                #  ---------------- END OF ADDED IN Django v5.1 ----------------
            return nodelist
        except Exception as e:
            if self.engine.debug:
                e.template_debug = self.get_exception_info(e, e.token)  # type: ignore[attr-defined]
            raise

    template_cls.compile_nodelist = _compile_nodelist


def monkeypatch_template_render(template_cls: type[Template]) -> None:
    # Modify `Template.render` to set `isolated_context` kwarg of `push_state`
    # based on our custom `_DJC_COMPONENT_IS_NESTED`.
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
    # NOTE 2: Instead of setting `_DJC_COMPONENT_IS_NESTED` context key, alternatively we could
    # have passed the value to `monkeypatch_template_render` directly. However, we intentionally
    # did NOT do that, so the monkey-patched method is more robust, and can be e.g. copied
    # to other.
    if is_cls_patched(template_cls):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    # NOTE: This implementation is based on Django v5.1.3)
    def _template_render(self: Template, context: Context, *args: Any, **kwargs: Any) -> str:
        """Display stage -- can be called many times"""
        # We parametrized `isolated_context`, which was `True` in the original method.
        if COMPONENT_IS_NESTED_KEY not in context:
            isolated_context = True
        else:
            # MUST be `True` for templates that are NOT import with `{% extends %}` tag,
            # and `False` otherwise.
            isolated_context = not context[COMPONENT_IS_NESTED_KEY]

        # This is original implementation, except we override `isolated_context`,
        # and we post-process the result with `render_dependencies()`.
        with context.render_context.push_state(self, isolated_context=isolated_context):
            if context.template is None:
                with context.bind_template(self):
                    context.template_name = self.name
                    result: str = self._render(context, *args, **kwargs)
            else:
                result = self._render(context, *args, **kwargs)

        # If the key is present, that means this Template is rendered as part of `Component.render()`
        # or `{% component %}`. In that case the parent component will take care of rendering the
        # dependencies, so we don't need to do that here.
        if _COMPONENT_CONTEXT_KEY in context:
            return result

        # NOTE: Only process dependencies if the rendered result contains AT LEAST ONE rendered component.
        #       This has two reasons:
        #       1. To keep the behavior consistent with the previous implementation, when `Template.render()`
        #          didn't call `render_dependencies()`.
        #       2. To avoid unnecessary processing which otherwise has a considerable perf overhead.
        #          See https://github.com/django-components/django-components/pull/1166#issuecomment-2850899765
        if not COMPONENT_COMMENT_REGEX.search(result.encode("utf-8")):
            return result

        # Don't post-process if this template was rendered with Django's InclusionNode.
        # Fix for https://github.com/django-components/django-components/issues/1390
        # NOTE: Lenght of 2 means a Context with single layer (+ layer with defaults)
        if "_DJC_INSIDE_INCLUSION_TAG" in context and len(context.dicts) == 2:
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


def monkeypatch_include_node(include_node_cls: type[Node]) -> None:
    if is_cls_patched(include_node_cls):
        return

    monkeypatch_include_render(include_node_cls)
    include_node_cls._djc_patched = True


def monkeypatch_include_render(include_node_cls: type[Node]) -> None:
    # Modify `IncludeNode.render()` (what renders `{% include %}` tag) so that the included
    # template does NOT render the JS/CSS by itself.
    #
    # Instead, we want the parent template
    # (which contains the `{% component %}` tag) to decide whether to render the JS/CSS.
    #
    # We achieve this by setting `DJC_DEPS_STRATEGY` to `ignore` in the context.
    #
    # Fix for https://github.com/django-components/django-components/issues/1296
    if is_cls_patched(include_node_cls):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    orig_include_render = include_node_cls.render

    # NOTE: This implementation is based on Django v5.1.3)
    def _include_render(self: IncludeNode, context: Context, *args: Any, **kwargs: Any) -> str:
        # NOTE: `_STRATEGY_CONTEXT_KEY` is used so that we defer the rendering of components' JS/CSS
        #       to until the parent template that used the `{% include %}` tag is rendered.
        # NOTE: `{ COMPONENT_IS_NESTED_KEY: False }` is used so that a new RenderContext layer is created,
        #       so that inside each `{% include %}` the template can use the `{% extends %}` tag.
        #       Otherwise, the state leaks, and if both `{% include %}` templates use the `{% extends %}` tag,
        #       the second one raises, because it would be like using two `{% extends %}` tags in the same template.
        #       See https://github.com/django-components/django-components/issues/1389
        with context.update({_STRATEGY_CONTEXT_KEY: "ignore", COMPONENT_IS_NESTED_KEY: False}):
            return orig_include_render(self, context, *args, **kwargs)

    include_node_cls.render = _include_render


def monkeypatch_inclusion_node(inclusion_node_cls: type[Node]) -> None:
    if is_cls_patched(inclusion_node_cls):
        return

    monkeypatch_inclusion_init(inclusion_node_cls)
    monkeypatch_inclusion_render(inclusion_node_cls)
    inclusion_node_cls._djc_patched = True


# Patch `InclusionNode.__init__` so that `InclusionNode.func` returns also `{"_DJC_INSIDE_INCLUSION_TAG": True}`.
# This is then used in `Template.render()` so that we can detect if template was rendered inside an inclusion tag.
# See https://github.com/django-components/django-components/issues/1390
def monkeypatch_inclusion_init(inclusion_node_cls: type[Node]) -> None:
    original_init = inclusion_node_cls.__init__

    # NOTE: Function signature of InclusionNode.__init__ hasn't changed in 9 years, so we can safely patch it.
    #       See https://github.com/django/django/blame/main/django/template/library.py#L348
    def __init__(  # noqa: N807
        self: InclusionNode,
        func: Any,
        takes_context: bool,
        args: Any,
        kwargs: Any,
        filename: Any,
        *future_args: Any,
        **future_kwargs: Any,
    ) -> None:
        original_init(self, func, takes_context, args, kwargs, filename, *future_args, **future_kwargs)  # type: ignore[misc]

        orig_func = self.func

        def new_func(*args: Any, **kwargs: Any) -> Any:
            result = orig_func(*args, **kwargs)
            result["_DJC_INSIDE_INCLUSION_TAG"] = True
            return result

        self.func = new_func

    inclusion_node_cls.__init__ = __init__


def monkeypatch_inclusion_render(inclusion_node_cls: type[Node]) -> None:
    # Modify `InclusionNode.render()`  so that the included
    # template does NOT render the JS/CSS by itself.
    #
    # Instead, we want the parent template to decide whether to render the JS/CSS.
    #
    # We achieve this by setting `_DJC_INSIDE_INCLUSION_TAG`.
    #
    # Fix for https://github.com/django-components/django-components/issues/1390
    if is_cls_patched(inclusion_node_cls):
        # Do not patch if done so already. This helps us avoid RecursionError
        return

    orig_inclusion_render = inclusion_node_cls.render

    # NOTE: This implementation is based on Django v5.2.5)
    def _inclusion_render(self: InclusionNode, context: Context, *args: Any, **kwargs: Any) -> str:
        with context.update({"_DJC_INSIDE_INCLUSION_TAG": True}):
            return orig_inclusion_render(self, context, *args, **kwargs)

    inclusion_node_cls.render = _inclusion_render


# NOTE: Remove once Django v5.2 reaches end of life
#       See https://github.com/django-components/django-components/issues/1323#issuecomment-3163478287
def monkeypatch_template_proxy_cls() -> None:
    # Patch TemplateProxy if template_partials is installed
    # See https://github.com/django-components/django-components/issues/1323#issuecomment-3164224042
    try:
        from template_partials.templatetags.partials import TemplateProxy  # noqa: PLC0415
    except ImportError:
        # template_partials is in INSTALLED_APPS but not actually installed
        # This is fine, just skip the patching
        return

    if is_cls_patched(TemplateProxy):
        return

    monkeypatch_template_proxy_render(TemplateProxy)
    TemplateProxy._djc_patched = True


def monkeypatch_template_proxy_render(template_proxy_cls: type[Any]) -> None:
    # NOTE: TemplateProxy.render() is same logic as Template.render(), just duplicated.
    # So we can instead reuse Template.render()
    def _template_proxy_render(self: Any, context: Context, *_args: Any, **_kwargs: Any) -> str:
        return Template.render(self, context)

    template_proxy_cls.render = _template_proxy_render

    # TemplateProxy from django-template-partials replicates Template.render().
    # However, the older versions (e.g. 24.1) didn't define `_render()` method.
    # So we define it to support the older versions of django-template-partials.
    # With this, we support django-template-partials as old as v23.3.
    if not hasattr(template_proxy_cls, "_render"):

        def _render(self: Any, context: Context, *args: Any, **kwargs: Any) -> str:
            return self.nodelist.render(context, *args, **kwargs)

        template_proxy_cls._render = _render


def is_cls_patched(cls: type[Any]) -> bool:
    return getattr(cls, "_djc_patched", False)
