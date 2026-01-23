import abc
import re
from typing import TYPE_CHECKING, NamedTuple

from django.template import TemplateSyntaxError
from django.utils.module_loading import import_string

from django_components.util.misc import is_str_wrapped_in_quotes

if TYPE_CHECKING:
    from django_components.component_registry import ComponentRegistry


# Require the start / end tags to contain NO spaces and only these characters
TAG_CHARS = r"\w\-\:\@\.\#/"
TAG_RE = re.compile(rf"^[{TAG_CHARS}]+$")


class TagResult(NamedTuple):
    """
    The return value from [`TagFormatter.parse()`](../api#django_components.TagFormatterABC.parse).

    Read more about [Tag formatter](../../concepts/advanced/tag_formatter).
    """

    component_name: str
    """
    Component name extracted from the template tag

    For example, if we had tag

    ```django
    {% component "my_comp" key=val key2=val2 %}
    ```

    Then `component_name` would be `my_comp`.
    """

    tokens: list[str]
    """
    Remaining tokens (words) that were passed to the tag, with component name removed

    For example, if we had tag

    ```django
    {% component "my_comp" key=val key2=val2 %}
    ```

    Then `tokens` would be `['key=val', 'key2=val2']`.
    """


class TagFormatterABC(abc.ABC):
    """
    Abstract base class for defining custom tag formatters.

    Tag formatters define how the component tags are used in the template.

    Read more about [Tag formatter](../../concepts/advanced/tag_formatter).

    For example, with the default tag formatter
    ([`ComponentFormatter`](../tag_formatters#django_components.tag_formatter.ComponentFormatter)),
    components are written as:

    ```django
    {% component "comp_name" %}
    {% endcomponent %}
    ```

    While with the shorthand tag formatter
    ([`ShorthandComponentFormatter`](../tag_formatters#django_components.tag_formatter.ShorthandComponentFormatter)),
    components are written as:
    ```django
    {% comp_name %}
    {% endcomp_name %}
    ```

    **Example:**

    Implementation for `ShorthandComponentFormatter`:

    ```python
    from djagno_components import TagFormatterABC, TagResult

    class ShorthandComponentFormatter(TagFormatterABC):
        def start_tag(self, name: str) -> str:
            return name

        def end_tag(self, name: str) -> str:
            return f"end{name}"

        def parse(self, tokens: list[str]) -> TagResult:
            tokens = [*tokens]
            name = tokens.pop(0)
            return TagResult(name, tokens)
    ```
    """

    @abc.abstractmethod
    def start_tag(self, name: str) -> str:
        """
        Formats the start tag of a component.

        Args:
            name (str): Component's registered name. Required.

        Returns:
            str: The formatted start tag.

        """
        ...

    @abc.abstractmethod
    def end_tag(self, name: str) -> str:
        """
        Formats the end tag of a block component.

        Args:
            name (str): Component's registered name. Required.

        Returns:
            str: The formatted end tag.

        """
        ...

    @abc.abstractmethod
    def parse(self, tokens: list[str]) -> TagResult:
        """
        Given the tokens (words) passed to a component start tag, this function extracts
        the component name from the tokens list, and returns
        [`TagResult`](../api#django_components.TagResult),
        which is a tuple of `(component_name, remaining_tokens)`.

        Args:
            tokens (list[str]): List of tokens passed to the component tag.

        Returns:
            TagResult: Parsed component name and remaining tokens.

        **Example:**

        Assuming we used a component in a template like this:

        ```django
        {% component "my_comp" key=val key2=val2 %}
        {% endcomponent %}
        ```

        This function receives a list of tokens:

        ```python
        ['component', '"my_comp"', 'key=val', 'key2=val2']
        ```

        - `component` is the tag name, which we drop.
        - `"my_comp"` is the component name, but we must remove the extra quotes.
        - The remaining tokens we pass unmodified, as that's the input to the component.

        So in the end, we return:

        ```python
        TagResult('my_comp', ['key=val', 'key2=val2'])
        ```

        """
        ...


class InternalTagFormatter:
    """Internal wrapper around user-provided TagFormatters, so that we validate the outputs."""

    def __init__(self, tag_formatter: TagFormatterABC) -> None:
        self.tag_formatter = tag_formatter

    def start_tag(self, name: str) -> str:
        tag = self.tag_formatter.start_tag(name)
        self._validate_tag(tag, "start_tag")
        return tag

    def end_tag(self, name: str) -> str:
        tag = self.tag_formatter.end_tag(name)
        self._validate_tag(tag, "end_tag")
        return tag

    def parse(self, tokens: list[str]) -> TagResult:
        return self.tag_formatter.parse(tokens)

    # NOTE: We validate the generated tags, so they contain only valid characters (\w - : . @ #)
    # and NO SPACE. Otherwise we wouldn't be able to distinguish a "multi-word" tag from several
    # single-word tags.
    def _validate_tag(self, tag: str, tag_type: str) -> None:
        if not tag:
            raise ValueError(
                f"{self.tag_formatter.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag cannot be empty",
            )

        if not TAG_RE.match(tag):
            raise ValueError(
                f"{self.tag_formatter.__class__.__name__} returned an invalid tag for {tag_type}: '{tag}'."
                f" Tag must contain only following chars: {TAG_CHARS}",
            )


class ComponentFormatter(TagFormatterABC):
    """
    The original django_component's component tag formatter, it uses the `{% component %}`
    and `{% endcomponent %}` tags, and the component name is given as the first positional arg.

    Example as block:
    ```django
    {% component "mycomp" abc=123 %}
        {% fill "myfill" %}
            ...
        {% endfill %}
    {% endcomponent %}
    ```

    Example as inlined tag:
    ```django
    {% component "mycomp" abc=123 / %}
    ```
    """

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def start_tag(self, name: str) -> str:  # noqa: ARG002
        return self.tag

    def end_tag(self, name: str) -> str:  # noqa: ARG002
        return f"end{self.tag}"

    def parse(self, tokens: list[str]) -> TagResult:
        _tag, *args = tokens

        if not args:
            raise TemplateSyntaxError(f"{self.__class__.__name__}: Component tag did not receive tag name")

        # If the first arg is a kwarg, then clearly the component name is not set.
        comp_name = None if "=" in args[0] else args.pop(0)

        if not comp_name:
            raise TemplateSyntaxError("Component name must be a non-empty quoted string, e.g. 'my_comp'")

        if not is_str_wrapped_in_quotes(comp_name):
            raise TemplateSyntaxError(f"Component name must be a string 'literal', got: {comp_name}")

        # Remove the quotes
        comp_name = comp_name[1:-1]

        return TagResult(comp_name, args)


class ShorthandComponentFormatter(TagFormatterABC):
    """
    The component tag formatter that uses `{% <name> %}` / `{% end<name> %}` tags.

    This is similar to [django-web-components](https://github.com/Xzya/django-web-components)
    and [django-slippers](https://github.com/mixxorz/slippers)
    syntax.

    Example as block:
    ```django
    {% mycomp abc=123 %}
        {% fill "myfill" %}
            ...
        {% endfill %}
    {% endmycomp %}
    ```

    Example as inlined tag:
    ```django
    {% mycomp abc=123 / %}
    ```
    """

    def start_tag(self, name: str) -> str:
        return name

    def end_tag(self, name: str) -> str:
        return f"end{name}"

    def parse(self, tokens: list[str]) -> TagResult:
        tokens = [*tokens]
        name = tokens.pop(0)
        return TagResult(name, tokens)


def get_tag_formatter(registry: "ComponentRegistry") -> InternalTagFormatter:
    """Returns an instance of the currently configured component tag formatter."""
    # Allow users to configure the component TagFormatter
    formatter_cls_or_str = registry.settings.tag_formatter

    if isinstance(formatter_cls_or_str, str):
        tag_formatter: TagFormatterABC = import_string(formatter_cls_or_str)
    else:
        tag_formatter = formatter_cls_or_str

    return InternalTagFormatter(tag_formatter)


# Pre-defined formatters
component_formatter = ComponentFormatter("component")
component_shorthand_formatter = ShorthandComponentFormatter()
