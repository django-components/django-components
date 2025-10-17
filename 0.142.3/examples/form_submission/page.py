from django.http import HttpRequest, HttpResponse

from django_components import Component, types


class FormSubmissionPage(Component):
    class Media:
        js = (
            "https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,container-queries",
            "https://unpkg.com/htmx.org@2.0.7",
        )

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>Form Submission Example</title>
            </head>
            <body class="bg-gray-100 p-8" hx-boost="true">
                <div class="max-w-md mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-2xl font-bold mb-4">
                        Self-Contained Form Component
                    </h1>
                    <p class="text-gray-600 mb-6">
                        This form's HTML and submission logic are all
                        handled within a single component file.
                    </p>
                    {% component "contact_form" / %}
                </div>
            </body>
        </html>
    """

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            return FormSubmissionPage.render_to_response(request=request)
