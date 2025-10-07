from django.http import HttpRequest, HttpResponse
from django.utils.safestring import mark_safe

from django_components import Component, get_component_url, types

from .component import AlpineFragment, SimpleFragment


class FragmentsPage(Component):
    class Media:
        js = (
            "https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,container-queries",
            mark_safe('<script defer src="https://unpkg.com/alpinejs"></script>'),
        )

    def get_template_data(self, args, kwargs, slots, context):
        # Get URLs that points to the FragmentsPageView.get() method
        alpine_url = get_component_url(FragmentsPage, query={"type": "alpine"})
        js_url = get_component_url(FragmentsPage, query={"type": "js"})
        htmx_url = get_component_url(FragmentsPage, query={"type": "htmx"})

        return {
            "alpine_url": alpine_url,
            "js_url": js_url,
            "htmx_url": htmx_url,
        }

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>HTML Fragments Example</title>
                <script src="https://unpkg.com/htmx.org@2.0.7/dist/htmx.js"></script>
            </head>
            <body
                class="bg-gray-100 p-8"
                data-alpine-url="{{ alpine_url }}"
                data-js-url="{{ js_url }}"
                hx-boost="true"
            >
                <div class="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">
                        HTML Fragments
                    </h1>
                    <p class="text-gray-600 mb-6">
                        This example shows how to load HTML fragments
                        using different client-side techniques.
                    </p>

                    <!-- Vanilla JS -->
                    <div class="mb-8 p-4 border rounded-lg">
                        <h2 class="text-xl font-semibold mb-2">
                            Vanilla JS
                        </h2>
                        <div id="target-js">Initial content</div>
                        <button
                            id="loader-js"
                            class="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                            Load Fragment
                        </button>
                    </div>

                    <!-- AlpineJS -->
                    <div
                        class="mb-8 p-4 border rounded-lg"
                        x-data="{
                            htmlVar: '<div id=\\'target-alpine\\'>Initial content</div>',
                        }"
                    >
                        <h2 class="text-xl font-semibold mb-2">
                            AlpineJS
                        </h2>
                        <div x-html="htmlVar"></div>
                        <button
                            id="loader-alpine"
                            @click="() => {
                                const alpineUrl = document.body.dataset.alpineUrl;
                                fetch(alpineUrl)
                                    .then(r => r.text())
                                    .then(html => {
                                        htmlVar = html;
                                    })
                            }"
                            class="mt-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                        >
                            Load Fragment
                        </button>
                    </div>

                    <!-- HTMX -->
                    <div class="p-4 border rounded-lg">
                        <h2 class="text-xl font-semibold mb-2">
                            HTMX
                        </h2>
                        <div id="target-htmx">Initial content</div>
                        <button
                            id="loader-htmx"
                            hx-get="{{ htmx_url }}"
                            hx-swap="outerHTML"
                            hx-target="#target-htmx"
                            class="mt-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                        >
                            Load Fragment
                        </button>
                    </div>
                </div>

                <script>
                    document.querySelector('#loader-js').addEventListener('click', function () {
                        const jsUrl = document.body.dataset.jsUrl;
                        fetch(jsUrl)
                            .then(response => response.text())
                            .then(html => {
                                document.querySelector('#target-js').outerHTML = html;
                            });
                    });
                </script>
            </body>
        </html>
    """

    class View:
        public = True

        # The same GET endpoint handles rendering either the whole page or a fragment.
        # We use the `type` query parameter to determine which one to render.
        def get(self, request: HttpRequest) -> HttpResponse:
            fragment_type = request.GET.get("type")
            if fragment_type:
                fragment_cls = AlpineFragment if fragment_type == "alpine" else SimpleFragment
                return fragment_cls.render_to_response(
                    request=request,
                    deps_strategy="fragment",
                    kwargs={"type": fragment_type},
                )
            else:
                return FragmentsPage.render_to_response(
                    request=request,
                    deps_strategy="fragment",
                )
