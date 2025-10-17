from typing import NamedTuple

from django.http import HttpRequest, HttpResponse

from django_components import Component, get_component_url, register, types

DESCRIPTION = "Handle the entire form submission flow in a single file and without Django's Form class."


@register("thank_you_message")
class ThankYouMessage(Component):
    class Kwargs(NamedTuple):
        name: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {"name": kwargs.name}

    template: types.django_html = """
        <div class="p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg mt-4">
            <p>Thank you for your submission, {{ name }}!</p>
        </div>
    """


@register("contact_form")
class ContactFormComponent(Component):
    def get_template_data(self, args, kwargs: NamedTuple, slots, context):
        # Send the form data to the HTTP handlers of this component
        submit_url = get_component_url(ContactFormComponent)
        return {
            "submit_url": submit_url,
        }

    template: types.django_html = """
        <form hx-post="{{ submit_url }}" hx-target="#thank-you-container" hx-swap="innerHTML" class="space-y-4">
            {% csrf_token %}
            <div>
                <label for="name" class="block text-sm font-medium text-gray-700">
                    Name
                </label>
                <input
                    type="text"
                    name="name"
                    id="name"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                >
            </div>
            <div>
                <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                    Submit
                </button>
            </div>
        </form>
        <div id="thank-you-container"></div>
    """  # noqa: E501

    class View:
        # Submit handler
        def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Access the submitted data
            name = request.POST.get("name", "stranger")

            # Respond with the "thank you" message
            return ThankYouMessage.render_to_response(kwargs={"name": name})
