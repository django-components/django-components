# NOTE: This file is used for benchmarking. Before editing this file,
# please read through these:
# - `benchmarks/README`
# - https://github.com/django-components/django-components/pull/999

from pathlib import Path
from typing import Dict, Literal, NamedTuple, Optional, Union

import django
from django.conf import settings
from django.template import Context, Template

from django_components import types

# DO NOT REMOVE - See https://github.com/django-components/django-components/pull/999
# ----------- IMPORTS END ------------ #

# This variable is overridden by the benchmark runner
CONTEXT_MODE: Literal["django", "isolated"] = "isolated"

if not settings.configured:
    settings.configure(
        BASE_DIR=Path(__file__).resolve().parent,
        INSTALLED_APPS=["django_components"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    "tests/templates/",
                    "tests/components/",  # Required for template relative imports in tests
                ],
                "OPTIONS": {
                    "builtins": [
                        "django_components.templatetags.component_tags",
                    ]
                },
            }
        ],
        COMPONENTS={
            "template_cache_size": 128,
            "autodiscover": False,
            "context_behavior": CONTEXT_MODE,
        },
        MIDDLEWARE=["django_components.middleware.ComponentDependencyMiddleware"],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SECRET_KEY="secret",
        ROOT_URLCONF="django_components.urls",
    )
    django.setup()
else:
    settings.COMPONENTS["context_behavior"] = CONTEXT_MODE

#####################################
#
# IMPLEMENTATION START
#
#####################################

templates_cache: Dict[int, Template] = {}


def lazy_load_template(template: str) -> Template:
    template_hash = hash(template)
    if template_hash in templates_cache:
        return templates_cache[template_hash]
    else:
        template_instance = Template(template)
        templates_cache[template_hash] = template_instance
        return template_instance


#####################################
# RENDER ENTRYPOINT
#####################################


def gen_render_data():
    data = ButtonData(
        href="https://example.com",
        disabled=False,
        variant="primary",
        type="button",
        attrs={
            "class": "py-2 px-4",
        },
        slot_content="Click me!",
    )
    return data


def render(data: "ButtonData"):
    # Render
    result = button(Context(), data)
    return result


#####################################
# THEME
#####################################

ThemeColor = Literal["default", "error", "success", "alert", "info"]
ThemeVariant = Literal["primary", "secondary"]

VARIANTS = ["primary", "secondary"]


class ThemeStylingUnit(NamedTuple):
    """
    Smallest unit of info, this class defines a specific styling of a specific
    component in a specific state.

    E.g. styling of a disabled "Error" button.
    """

    color: str
    """CSS class(es) specifying color"""
    css: str = ""
    """Other CSS classes not specific to color"""


class ThemeStylingVariant(NamedTuple):
    """
    Collection of styling combinations that are meaningful as a group.

    E.g. all "error" variants - primary, disabled, secondary, ...
    """

    primary: ThemeStylingUnit
    primary_disabled: ThemeStylingUnit
    secondary: ThemeStylingUnit
    secondary_disabled: ThemeStylingUnit


class Theme(NamedTuple):
    """Class for defining a styling and color theme for the app."""

    default: ThemeStylingVariant
    error: ThemeStylingVariant
    alert: ThemeStylingVariant
    success: ThemeStylingVariant
    info: ThemeStylingVariant


_secondary_btn_styling = "ring-1 ring-inset"

theme = Theme(
    default=ThemeStylingVariant(
        primary=ThemeStylingUnit(
            color="bg-blue-600 text-white hover:bg-blue-500 focus-visible:outline-blue-600 transition"
        ),
        primary_disabled=ThemeStylingUnit(color="bg-blue-300 text-blue-50 focus-visible:outline-blue-600 transition"),
        secondary=ThemeStylingUnit(
            color="bg-white text-gray-800 ring-gray-300 hover:bg-gray-100 focus-visible:outline-gray-600 transition",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-gray-300 ring-gray-300 focus-visible:outline-gray-600 transition",
            css=_secondary_btn_styling,
        ),
    ),
    error=ThemeStylingVariant(
        primary=ThemeStylingUnit(color="bg-red-600 text-white hover:bg-red-500 focus-visible:outline-red-600"),
        primary_disabled=ThemeStylingUnit(color="bg-red-300 text-white focus-visible:outline-red-600"),
        secondary=ThemeStylingUnit(
            color="bg-white text-red-600 ring-red-300 hover:bg-red-100 focus-visible:outline-red-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-red-200 ring-red-100 focus-visible:outline-red-600",
            css=_secondary_btn_styling,
        ),
    ),
    alert=ThemeStylingVariant(
        primary=ThemeStylingUnit(color="bg-amber-500 text-white hover:bg-amber-400 focus-visible:outline-amber-500"),
        primary_disabled=ThemeStylingUnit(color="bg-amber-100 text-orange-300 focus-visible:outline-amber-500"),
        secondary=ThemeStylingUnit(
            color="bg-white text-amber-500 ring-amber-300 hover:bg-amber-100 focus-visible:outline-amber-500",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-orange-200 ring-amber-100 focus-visible:outline-amber-500",
            css=_secondary_btn_styling,
        ),
    ),
    success=ThemeStylingVariant(
        primary=ThemeStylingUnit(color="bg-green-600 text-white hover:bg-green-500 focus-visible:outline-green-600"),
        primary_disabled=ThemeStylingUnit(color="bg-green-300 text-white focus-visible:outline-green-600"),
        secondary=ThemeStylingUnit(
            color="bg-white text-green-600 ring-green-300 hover:bg-green-100 focus-visible:outline-green-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-green-200 ring-green-100 focus-visible:outline-green-600",
            css=_secondary_btn_styling,
        ),
    ),
    info=ThemeStylingVariant(
        primary=ThemeStylingUnit(color="bg-sky-600 text-white hover:bg-sky-500 focus-visible:outline-sky-600"),
        primary_disabled=ThemeStylingUnit(color="bg-sky-300 text-white focus-visible:outline-sky-600"),
        secondary=ThemeStylingUnit(
            color="bg-white text-sky-600 ring-sky-300 hover:bg-sky-100 focus-visible:outline-sky-600",
            css=_secondary_btn_styling,
        ),
        secondary_disabled=ThemeStylingUnit(
            color="bg-white text-sky-200 ring-sky-100 focus-visible:outline-sky-600",
            css=_secondary_btn_styling,
        ),
    ),
)


def get_styling_css(
    variant: Optional["ThemeVariant"] = None,
    color: Optional["ThemeColor"] = None,
    disabled: Optional[bool] = None,
):
    """
    Dynamically access CSS styling classes for a specific variant and state.

    E.g. following two calls get styling classes for:
    1. Secondary error state
    1. Secondary alert disabled state
    2. Primary default disabled state
    ```py
    get_styling_css('secondary', 'error')
    get_styling_css('secondary', 'alert', disabled=True)
    get_styling_css(disabled=True)
    ```
    """
    variant = variant or "primary"
    color = color or "default"
    disabled = disabled if disabled is not None else False

    color_variants: ThemeStylingVariant = getattr(theme, color)

    if variant not in VARIANTS:
        raise ValueError(f'Unknown theme variant "{variant}", must be one of {VARIANTS}')

    variant_name = variant if not disabled else f"{variant}_disabled"
    styling: ThemeStylingUnit = getattr(color_variants, variant_name)

    css = f"{styling.color} {styling.css}".strip()
    return css


#####################################
# BUTTON
#####################################

button_template_str: types.django_html = """
    {# Based on buttons from https://tailwindui.com/components/application-ui/overlays/modals #}

    {% if is_link %}
    <a
        href="{{ href }}"
        {% html_attrs attrs class=btn_class class="no-underline" %}
    >
    {% else %}
    <button
        type="{{ type }}"
        {% if disabled %} disabled {% endif %}
        {% html_attrs attrs class=btn_class %}
    >
    {% endif %}

        {{ slot_content }}

    {% if is_link %}
    </a>
    {% else %}
    </button>
    {% endif %}
"""


class ButtonData(NamedTuple):
    href: Optional[str] = None
    link: Optional[bool] = None
    disabled: Optional[bool] = False
    variant: Union["ThemeVariant", Literal["plain"]] = "primary"
    color: Union["ThemeColor", str] = "default"
    type: Optional[str] = "button"
    attrs: Optional[dict] = None
    slot_content: Optional[str] = ""


def button(context: Context, data: ButtonData):
    common_css = (
        "inline-flex w-full text-sm font-semibold"
        " sm:mt-0 sm:w-auto focus-visible:outline-2 focus-visible:outline-offset-2"
    )
    if data.variant == "plain":
        all_css_class = common_css
    else:
        button_classes = get_styling_css(data.variant, data.color, data.disabled)  # type: ignore[arg-type]
        all_css_class = f"{button_classes} {common_css} px-3 py-2 justify-center rounded-md shadow-sm"

    is_link = not data.disabled and (data.href or data.link)

    all_attrs = {**(data.attrs or {})}
    if data.disabled:
        all_attrs["aria-disabled"] = "true"

    with context.push(
        {
            "href": data.href,
            "disabled": data.disabled,
            "type": data.type,
            "btn_class": all_css_class,
            "attrs": all_attrs,
            "is_link": is_link,
            "slot_content": data.slot_content,
        }
    ):
        return lazy_load_template(button_template_str).render(context)


#####################################
#
# IMPLEMENTATION END
#
#####################################


# DO NOT REMOVE - See https://github.com/django-components/django-components/pull/999
# ----------- TESTS START ------------ #
# The code above is used also used when benchmarking.
# The section below is NOT included.

from django_components.testing import djc_test  # noqa: E402

@djc_test
def test_render(snapshot):
    data = gen_render_data()
    rendered = render(data)
    assert rendered == snapshot
