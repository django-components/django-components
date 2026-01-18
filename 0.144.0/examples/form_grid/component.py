from typing import Any, Dict, List, Optional, Set, Tuple

from django_components import Component, Slot, register, types

DESCRIPTION = "Form that automatically arranges fields in a grid and generates labels."


@register("form_grid")
class FormGrid(Component):
    """Form that automatically arranges fields in a grid and generates labels."""

    class Kwargs:
        editable: bool = True
        method: str = "post"
        form_content_attrs: Optional[dict] = None
        attrs: Optional[dict] = None

    def get_template_data(self, args, kwargs: Kwargs, slots: Dict[str, Slot], context):
        fields = prepare_form_grid(slots)

        return {
            "form_content_attrs": kwargs.form_content_attrs,
            "method": kwargs.method,
            "editable": kwargs.editable,
            "attrs": kwargs.attrs,
            "fields": fields,
        }

    template: types.django_html = """
        <form
            {% if submit_href and editable %} action="{{ submit_href }}" {% endif %}
            method="{{ method }}"
            {% html_attrs attrs %}
        >
            {% slot "prepend" / %}

            <div {% html_attrs form_content_attrs %}>
                {# Generate a grid of fields and labels out of given slots #}
                <div class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-2 items-center">
                    {% for field_name, label in fields %}
                        {{ label }}
                        {% slot name=field_name / %}
                    {% endfor %}
                </div>
            </div>

            {% slot "append" / %}
        </form>
    """


# Users of this component can define form fields as slots.
#
# For example:
# ```django
# {% component "form" %}
#   {% fill "field:field_1" / %}
#     <textarea name="field_1" />
#   {% endfill %}
#   {% fill "field:field_2" / %}
#     <select name="field_2">
#       <option value="1">Option 1</option>
#       <option value="2">Option 2</option>
#     </select>
#   {% endfill %}
# {% endcomponent %}
# ```
#
# The above will automatically generate labels for the fields,
# and the form will be aligned with a grid.
#
# To explicitly define a label, use `label:<field_name>` slot name.
#
# For example:
# ```django
# {% component "form" %}
#   {% fill "label:field_1" / %}
#     <label for="field_1">Label 1</label>
#   {% endfill %}
#   {% fill "field:field_1" / %}
#     <textarea name="field_1" />
#   {% endfill %}
# {% endcomponent %}
# ```
def prepare_form_grid(slots: Dict[str, Slot]):
    used_labels: Set[str] = set()
    unused_labels: Set[str] = set()
    fields: List[Tuple[str, str]] = []

    for slot_name in slots:
        # Case: Label slot
        is_label = slot_name.startswith("label:")
        if is_label and slot_name not in used_labels:
            unused_labels.add(slot_name)
            continue

        # Case: non-field, non-label slot
        is_field = slot_name.startswith("field:")
        if not is_field:
            continue

        # Case: Field slot
        field_name = slot_name.split(":", 1)[1]
        label_slot_name = f"label:{field_name}"
        label = None
        if label_slot_name in slots:
            # Case: Component user explicitly defined how to render the label
            label_slot: Slot[Any] = slots[label_slot_name]
            label = label_slot()

            unused_labels.discard(label_slot_name)
            used_labels.add(slot_name)
        else:
            # Case: Component user didn't explicitly define how to render the label
            #       We will create the label for the field automatically
            label = FormGridLabel.render(
                kwargs=FormGridLabel.Kwargs(field_name=field_name),  # type: ignore[call-arg]
                deps_strategy="ignore",
            )

        fields.append((slot_name, label))

    if unused_labels:
        raise ValueError(f"Unused labels: {unused_labels}")

    return fields


@register("form_grid_label")
class FormGridLabel(Component):
    template: types.django_html = """
        <label for="{{ field_name }}" class="font-semibold text-gray-700">
            {{ title }}
        </label>
    """

    class Kwargs:
        field_name: str
        title: Optional[str] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if kwargs.title:
            title = kwargs.title
        else:
            title = kwargs.field_name.replace("_", " ").replace("-", " ").title()

        return {
            "field_name": kwargs.field_name,
            "title": title,
        }
