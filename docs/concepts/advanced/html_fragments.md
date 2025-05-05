Django-components provides a seamless integration with HTML fragments with AJAX ([HTML over the wire](https://hotwired.dev/)),
whether you're using jQuery, HTMX, AlpineJS, vanilla JavaScript, or other.

If the fragment component has any JS or CSS, django-components will:

- Automatically load the associated JS and CSS
- Ensure that JS is loaded and executed only once even if the fragment is inserted multiple times

!!! info

    **What are HTML fragments and "HTML over the wire"?**

    It is one of the methods for updating the state in the browser UI upon user interaction.

    How it works is that:

    1. User makes an action - clicks a button or submits a form
    2. The action causes a request to be made from the client to the server.
    3. Server processes the request (e.g. form submission), and responds with HTML
       of some part of the UI (e.g. a new entry in a table).
    4. A library like HTMX, AlpineJS, or custom function inserts the new HTML into
       the correct place.

## Document and fragment strategies

Components support different ["strategies"](../../advanced/rendering_js_css#dependencies-strategies)
for rendering JS and CSS.

Two of them are used to enable HTML fragments - ["document"](../../advanced/rendering_js_css#document)
and ["fragment"](../../advanced/rendering_js_css#fragment).

What's the difference?

### Document strategy

Document strategy assumes that the rendered components will be embedded into the HTML
of the initial page load. This means that:

- The JS and CSS is embedded into the HTML as `<script>` and `<style>` tags
  (see [Default JS / CSS locations](./rendering_js_css.md#default-js-css-locations))
- Django-components injects a JS script for managing JS and CSS assets

A component is rendered as a "document" when:

- It is embedded inside a template as [`{% component %}`](../../reference/template_tags.md#component)
- It is rendered with [`Component.render()`](../../../reference/api#django_components.Component.render)
or [`Component.render_to_response()`](../../../reference/api#django_components.Component.render_to_response)
  with the `deps_strategy` kwarg set to `"document"` (default)

Example:

```py
MyTable.render(
    kwargs={...},
)

# or

MyTable.render(
    kwargs={...},
    deps_strategy="document",
)
```

### Fragment strategy

Fragment strategy assumes that the main HTML has already been rendered and loaded on the page.
The component renders HTML that will be inserted into the page as a fragment, at a LATER time:

- JS and CSS is not directly embedded to avoid duplicately executing the same JS scripts.
  So template tags like [`{% component_js_dependencies %}`](../../reference/template_tags.md#component_js_dependencies)
  inside of fragments are ignored.
- Instead, django-components appends the fragment's content with a JSON `<script>` to trigger a call
  to its asset manager JS script, which will load the JS and CSS smartly.
- The asset manager JS script is assumed to be already loaded on the page.

A component is rendered as "fragment" when:

- It is rendered with [`Component.render()`](../../../reference/api#django_components.Component.render)
  or [`Component.render_to_response()`](../../../reference/api#django_components.Component.render_to_response)
  with the `deps_strategy` kwarg set to `"fragment"`

Example:

```py
MyTable.render(
    kwargs={...},
    deps_strategy="fragment",
)
```

## Live examples

For live interactive examples, [start our demo project](../../overview/development.md#developing-against-live-django-app)
(`sampleproject`).

Then navigate to these URLs:

- `/fragment/base/alpine`
- `/fragment/base/htmx`
- `/fragment/base/js`

## Example - HTMX

### 1. Define document HTML

This is the HTML into which a fragment will be loaded using HTMX.

```djc_py title="[root]/components/demo.py"
from django_components import Component, types

class MyPage(Component):
    template = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
                <script src="https://unpkg.com/htmx.org@1.9.12"></script>
            </head>
            <body>
                <div id="target">OLD</div>

                <button
                    hx-get="/mypage/frag"
                    hx-swap="outerHTML"
                    hx-target="#target"
                >
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(request=request)
```

### 2. Define fragment HTML

The fragment to be inserted into the document.

IMPORTANT: Don't forget to set `deps_strategy="fragment"`

```djc_py title="[root]/components/demo.py"
class Frag(Component):
    template = """
        <div class="frag">
            123
            <span id="frag-text"></span>
        </div>
    """

    js = """
        document.querySelector('#frag-text').textContent = 'xxx';
    """

    css = """
        .frag {
            background: blue;
        }
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(
                request=request,
                # IMPORTANT: Don't forget `deps_strategy="fragment"`
                deps_strategy="fragment",
            )
```

### 3. Create view and URLs

```py title="[app]/urls.py"
from django.urls import path

from components.demo import MyPage, Frag

urlpatterns = [
    path("mypage/", MyPage.as_view())
    path("mypage/frag", Frag.as_view()),
]
```

## Example - AlpineJS

### 1. Define document HTML

This is the HTML into which a fragment will be loaded using AlpineJS.

```djc_py title="[root]/components/demo.py"
from django_components import Component, types

class MyPage(Component):
    template = """
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
                    const url = '/mypage/frag';
                    fetch(url)
                        .then(response => response.text())
                        .then(html => {
                            this.htmlVar = html;
                        });
                }
            }">
                <div id="target" x-html="htmlVar">OLD</div>

                <button @click="loadFragment">
                  Click me!
                </button>

                {% component_js_dependencies %}
            </body>
        </html>
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(request=request)
```

### 2. Define fragment HTML

The fragment to be inserted into the document.

IMPORTANT: Don't forget to set `deps_strategy="fragment"`

```djc_py title="[root]/components/demo.py"
class Frag(Component):
    # NOTE: We wrap the actual fragment in a template tag with x-if="false" to prevent it
    #       from being rendered until we have registered the component with AlpineJS.
    template = """
        <template x-if="false" data-name="frag">
            <div class="frag">
                123
                <span x-data="frag" x-text="fragVal">
                </span>
            </div>
        </template>
    """

    js = """
        Alpine.data('frag', () => ({
            fragVal: 'xxx',
        }));

        // Now that the component has been defined in AlpineJS, we can "activate"
        // all instances where we use the `x-data="frag"` directive.
        document.querySelectorAll('[data-name="frag"]').forEach((el) => {
            el.setAttribute('x-if', 'true');
        });
    """

    css = """
        .frag {
            background: blue;
        }
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(
                request=request,
                # IMPORTANT: Don't forget `deps_strategy="fragment"`
                deps_strategy="fragment",
            )
```

### 3. Create view and URLs

```py title="[app]/urls.py"
from django.urls import path

from components.demo import MyPage, Frag

urlpatterns = [
    path("mypage/", MyPage.as_view())
    path("mypage/frag", Frag.as_view()),
]
```

## Example - Vanilla JS

### 1. Define document HTML

This is the HTML into which a fragment will be loaded using vanilla JS.

```djc_py title="[root]/components/demo.py"
from django_components import Component, types

class MyPage(Component):
    template = """
        {% load component_tags %}
        <!DOCTYPE html>
        <html>
            <head>
                {% component_css_dependencies %}
            </head>
            <body>
                <div id="target">OLD</div>

                <button>
                  Click me!
                </button>
                <script>
                    const url = `/mypage/frag`;
                    document.querySelector('#loader').addEventListener('click', function () {
                        fetch(url)
                            .then(response => response.text())
                            .then(html => {
                                document.querySelector('#target').outerHTML = html;
                            });
                    });
                </script>

                {% component_js_dependencies %}
            </body>
        </html>
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(request=request)
```

### 2. Define fragment HTML

The fragment to be inserted into the document.

IMPORTANT: Don't forget to set `deps_strategy="fragment"`

```djc_py title="[root]/components/demo.py"
class Frag(Component):
    template = """
        <div class="frag">
            123
            <span id="frag-text"></span>
        </div>
    """

    js = """
        document.querySelector('#frag-text').textContent = 'xxx';
    """

    css = """
        .frag {
            background: blue;
        }
    """

    class View:
        def get(self, request):
            return self.component.render_to_response(
                request=request,
                # IMPORTANT: Don't forget `deps_strategy="fragment"`
                deps_strategy="fragment",
            )
```

### 3. Create view and URLs

```py title="[app]/urls.py"
from django.urls import path

from components.demo import MyPage, Frag

urlpatterns = [
    path("mypage/", MyPage.as_view())
    path("mypage/frag", Frag.as_view()),
]
```
