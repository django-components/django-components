import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


def _import_components():
    from docs.examples.form_submission.component import ContactFormComponent, ThankYouMessage  # noqa: PLC0415

    registry.register("contact_form", ContactFormComponent)
    registry.register("thank_you_message", ThankYouMessage)


@pytest.mark.django_db
@djc_test
class TestFormSubmission:
    def test_form_renders(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "contact_form" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert 'hx-post="' in rendered
        assert '<div id="thank-you-container" data-djc-id-ca1bc3f=""></div>' in rendered
        assert "Thank you" not in rendered

    def test_form_submission(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "thank_you_message" name="John Doe" / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))
        assert "Thank you for your submission, John Doe!" in rendered
        assert '<div id="thank-you-container"></div>' not in rendered
