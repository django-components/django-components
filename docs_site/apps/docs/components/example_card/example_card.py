"""
ExampleCard - tabbed widget showing Component code, Page code, and Live demo.

This is the centerpiece of Phase 2: the {% example %} tag renders an ExampleCard
for each referenced example. The component reads the example's source files,
syntax-highlights them, and renders the live demo in an iframe that loads the
pre-rendered example page by URL.

For fragment examples, the pre-rendered page has its get_component_url() outputs
rewritten to point at static file paths so fragment buttons work on GitHub Pages.
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
        <div class="example-card">
            <input
                type="radio"
                name="example-{{ name }}"
                id="tab-{{ name }}-demo"
                class="example-tab-input"
                checked
            >
            <input
                type="radio"
                name="example-{{ name }}"
                id="tab-{{ name }}-component"
                class="example-tab-input"
            >
            <input
                type="radio"
                name="example-{{ name }}"
                id="tab-{{ name }}-page"
                class="example-tab-input"
            >
            <div class="example-tabs">
                <label for="tab-{{ name }}-demo">Live demo</label>
                <label for="tab-{{ name }}-component">Component</label>
                <label for="tab-{{ name }}-page">Page</label>
            </div>
            <div class="example-panel example-panel-demo">
                <iframe
                    src="{{ demo_url }}" class="example-demo-frame"
                    sandbox="allow-scripts allow-same-origin"
                    loading="lazy"
                ></iframe>
            </div>
            <div class="example-panel example-panel-component">
                {{ component_code_html|safe }}
            </div>
            <div class="example-panel example-panel-page">
                {{ page_code_html|safe }}
            </div>
            <style>
                .example-card {
                    margin: 1.5rem 0;
                    border: 1px solid var(--c-border, #d0d5db);
                    border-radius: 0.5rem;
                    overflow: hidden;
                }
                .example-tab-input { display: none; }
                .example-tabs {
                    display: flex;
                    background: var(--c-surface-2, #e9edf2);
                    border-bottom: 1px solid var(--c-border, #d0d5db);
                }
                .example-tabs label {
                    padding: 0.6rem 1.2rem;
                    cursor: pointer;
                    font-size: 0.85rem;
                    font-weight: 500;
                    color: var(--c-fg-muted, #525b6e);
                    border-bottom: 2px solid transparent;
                    transition: color 0.15s, border-color 0.15s;
                    user-select: none;
                }
                .example-tabs label:hover {
                    color: var(--c-fg, #1d2030);
                }
                .example-panel {
                    display: none;
                    padding: 0;
                }
                .example-panel pre {
                    margin: 0;
                    border: none;
                    border-radius: 0;
                    border-left: none;
                    max-height: 500px;
                    overflow: auto;
                }
                .example-demo-frame {
                    width: 100%;
                    min-height: 400px;
                    border: none;
                    background: #fff;
                }

                /* Radio-button tab switching via CSS :checked + sibling selectors */
                #tab-{{ name }}-component:checked ~ .example-tabs label[for="tab-{{ name }}-component"],
                #tab-{{ name }}-page:checked ~ .example-tabs label[for="tab-{{ name }}-page"],
                #tab-{{ name }}-demo:checked ~ .example-tabs label[for="tab-{{ name }}-demo"] {
                    color: var(--c-link, #3870c5);
                    border-bottom-color: var(--c-link, #3870c5);
                }
                #tab-{{ name }}-component:checked ~ .example-panel-component,
                #tab-{{ name }}-page:checked ~ .example-panel-page,
                #tab-{{ name }}-demo:checked ~ .example-panel-demo {
                    display: block;
                }
            </style>
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

        # The iframe loads the pre-rendered example page by URL.
        # On the dev server this hits serve_example(); on the static site
        # it loads the pre-rendered HTML file at the same path.
        demo_url = f"/examples/{name}/"

        return {
            "name": name,
            "component_code_html": component_code_html,
            "page_code_html": page_code_html,
            "demo_url": demo_url,
        }
