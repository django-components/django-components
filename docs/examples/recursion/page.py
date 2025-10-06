from django.http import HttpRequest, HttpResponse
from django.utils.safestring import mark_safe

from django_components import Component, types


class RecursionPage(Component):
    class Media:
        js = (
            mark_safe(
                '<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp,container-queries"></script>'
            ),
        )

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>Recursion Example</title>
                {{ component.media.render_js }}
            </head>
            <body class="bg-gray-100 p-8">
                <div class="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">Recursion</h1>
                    <p class="text-gray-600 mb-6">
                        Django components easily handles even deeply nested components.
                    </p>
                    {% component "recursion" / %}
                </div>
            </body>
        </html>
    """

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            return RecursionPage.render_to_response(request=request)
