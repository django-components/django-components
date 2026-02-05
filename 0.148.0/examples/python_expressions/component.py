from django_components import Component, register, types

DESCRIPTION = "Evaluate Python expressions directly in template using parentheses."


@register("button")
class Button(Component):
    class Kwargs:
        text: str
        disabled: bool = False
        variant: str = "primary"
        size: str | None = None

    def get_template_data(self, args, kwargs, slots, context):
        # Determine button classes based on variant and size
        classes = ["px-4", "py-2", "rounded", "font-medium"]

        if kwargs.variant == "primary":
            classes.extend(["bg-blue-600", "text-white", "hover:bg-blue-700"])
        elif kwargs.variant == "secondary":
            classes.extend(["bg-gray-200", "text-gray-800", "hover:bg-gray-300"])
        elif kwargs.variant == "danger":
            classes.extend(["bg-red-600", "text-white", "hover:bg-red-700"])

        if kwargs.size == "small":
            classes.extend(["text-sm", "px-2", "py-1"])
        elif kwargs.size == "large":
            classes.extend(["text-lg", "px-6", "py-3"])

        if kwargs.disabled:
            classes.extend(["opacity-50", "cursor-not-allowed"])

        return {
            "text": kwargs.text,
            "disabled": kwargs.disabled,
            "classes": " ".join(classes),
        }

    template: types.django_html = """
        <button
            type="button"
            class="{{ classes }}"
            {% if disabled %}disabled{% endif %}
        >
            {{ text }}
        </button>
    """


@register("user_card")
class UserCard(Component):
    class Kwargs:
        username: str
        is_active: bool
        is_admin: bool
        score: int

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "username": kwargs.username,
            "is_active": kwargs.is_active,
            "is_admin": kwargs.is_admin,
            "score": kwargs.score,
            "status": "active" if kwargs.is_active else "inactive",
            "badge_color": "green" if kwargs.is_admin else "blue",
        }

    template: types.django_html = """
        <div class="p-4 border rounded-lg">
            <h3 class="font-bold">{{ username }}</h3>
            <p class="text-sm text-gray-600">Status: {{ status }}</p>
            <p class="text-sm">Score: {{ score }}</p>
            <span class="px-2 py-1 rounded text-xs bg-{{ badge_color }}-100 text-{{ badge_color }}-800">
                {% if is_admin %}Admin{% else %}User{% endif %}
            </span>
        </div>
    """


@register("search_input")
class SearchInput(Component):
    class Kwargs:
        placeholder: str = "Search..."
        required: bool = False
        min_length: int | None = None

    def get_template_data(self, args, kwargs, slots, context):
        attrs = {}
        if kwargs.required:
            attrs["required"] = True
        if kwargs.min_length:
            attrs["minlength"] = kwargs.min_length

        return {
            "placeholder": kwargs.placeholder,
            "attrs": attrs,
        }

    template: types.django_html = """
        <input
            type="search"
            placeholder="{{ placeholder }}"
            class="px-4 py-2 border rounded"
            {% for key, value in attrs.items %}
                {{ key }}="{{ value }}"
            {% endfor %}
        >
    """
