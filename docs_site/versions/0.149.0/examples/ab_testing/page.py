from django.http import HttpRequest, HttpResponse

from django_components import Component, types


class ABTestingPage(Component):
    class Media:
        js = ("https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,container-queries",)

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>A/B Testing Example</title>
            </head>
            <body class="bg-gray-100 p-8">
                <div class="max-w-2xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">
                        A/B Testing Components
                    </h1>
                    <p class="text-gray-600 mb-6">
                        This example shows how a single component can render different versions
                        based on a parameter (or a random choice), perfect for A/B testing.
                    </p>

                    <div class="mb-8">
                        <h2 class="text-xl font-semibold mb-2">
                            Variant A (Old Offer)
                        </h2>
                        <p class="text-sm text-gray-500 mb-2">
                            Rendered with <code>use_new_version=False</code>
                        </p>
                        {% component "offer_card" use_new_version=False savings_percent=10 / %}
                    </div>

                    <div>
                        <h2 class="text-xl font-semibold mb-2">
                            Variant B (New Offer)
                        </h2>
                        <p class="text-sm text-gray-500 mb-2">
                            Rendered with <code>use_new_version=True</code>
                        </p>
                        {% component "offer_card" use_new_version=True savings_percent=25 / %}
                    </div>

                    <div class="mt-8">
                        <h2 class="text-xl font-semibold mb-2">
                            Variant C (Random)
                        </h2>
                        <p class="text-sm text-gray-500 mb-2">
                            Rendered without <code>use_new_version</code>.
                            Reload the page to see a different version.
                        </p>
                        {% component "offer_card" savings_percent=15 / %}
                    </div>
                </div>
            </body>
        </html>
    """

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            return ABTestingPage.render_to_response(request=request)
