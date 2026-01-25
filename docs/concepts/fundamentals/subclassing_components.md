In larger projects, you might need to write multiple components with similar behavior.
In such cases, you can extract shared behavior into a standalone component class to keep things
[DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself).

When subclassing a component, there's a couple of things to keep in mind:

## Template, JS, and CSS inheritance

When it comes to the pairs:

- [`Component.template`](../../reference/api.md#django_components.Component.template)/[`Component.template_file`](../../reference/api.md#django_components.Component.template_file)
- [`Component.js`](../../reference/api.md#django_components.Component.js)/[`Component.js_file`](../../reference/api.md#django_components.Component.js_file)
- [`Component.css`](../../reference/api.md#django_components.Component.css)/[`Component.css_file`](../../reference/api.md#django_components.Component.css_file)

inheritance follows these rules:

- If a child component class defines either member of a pair (e.g., either [`template`](../../reference/api.md#django_components.Component.template) or [`template_file`](../../reference/api.md#django_components.Component.template_file)), it takes precedence and the parent's definition is ignored completely.
- For example, if a child component defines [`template_file`](../../reference/api.md#django_components.Component.template_file), the parent's [`template`](../../reference/api.md#django_components.Component.template) or [`template_file`](../../reference/api.md#django_components.Component.template_file) will be ignored.
- This applies independently to each pair - you can inherit the JS while overriding the template, for instance.

For example:

```djc_py
class BaseCard(Component):
    template = """
        <div class="card">
            <div class="card-content">{{ content }}</div>
        </div>
    """
    css = """
        .card {
            border: 1px solid gray;
        }
    """
    js = """console.log('Base card loaded');"""

# This class overrides parent's template, but inherits CSS and JS
class SpecialCard(BaseCard):
    template = """
        <div class="card special">
            <div class="card-content">✨ {{ content }} ✨</div>
        </div>
    """

# This class overrides parent's template and CSS, but inherits JS
class CustomCard(BaseCard):
    template_file = "custom_card.html"
    css = """
        .card {
            border: 2px solid gold;
        }
    """
```

## Media inheritance

The [`Component.Media`](../../reference/api.md#django_components.Component.Media) nested class follows Django's media inheritance rules:

- If both parent and child define a `Media` class, the child's media will automatically include both its own and the parent's JS and CSS files.
- This behavior can be configured using the [`extend`](../../reference/api.md#django_components.ComponentMediaInput.extend) attribute in the Media class, similar to Django's forms.
  Read more on this in [Media inheritance](secondary_js_css_files.md#media-inheritance).

For example:

```python
class BaseModal(Component):
    template = "<div>Modal content</div>"

    class Media:
        css = ["base_modal.css"]
        js = ["base_modal.js"]  # Contains core modal functionality

class FancyModal(BaseModal):
    class Media:
        # Will include both base_modal.css/js AND fancy_modal.css/js
        css = ["fancy_modal.css"]  # Additional styling
        js = ["fancy_modal.js"]    # Additional animations

class SimpleModal(BaseModal):
    class Media:
        extend = False  # Don't inherit parent's media
        css = ["simple_modal.css"]  # Only this CSS will be included
        js = ["simple_modal.js"]    # Only this JS will be included
```

## Opt out of inheritance

For the following media attributes, when you don't want to inherit from the parent,
but you also don't need to set the template / JS / CSS to any specific value,
you can set these attributes to `None`.

- [`template`](../../reference/api.md#django_components.Component.template) / [`template_file`](../../reference/api.md#django_components.Component.template_file)
- [`js`](../../reference/api.md#django_components.Component.js) / [`js_file`](../../reference/api.md#django_components.Component.js_file)
- [`css`](../../reference/api.md#django_components.Component.css) / [`css_file`](../../reference/api.md#django_components.Component.css_file)
- [`Media`](../../reference/api.md#django_components.Component.Media) class

For example:

```djc_py
class BaseForm(Component):
    template = "..."
    css = "..."
    js = "..."

    class Media:
        js = ["form.js"]

# Use parent's template and CSS, but no JS
class ContactForm(BaseForm):
    js = None
    Media = None
```

## Regular Python inheritance

All other attributes and methods (including the [`Component.View`](../../reference/api.md#django_components.ComponentView) class and its methods) follow standard Python inheritance rules.

For example:

```djc_py
class BaseForm(Component):
    template = """
        <form>
            {{ form_content }}
            <button type="submit">
                {{ submit_text }}
            </button>
        </form>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "form_content": self.get_form_content(),
            "submit_text": "Submit"
        }

    def get_form_content(self):
        return "<input type='text' name='data'>"

class ContactForm(BaseForm):
    # Extend parent's "context"
    # but override "submit_text"
    def get_template_data(self, args, kwargs, slots, context):
        context = super().get_template_data(args, kwargs, slots, context)
        context["submit_text"] = "Send Message"  
        return context

    # Completely override parent's get_form_content
    def get_form_content(self):
        return """
            <input type='text' name='name' placeholder='Your Name'>
            <input type='email' name='email' placeholder='Your Email'>
            <textarea name='message' placeholder='Your Message'></textarea>
        """
```
