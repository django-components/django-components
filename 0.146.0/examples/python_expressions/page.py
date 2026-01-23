from dataclasses import dataclass
from typing import List

from django.http import HttpRequest, HttpResponse

from django_components import Component, types


@dataclass
class User:
    username: str
    status: str
    role: str
    points: int
    is_admin: bool = False

    def __post_init__(self):
        # Derive is_admin from role if not explicitly set to True
        if not self.is_admin:
            self.is_admin = self.role == "admin"


@dataclass
class Item:
    title: str


class PythonExpressionsPage(Component):
    @dataclass
    class Kwargs:
        editable: bool
        my_user: User
        bonus_points: int
        name: str
        items: List[Item]
        config: dict

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "editable": kwargs.editable,
            "my_user": kwargs.my_user,
            "bonus_points": kwargs.bonus_points,
            "name": kwargs.name,
            "items": kwargs.items,
            "items_len": len(kwargs.items),
            "config": kwargs.config,
        }

    class Media:
        js = ("https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,container-queries",)

    template: types.django_html = """
        {% load component_tags %}
        <html>
            <head>
                <title>Python Expressions Example</title>
            </head>
            <body class="bg-gray-100 p-8">
                <div class="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow-md">
                    <h1 class="text-3xl font-bold mb-4">
                        Python Expressions in Template Tags
                    </h1>
                    <p class="text-gray-600 mb-6">
                        Python expressions allow you to evaluate Python code directly in template tag attributes
                        by wrapping the expression in parentheses. This provides a Vue/React-like experience
                        for writing component templates.
                    </p>

                    <div class="mb-8">
                        <h2 class="text-2xl font-semibold mb-4">
                            Basic Examples
                        </h2>

                        <div class="mb-8">
                            <h3 class="text-lg font-medium mb-2">
                                Negating a boolean
                            </h3>
                            <div class="text-sm text-gray-500 mb-2">
                            <pre
                                class="text-sm bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "button"
  text="Submit"
  disabled=(not editable)
/ %}{% endverbatim %}</code></pre>
                            </div>
                            <div class="mb-2">
                                Evaluates to <code class="text-sm text-gray-500 mb-2">True</code>
                                when <code class="text-sm text-gray-500 mb-2">editable</code>
                                is <code class="text-sm text-gray-500 mb-2">False</code>
                            </div>
                            <div class="space-x-2">
                                {% component "button" text="Submit" disabled=(not editable) / %}
                            </div>
                        </div>

                        <div class="mb-8">
                            <h3 class="text-lg font-medium mb-2">
                                Conditional expressions
                            </h3>
                            <div class="text-sm text-gray-500 mb-2">
                            <pre
                                class="text-sm bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "button"
  text="Delete"
  variant=(my_user.is_admin and 'danger' or 'primary')
/ %}{% endverbatim %}</code></pre>
                            </div>
                            <div class="mb-2">
                                Ternary-like expression that evaluates to <code class="text-sm text-gray-500 mb-2">'danger'</code>
                                when <code class="text-sm text-gray-500 mb-2">my_user.is_admin</code> is <code class="text-sm text-gray-500 mb-2">True</code>,
                                otherwise <code class="text-sm text-gray-500 mb-2">'primary'</code>
                            </div>
                            <div class="space-x-2">
                                {% component "button" text="Delete" variant=(my_user.is_admin and 'danger' or 'primary') / %}
                            </div>
                        </div>

                        <div class="mb-8">
                            <h3 class="text-lg font-medium mb-2">
                                Method calls and attribute access
                            </h3>
                            <div class="text-sm text-gray-500 mb-2">
                            <pre
                                class="text-sm bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "button"
  text="Click Me"
  size=(name.upper() if name else 'medium')
/ %}{% endverbatim %}</code></pre>
                            </div>
                            <div class="mb-2">
                                Uses string methods (<code class="text-sm text-gray-500 mb-2">.upper()</code>) and conditionals
                                to transform the <code class="text-sm text-gray-500 mb-2">name</code> value
                            </div>
                            <div class="space-x-2">
                                {% component "button" text="Click Me" size=(name.upper() if name else 'medium') / %}
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h2 class="text-2xl font-semibold mb-4">
                            Complex Examples
                        </h2>

                        <div class="mb-8">
                            <h3 class="text-lg font-medium mb-2">
                                Multiple Python expressions
                            </h3>
                            <div class="text-sm text-gray-500 mb-2">
                            <pre
                                class="text-sm bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "user_card"
    username=my_user.username
    is_active=(my_user.status == 'active')
    is_admin=(my_user.role == 'admin')
    score=(my_user.points + bonus_points)
/ %}{% endverbatim %}</code></pre>
                            </div>
                            <div class="mb-2">
                                Using Python expressions for multiple attributes with comparisons and arithmetic
                            </div>
                            <div class="space-y-2">
                                {% component "user_card"
                                    username=my_user.username
                                    is_active=(my_user.status == 'active')
                                    is_admin=(my_user.role == 'admin')
                                    score=(my_user.points + bonus_points)
                                / %}
                            </div>
                        </div>

                        <div class="mb-8">
                            <h3 class="text-lg font-medium mb-2">
                                List and dictionary operations
                            </h3>
                            <div class="text-sm text-gray-500 mb-2">
                            <pre
                                class="text-sm bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "button"
    text=(items[0].title if items else 'No Items')
    disabled=(items_len == 0)
    variant=(config.get('button_style', 'primary'))
/ %}{% endverbatim %}</code></pre>
                            </div>
                            <div class="mb-2">
                                Python expressions work with lists, dicts, and other data structures
                            </div>
                            <div class="space-x-2">
                                {% component "button"
                                    text=(items[0].title if items else 'No Items')
                                    disabled=(items_len == 0)
                                    variant=(config.get('button_style', 'primary'))
                                / %}
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h2 class="text-2xl font-semibold mb-4">
                            Comparison with Alternatives
                        </h2>

                        <div class="mb-8 p-4 bg-gray-50 rounded">
                            <h3 class="text-lg font-medium mb-2">
                                Without Python expressions (verbose)
                            </h3>
                            <p class="text-sm text-gray-600 mb-2">
                                You would need to compute values in <code>get_template_data()</code>:
                            </p>
                            <pre
                                class="text-xs bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}def get_template_data(self, args, kwargs, slots, context):
    return {
        "disabled": not kwargs["editable"],
        "variant": "danger" if kwargs["my_user"].is_admin else "primary",
    }{% endverbatim %}</code></pre>
                        </div>

                        <div class="mb-8 p-4 bg-gray-50 rounded">
                            <h3 class="text-lg font-medium mb-2">
                                With Python expressions (concise)
                            </h3>
                            <p class="text-sm text-gray-600 mb-2">
                                Evaluate directly in the template:
                            </p>
                            <pre
                                class="text-xs bg-gray-800 text-gray-100 p-2 rounded overflow-x-auto"
                            ><code>{% verbatim %}{% component "button"
    disabled=(not editable)
    variant=(my_user.is_admin and 'danger' or 'primary')
/ %}{% endverbatim %}</code></pre>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h2 class="text-2xl font-semibold mb-4">
                            Best Practices
                        </h2>
                        <ul class="list-disc list-inside space-y-2 text-gray-700">
                            <li>Use Python expressions for simple transformations and conditionals</li>
                            <li>Keep complex business logic in <code>get_template_data()</code> or views</li>
                            <li>Python expressions have access to the template context</li>
                            <li>Expressions are cached for performance</li>
                        </ul>
                    </div>
                </div>
            </body>
        </html>
    """  # noqa: E501

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            # Set up example context data
            kwargs = PythonExpressionsPage.Kwargs(
                editable=False,
                my_user=User(username="johndoe", status="active", role="admin", points=150),
                bonus_points=25,
                name="large",
                items=[Item(title="First Item"), Item(title="Second Item")],
                config={"button_style": "secondary"},
            )
            return PythonExpressionsPage.render_to_response(request=request, kwargs=kwargs)
