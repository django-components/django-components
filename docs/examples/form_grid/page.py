from django.http import HttpRequest
from django.utils.safestring import mark_safe

from django_components import Component, types


class FormGridPage(Component):
    class Media:
        js = (
            # AlpineJS
            mark_safe('<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>'),
            # TailwindCSS
            "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4",
        )

    template: types.django_html = """
      <html>
        <head>
          <title>FormGrid</title>
          <script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp,container-queries"></script>
        </head>
        <body>
          <div x-data="{
            onSubmit: () => {
              alert('Submitted!');
            }
          }">
            <div class="prose-xl p-6">
              <h3>Submit form</h3>
            </div>

            {% component "form_grid"
              attrs:class="pb-4 px-4 pt-6 sm:px-6 lg:px-8 flex-auto flex flex-col"
              attrs:style="max-width: 600px;"
              attrs:@submit.prevent="onSubmit"
            %}
              {% fill "field:project" %}
                <input
                  name="project"
                  required
                  class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                >
              {% endfill %}

              {% fill "field:option" %}
                <select
                  name="option"
                  required
                  class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:max-w-xs sm:text-sm sm:leading-6"
                >
                  <option value="1">Option 1</option>
                  <option value="2">Option 2</option>
                  <option value="3">Option 3</option>
                </select>
              {% endfill %}

              {# Defined both label and field because label name is different from field name #}
              {% fill "label:description" %}
                {% component "form_grid_label" field_name="description" title="Marvelous description" / %}
              {% endfill %}
              {% fill "field:description" %}
                <textarea
                  name="description"
                  id="description"
                  rows="5"
                  class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                ></textarea>
              {% endfill %}

              {% fill "append" %}
                <div class="flex justify-end items-center gap-x-6 border-t border-gray-900/10 py-4">
                  <button type="submit" class="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">
                    Submit
                  </button>
                  <button type="button" class="text-sm font-semibold leading-6 text-gray-900">
                    Cancel
                  </button>
                </div>
              {% endfill %}
            {% endcomponent %}
          </div>
        </body>
      </html>
    """  # noqa: E501

    class View:
        def get(self, request: HttpRequest):
            return FormGridPage.render_to_response(request=request)
