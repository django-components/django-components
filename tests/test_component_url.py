from typing import Any

import pytest
from django.http import HttpRequest
from django.test import Client

from django_components import Component, get_component_url
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


@djc_test
class TestComponentUrl:
    def test_public_url(self):
        did_call_get = False
        did_call_post = False

        class TestComponent(Component):
            template = "Hello"

            class Url:
                public = True

            class View:
                def get(self, request: HttpRequest, **kwargs: Any):
                    nonlocal did_call_get
                    did_call_get = True

                    component: Component = self.component  # type: ignore[attr-defined]
                    return component.render_to_response()

                def post(self, request: HttpRequest, **kwargs: Any):
                    nonlocal did_call_post
                    did_call_post = True

                    component: Component = self.component  # type: ignore[attr-defined]
                    return component.render_to_response()

        # Check if the URL is correctly generated
        component_url = get_component_url(TestComponent)
        comp_class_hash = TestComponent._class_hash.split("_")[-1]
        assert component_url == f"/components/ext/url/components/{comp_class_hash}/"

        client = Client()
        response = client.get(component_url)
        assert response.status_code == 200
        assert response.content == b"Hello"
        assert did_call_get

        response = client.post(component_url)
        assert response.status_code == 200
        assert response.content == b"Hello"
        assert did_call_get

    def test_non_public_url(self):
        did_call_get = False

        class TestComponent(Component):
            template = "Hi"

            class Url:
                public = False

            class View:
                def get(self, request: HttpRequest, **attrs: Any):
                    nonlocal did_call_get
                    did_call_get = True

                    component: Component = self.component  # type: ignore[attr-defined]
                    return component.render_to_response()

        # Attempt to get the URL should raise RuntimeError
        with pytest.raises(
            RuntimeError,
            match="Component URL is not available - Component is not public",
        ):
            get_component_url(TestComponent)

        # Even calling the URL directly should raise an error
        comp_class_hash = TestComponent._class_hash.split("_")[-1]
        component_url = f"/components/ext/url/components/{comp_class_hash}/"

        client = Client()
        response = client.get(component_url)
        assert response.status_code == 404
        assert not did_call_get
