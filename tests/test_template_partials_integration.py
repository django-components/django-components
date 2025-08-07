"""Tests for template_partials integration with django-components."""

import pytest

from django_components.util.django_monkeypatch import is_cls_patched


# Skip the test if template_partials is not installed
template_partials = pytest.importorskip("template_partials")
try:
    from template_partials.templatetags.partials import TemplateProxy
except ImportError:
    TemplateProxy = None


class TestTemplatePartialsIntegration:
    """Test that TemplateProxy is patched when template_partials is installed."""

    @pytest.mark.skipif(TemplateProxy is None, reason="template_partials not available")
    def test_template_proxy_is_patched(self):
        """Test that TemplateProxy has been monkey-patched by django-components."""
        # Check if TemplateProxy was patched
        assert is_cls_patched(TemplateProxy), "TemplateProxy should be patched when template_partials is in INSTALLED_APPS"

    @pytest.mark.skipif(TemplateProxy is None, reason="template_partials not available")
    def test_template_proxy_has_patched_render_method(self):
        """Test that TemplateProxy render method includes our modifications."""
        import inspect

        render_source = inspect.getsource(TemplateProxy.render)

        # Check for key indicators that our patch was applied
        assert 'COMPONENT_IS_NESTED_KEY' in render_source, "TemplateProxy.render should contain component context handling"
        assert 'render_dependencies' in render_source, "TemplateProxy.render should contain dependency rendering"
        assert '_COMPONENT_CONTEXT_KEY' in render_source, "TemplateProxy.render should contain component context key handling"

    @pytest.mark.skipif(TemplateProxy is None, reason="template_partials not available")
    def test_template_proxy_render_method_signature(self):
        """Test that TemplateProxy render method still has the expected signature."""
        import inspect
        
        sig = inspect.signature(TemplateProxy.render)
        params = list(sig.parameters.keys())
        
        # The signature should match the expected TemplateProxy.render signature
        # (self, context, *args, **kwargs)
        assert len(params) >= 2, "TemplateProxy.render should have at least self and context parameters"
        assert params[0] == 'self', "First parameter should be self"
        assert params[1] == 'context', "Second parameter should be context"