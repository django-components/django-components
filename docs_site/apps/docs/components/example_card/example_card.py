"""
ExampleCard - tabbed widget showing Component code, Page code, and Live demo.

Reuses the shared .tabbed-set tab system (site.css + site.js) instead of
a custom CSS radio-button implementation. The JS tab handler in site.js
picks up the .tabbed-set container automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from django_components import Component, register, types

if TYPE_CHECKING:
    from apps.docs.examples import ExampleInfo


@register("example_card")
class ExampleCard(Component):
    class Kwargs:
        name: str
        info: ExampleInfo

    template: types.django_html = """
        <div class="tabbed-set example-card" data-tabs="ex-{{ name }}:3">
            <input checked id="__tabbed_ex{{ name }}_1" name="__tabbed_ex{{ name }}" type="radio">
            <input id="__tabbed_ex{{ name }}_2" name="__tabbed_ex{{ name }}" type="radio">
            <input id="__tabbed_ex{{ name }}_3" name="__tabbed_ex{{ name }}" type="radio">
            <div class="tabbed-labels">
                <label for="__tabbed_ex{{ name }}_1">Live demo</label>
                <label for="__tabbed_ex{{ name }}_2">Component</label>
                <label for="__tabbed_ex{{ name }}_3">Page</label>
            </div>
            <div class="tabbed-content">
                <div class="tabbed-block tabbed-block--demo">
                    <iframe
                        src="{{ demo_url }}"
                        class="example-demo-frame"
                        sandbox="allow-scripts allow-same-origin"
                        loading="lazy"
                    ></iframe>
                </div>
                <div class="tabbed-block">
                    {{ component_code_html|safe }}
                </div>
                <div class="tabbed-block">
                    {{ page_code_html|safe }}
                </div>
            </div>
        </div>
    """

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        info: ExampleInfo = kwargs.info
        name = kwargs.name

        component_code = (info.example_dir / "component.py").read_text(encoding="utf-8")
        page_code = (info.example_dir / "page.py").read_text(encoding="utf-8")

        formatter = HtmlFormatter(cssclass="highlight", nowrap=False)
        lexer = PythonLexer()

        component_code_html = highlight(component_code, lexer, formatter)
        page_code_html = highlight(page_code, lexer, formatter)

        demo_url = f"/examples/{name}/"

        return {
            "name": name,
            "component_code_html": component_code_html,
            "page_code_html": page_code_html,
            "demo_url": demo_url,
        }
