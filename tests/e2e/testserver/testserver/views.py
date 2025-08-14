from django.http import HttpResponse
from django.template import Context, Template
from testserver.components import FragComp, FragMedia

from django_components import types


def single_component_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'inner' variable='foo' / %}
                <div class="my-style">123</div>
                <div class="my-style2">xyz</div>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def multiple_components_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                <div class="my-style">123</div>
                <div class="my-style2">xyz</div>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def check_js_order_in_js_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                {# check_script_order_in_media is AFTER the other components #}
                {% component 'check_script_order_in_js' / %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def check_js_order_in_media_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                {# check_script_order_in_media is AFTER the other components #}
                {% component 'check_script_order_in_media' / %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def check_js_order_vars_not_available_before_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {# check_script_order_in_media is BEFORE the other components #}
                {% component 'check_script_order_in_media' / %}
                {% component 'outer' variable='variable' %}
                    {% component 'other' variable='variable_inner' / %}
                {% endcomponent %}
                abc
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


# HTML into which a fragment will be loaded using vanilla JS
def fragment_base_js_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'inner' variable='foo' / %}

                <div id="target">OLD</div>

                <button id="loader">
                  Click me!
                </button>
                <script>
                    const frag = "{{ frag }}";
                    document.querySelector('#loader').addEventListener('click', function () {
                        fetch(`/fragment/frag?frag=${frag}`)
                            .then(response => response.text())
                            .then(html => {
                                console.log({ fragment: html })
                                const target = document.querySelector('#target');
                                const a = new DOMParser().parseFromString(html, "text/html");
                                target.replaceWith(...a.body.childNodes);
                                for (const script of a.querySelectorAll('script')) {
                                    const newScript = document.createElement('script');
                                    newScript.textContent = script.textContent;
                                    newScript.async = false;
                                    document.body.appendChild(newScript);
                                }
                            });
                    });
                </script>

                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    frag = request.GET["frag"]
    rendered = template.render(
        Context(
            {
                "frag": frag,
            }
        )
    )
    return HttpResponse(rendered)


# HTML into which a fragment will be loaded using AlpineJS
def fragment_base_alpine_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script defer src="https://unpkg.com/alpinejs"></script>
            </head>
            <body x-data="{
                htmlVar: 'OLD',
                loadFragment: function () {
                    const frag = '{{ frag }}';
                    fetch(`/fragment/frag?frag=${frag}`)
                        .then(response => response.text())
                        .then(html => {
                            console.log({ fragment: html });
                            this.htmlVar = html;
                        });
                }
            }">
                {% component 'inner' variable='foo' / %}

                <div id="target" x-html="htmlVar">OLD</div>

                <button id="loader" @click="loadFragment">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    frag = request.GET["frag"]
    rendered = template.render(Context({"frag": frag}))
    return HttpResponse(rendered)


# HTML into which a fragment will be loaded using HTMX
def fragment_base_htmx_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script src="https://unpkg.com/htmx.org@1.9.12"></script>
            </head>
            <body>
                {% component 'inner' variable='foo' / %}

                <div id="target">OLD</div>

                <button id="loader" hx-get="/fragment/frag?frag={{ frag }}" hx-swap="outerHTML" hx-target="#target">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    frag = request.GET["frag"]
    rendered = template.render(Context({"frag": frag}))
    return HttpResponse(rendered)


# HTML into which a fragment will be loaded using HTMX
# This variant doesn't include the component manager script, so that we can test
# that the fragment can be rendered even when the page wasn't rendered with the "document" strategy.
def fragment_base_htmx_view__raw(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script src="https://unpkg.com/htmx.org@1.9.12"></script>
            </head>
            <body>
                {% component 'inner' variable='foo' / %}

                <div id="target">OLD</div>

                <button id="loader" hx-get="/fragment/frag?frag={{ frag }}" hx-swap="outerHTML" hx-target="#target">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)

    frag = request.GET["frag"]
    rendered = template.render(Context({"frag": frag, "DJC_DEPS_STRATEGY": "ignore"}))
    return HttpResponse(rendered)


def fragment_view(request):
    fragment_type = request.GET["frag"]
    if fragment_type == "comp":
        return FragComp.render_to_response(deps_strategy="fragment")
    elif fragment_type == "media":
        return FragMedia.render_to_response(deps_strategy="fragment")
    else:
        raise ValueError("Invalid fragment type")


def alpine_in_head_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script defer src="https://unpkg.com/alpinejs"></script>
            </head>
            <body>
                {% component 'alpine_test_in_media' / %}
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def alpine_in_body_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_media' / %}
                {% component_js_dependencies %}
                <script src="https://unpkg.com/alpinejs"></script>
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


# Same as before, but Alpine component defined in Component.js
def alpine_in_body_view_2(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_js' / %}
                {% component_js_dependencies %}
                <script src="https://unpkg.com/alpinejs"></script>
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)


def alpine_in_body_vars_not_available_before_view(request):
    template_str: types.django_html = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                {% component 'alpine_test_in_js' / %}
                {# Alpine loaded BEFORE components JS #}
                <script src="https://unpkg.com/alpinejs"></script>
                {% component_js_dependencies %}
            </body>
        </html>
    """
    template = Template(template_str)
    rendered = template.render(Context({}))
    return HttpResponse(rendered)
