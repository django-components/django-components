from importlib import import_module

from django.http import HttpRequest
from django.utils.safestring import mark_safe

from django_components import Component, types

from .utils import discover_example_modules


class ExamplesIndexPage(Component):
    """Index page that lists all available examples"""

    class Media:
        js = (
            mark_safe(
                '<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp,container-queries"></script>'
            ),
        )

    def get_template_data(self, args, kwargs, slots, context):
        # Get the list of discovered examples
        example_names = discover_example_modules()

        # Convert example names to display format
        examples = []
        for name in sorted(example_names):
            # Convert snake_case to PascalCase (e.g. error_fallback -> ErrorFallback)
            display_name = "".join(word.capitalize() for word in name.split("_"))

            # For the short description, we use the DESCRIPTION variable from the component's module
            description = ""
            try:
                module_name = f"examples.dynamic.{name}.component"
                module = import_module(module_name)
                description = getattr(module, "DESCRIPTION", "")
            except ImportError:
                pass  # Component file may not exist, which is fine

            examples.append(
                {
                    "name": name,  # Original name for URLs
                    "display_name": display_name,  # PascalCase for display
                    "description": description,
                }
            )

        return {
            "examples": examples,
        }

    class View:
        def get(self, request: HttpRequest):
            return ExamplesIndexPage.render_to_response(request=request)

    template: types.django_html = """
        <html>
            <head>
                <title>Django Components Examples</title>
            </head>
            <body class="bg-gray-50">
                <div class="max-w-4xl mx-auto py-12 px-6">
                    <div class="text-center mb-12">
                        <h1 class="text-4xl font-bold text-gray-900 mb-4">
                            Django Components Examples
                        </h1>
                        <p class="text-xl text-gray-600">
                            Interactive examples showcasing django-components features
                        </p>
                    </div>

                        {% if examples %}
                            <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                                {% for example in examples %}
                                    <div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 flex flex-col">
                                        <div class="p-6 flex flex-col flex-grow">
                                            <h2 class="text-xl font-semibold text-gray-900 mb-2">
                                                {{ example.display_name }}
                                            </h2>
                                            <p class="text-gray-600 mb-4 flex-grow">
                                                {{ example.description }}
                                            </p>
                                            <a
                                                href="/examples/{{ example.name }}"
                                                class="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors duration-200 self-start"
                                            >
                                                View Example
                                                <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                                </svg>
                                            </a>
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                    {% else %}
                        <div class="text-center py-12">
                            <div class="text-gray-400 mb-4">
                                <svg class="mx-auto w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                </svg>
                            </div>
                            <h3 class="text-lg font-medium text-gray-900 mb-2">No examples found</h3>
                            <p class="text-gray-600">
                                No example components were discovered in the docs/examples/ directory.
                            </p>
                        </div>
                    {% endif %}

                    <div class="mt-12 text-center">
                        <div class="bg-white rounded-lg shadow-sm p-6">
                            <h3 class="text-lg font-medium text-gray-900 mb-2">
                                About these examples
                            </h3>
                            <p class="text-gray-600 mb-4">
                                These examples are dynamically discovered from the <code class="bg-gray-100 px-2 py-1 rounded text-sm">docs/examples/</code> directory.
                                Each example includes a component definition, live demo page, and tests.
                            </p>
                            <a
                                href="https://github.com/django-components/django-components"
                                class="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                View on GitHub
                                <svg class="ml-1 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                            </a>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    """  # noqa: E501
