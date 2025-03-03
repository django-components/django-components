from django_components.util.component_highlight import apply_component_highlight, COLORS

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestComponentHighlight:
    def test_component_highlight(self):
        # Test component highlighting
        test_html = "<div>Test content</div>"
        component_name = "TestComponent"
        result = apply_component_highlight("component", test_html, component_name)

        # Check that the output contains the component name
        assert component_name in result
        # Check that the output contains the original HTML
        assert test_html in result
        # Check that the component colors are used
        assert COLORS["component"].text_color in result
        assert COLORS["component"].border_color in result

    def test_slot_highlight(self):
        # Test slot highlighting
        test_html = "<span>Slot content</span>"
        slot_name = "content-slot"
        result = apply_component_highlight("slot", test_html, slot_name)

        # Check that the output contains the slot name
        assert slot_name in result
        # Check that the output contains the original HTML
        assert test_html in result
        # Check that the slot colors are used
        assert COLORS["slot"].text_color in result
        assert COLORS["slot"].border_color in result
