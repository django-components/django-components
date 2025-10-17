import pytest
from django.template import Context, Template

from django_components import registry, types
from django_components.testing import djc_test


def _import_components():
    from docs.examples.ab_testing.component import OfferCard, OfferCardNew, OfferCardOld  # noqa: PLC0415

    registry.register("offer_card", OfferCard)
    registry.register("offer_card_old", OfferCardOld)
    registry.register("offer_card_new", OfferCardNew)


@pytest.mark.django_db
@djc_test
class TestABTesting:
    def test_renders_old_version(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "offer_card" use_new_version=False savings_percent=10 / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "Special Offer!" in rendered
        assert "10% off" in rendered
        assert "FLASH SALE!" not in rendered

    def test_renders_new_version(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "offer_card" use_new_version=True savings_percent=25 / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        assert "FLASH SALE!" in rendered
        assert "25% off" in rendered
        assert "Special Offer!" not in rendered

    def test_renders_random_version(self):
        _import_components()
        template_str: types.django_html = """
            {% load component_tags %}
            {% component "offer_card" savings_percent=15 / %}
        """
        template = Template(template_str)
        rendered = template.render(Context({}))

        is_new = "FLASH SALE!" in rendered and "15% off" in rendered
        is_old = "Special Offer!" in rendered and "15% off" in rendered

        # Check that one and only one of the versions is rendered
        assert (is_new and not is_old) or (is_old and not is_new)
