# JS and CSS rendering

Aim of this doc is to share the intuition on how we manage the JS and CSS ("dependencies")
associated with components, and how we render them.

## Starting conditions

1. First of all, when we consider a component, it has two kind of dependencies - the "inlined" JS and CSS, and additional linked JS and CSS via `Media.js/css`:

    ```djc_py
    from django_components import Component, types

    class MyTable(Component):
        # Inlined JS
        js: types.js = """
          console.log(123);
        """

        # Inlined CSS
        css: types.css = """
          .my-table {
            color: red;
          }
        """

        # Linked JS / CSS
        class Media:
            js = [
                "script-one.js",  # STATIC file relative to component file
                "/script-two.js", # URL path
                "https://example.com/script-three.js", # URL
            ]

            css = [
                "style-one.css",  # STATIC file relative to component file
                "/style-two.css", # URL path
                "https://example.com/style-three.css", # URL
            ]
    ```

2. Second thing to keep in mind is that all component's are eventually rendered into a string. And so, if we want to associate extra info with a rendered component, it has to be serialized to a string.

    This is because a component may be embedded in a Django Template with the `{% component %}` tag, which, when rendered, is turned into a string:

    ```py
    template = Template("""
      {% load component_tags %}
      <div>
        {% component "my_table" / %}
      </div>
    """)

    html_str = template.render(Context({}))
    ```

    And for this reason, we take the same approach also when we render a component with `Component.render()` - It returns a string.

3. Thirdly, we also want to add support for JS / CSS variables. That is, that a variable defined on the component would be somehow accessible from within the JS script / CSS style.

    A simple approach to this would be to modify the inlined JS / CSS directly, and insert them for each component. But if you had extremely large JS / CSS, and e.g. only a single JS / CSS variable that you want to insert, it would be wasteful to create a copy of the JS / CSS scripts for each component instance.

    So instead, a preferred approach here is to defined and insert the inlined JS / CSS only once, and have some kind of mechanism on how we make correct the JS / CSS variables available only to the correct components.

4. Last important thing is that we want the JS / CSS dependencies to work also with HTML fragments.

    So normally, e.g. when a user hits URL of a web page, the server renders full HTML document, with `<!doctype>`, `<html>`, `<head>`, and `<body>`. In such case, we know about ALL JS and CSS dependencies at render time, so we can e.g. insert them into `<head>` and `<body>` ourselves.

    However this renders only the initial state. HTML fragments is a common pattern where interactivity is added to the web page by fetching and replacing bits of HTML on the main HTML document after some user action.

    In the case of HTML fragments, the HTML is NOT a proper document, but only the HTML that will be inserted somewhere into the DOM.

    The challenge here is that Django template for the HTML fragment MAY contain components, and these components MAY have inlined or linked JS and CSS.

    ```py
    def fragment_view(request):
        template = Template("""
          {% load component_tags %}
          <div>
            {% component "my_table" / %}
          </div>
        """)

        fragment_str = template.render(Context({}))
        return HttpResponse(fragment_str, status=200)
    ```

    User may use different libraries to fetch and insert the HTML fragments (e.g. HTMX, AlpineJS, ...). From our perspective, the only thing that we can reliably say is that we expect that the HTML fragment WILL be eventually inserted into the DOM.

    So to include the corresponding JS and CSS, a simple approach could be to append them to the HTML as `<style>` and `<script>`, e.g.:

    ```html
    <!-- Original content -->
    <div>...</div>
    <!-- Associated CSS files -->
    <link href="http://..." />
    <style>
      .my-class {
        color: red;
      }
    </style>
    <!-- Associated JS files -->
    <script src="http://..."></script>
    <script>
      console.log(123);
    </script>
    ```

    But this has a number of issues:

    - The JS scripts would run for each instance of the component.
    - Bloating of the HTML file, as each inlined JS or CSS would be included fully for each component.
      - While this sound OK, this could really bloat the HTML files if we used a UI component library for the basic building blocks like buttons, lists, cards, etc.

## Flow

So the solution should address all the points above. To achieve that, we manage the JS / CSS dependencies ourselves in the browser. So when a full HTML document is loaded, we keep track of which JS and CSS have been loaded. And when an HTML fragment is inserted, we check which JS / CSS dependencies it has, and load only those that have NOT been loaded yet.

This is how we achieve that:

1. When a component is rendered, it inserts an HTML comment containing metadata about the rendered component.

    So a template like this

    ```django
    {% load component_tags %}
    <div>
      {% component "my_table" / %}
    </div>
    {% component "button" %}
      Click me!
    {% endcomponent %}
    ```

    May actually render:

    ```html
    <div>
      <!-- _RENDERED "my_table_10bc2c,c020ad" -->
      <table>
        ...
      </table>
    </div>
    <!-- _RENDERED "button_309dcf,31c0da" -->
    <button>Click me!</button>
    ```

    Each `<!-- _RENDERED -->` comment includes comma-separated data - a unique hash for the component class, e.g. `my_table_10bc2c`, and the component ID, e.g. `c020ad`.

    This way, we or the user can freely pass the rendered around or transform it, treating it as a string to add / remove / replace bits. As long as the `<!-- _RENDERED -->` comments remain in the rendered string, we will be able to deduce which JS and CSS dependencies the component needs.

2. Post-process the rendered HTML, extracting the `<!-- _RENDERED -->` comments, and instead inserting the corresponding JS and CSS dependencies.

    If we dealt only with JS, then we could get away with processing the `<!-- _RENDERED -->` comments on the client (browser). However, the CSS needs to be processed still on the server, so the browser receives CSS styles already inserted as `<style>` or `<link>` HTML tags. Because if we do not do that, we get a [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content), as there will be a delay between when the HTML page loaded and when the CSS was fetched and loaded.

    So, assuming that a user has already rendered their template, which still contains `<!-- _RENDERED -->` comments, we need to extract and process these comments.

    There's multiple ways to achieve this:

    - If users are using `Component.render()` or `Component.render_to_response()`, these post-process the `<!-- _RENDERED -->` comments by default.

      - NOTE: Users are able to opt out of the post-processing by setting `deps_strategy="ignore"`.

    - If one renders a Template directly, the `<!-- _RENDERED -->` will be processed too. We achieve this by
      modifying Django's `Template.render()` method.

    - For advanced use cases, users may use `render_dependencies()` directly. This is the function that
      `Component.render()` calls internally.

    `render_dependencies()`, whether called directly, or other way, does the following:

    1. Find all `<!-- _RENDERED -->` comments, and for each comment:

    2. Look up the corresponding component class.

    3. Get the component's inlined JS / CSS from `Component.js/css`, and linked JS / CSS from `Component.Media.js/css`.

    4. Generate JS script that loads the JS / CSS dependencies.

    5. Insert the JS scripts either at the end of `<body>`, or in place of `{% component_dependencies %}` / `{% component_js_dependencies %}` tags.

    6. To avoid the [flash of unstyled content](https://en.wikipedia.org/wiki/Flash_of_unstyled_content), we need place the styles into the HTML instead of dynamically loading them from within a JS script. The CSS is placed either at the end of `<head>`, or in place of `{% component_dependencies %}` / `{% component_css_dependencies %}`

    7. We cache the component's inlined JS and CSS, so they can be fetched via an URL, so the inlined JS / CSS an be treated the same way as the JS / CSS dependencies set in `Component.Media.js/css`.
        - NOTE: While this is currently not entirely necessary, it opens up the doors for allowing plugins to post-process the inlined JS and CSS. Because after it has been post-processed, we need to store it somewhere.

3. Server returns the post-processed HTML.

4. In the browser, the generated JS script from step 2.4 is executed. It goes through all JS and CSS dependencies it was given. If some JS / CSS was already loaded, it is NOT fetched again. Otherwise it generates the corresponding `<script>` or `<link>` HTML tags to load the JS / CSS dependencies.

    In the browser, the "dependency manager JS" may look like this:

    ```js
    // Load JS or CSS script if not loaded already
    DjangoComponents.loadJs('<script src="/abc/xyz/script.js">');
    DjangoComponents.loadCss('<link href="/abc/xyz/style.css">');

    // Or mark one as already-loaded, so it is ignored when
    // we call `loadJs`
    DjangoComponents.markScriptLoaded("js", "/abc/def");
    ```

    Note that `loadJs() / loadCss()` receive whole `<script> / <link>` tags, not just the URL.
    This is because when Django's `Media` class renders JS and CSS, it formats it as `<script>` and `<link>` tags.
    And we allow users to modify how the JS and CSS should be rendered into the `<script>` and `<link>` tags.
    
    So, if users decided to add an extra attribute to their `<script>` tags, e.g. `<script defer src="http://..."></script>`,
    then this way we make sure that the `defer` attribute will be present on the `<script>` tag when
    it is inserted into the DOM at the time of loading the JS script.

5. To be able to fetch component's inlined JS and CSS, django-components adds a URL path under:

    `/components/cache/<str:comp_cls_id>.<str:script_type>/`

    E.g. `/components/cache/MyTable_10bc2c.js/`

    This endpoint takes the component's unique ID, e.g. `MyTable_10bc2c`, and looks up the component's inlined JS or CSS.

---

Thus, with this approach, we ensure that:

1. All JS / CSS dependencies are loaded / executed only once.
2. The approach is compatible with HTML fragments
3. The approach is compatible with JS / CSS variables.
4. Inlined JS / CSS may be post-processed by plugins
