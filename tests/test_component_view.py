from typing import Any

import pytest
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template import Context, Template
from django.test import Client, SimpleTestCase
from django.urls import path

from django_components import Component, ComponentView, get_component_url, register, types
from django_components.urls import urlpatterns as dc_urlpatterns
from django_components.util.misc import format_url

from django_components.testing import djc_test
from .testutils import setup_test_config

# DO NOT REMOVE!
#
# This is intentionally defined before `setup_test_config()` in order to test that
# the URL extension works even before the Django has been set up.
#
# Because if we define the component before `django.setup()`, then we store it in
# event queue, and will register it when `AppConfig.ready()` is finally called.
#
# This test relies on the "url" extension calling `add_extension_urls()` from within
# the `on_component_class_created()` hook.
class ComponentBeforeReady(Component):
    class View:
        public = True

    template = "Hello"


setup_test_config({"autodiscover": False})


class CustomClient(Client):
    def __init__(self, urlpatterns=None, *args, **kwargs):
        import types

        if urlpatterns:
            urls_module = types.ModuleType("urls")
            urls_module.urlpatterns = urlpatterns + dc_urlpatterns  # type: ignore
            settings.ROOT_URLCONF = urls_module
        else:
            settings.ROOT_URLCONF = __name__
        settings.SECRET_KEY = "secret"  # noqa
        super().__init__(*args, **kwargs)


@djc_test
class TestComponentAsView(SimpleTestCase):
    def test_render_component_from_template(self):
        @register("testcomponent")
        class MockComponentRequest(Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ variable }}">
                    <input type="submit">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"variable": kwargs["variable"]}

        def render_template_view(request):
            template = Template(
                """
                {% load component_tags %}
                {% component "testcomponent" variable="TEMPLATE" %}{% endcomponent %}
                """
            )
            return HttpResponse(template.render(Context({})))

        client = CustomClient(urlpatterns=[path("test_template/", render_template_view)])
        response = client.get("/test_template/")
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="TEMPLATE">',
            response.content.decode(),
        )

    def test_get_request(self):
        class MockComponentRequest(Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"inner_var": kwargs["variable"]}

            class View(ComponentView):
                def get(self, request, *args, **kwargs) -> HttpResponse:
                    return self.component.render_to_response(kwargs={"variable": "GET"})

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.get("/test/")
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="GET">',
            response.content.decode(),
        )

    def test_get_request_shortcut(self):
        class MockComponentRequest(Component):
            template = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"inner_var": kwargs["variable"]}

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(kwargs={"variable": "GET"})

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.get("/test/")
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="GET">',
            response.content.decode(),
        )

    def test_post_request(self):
        class MockComponentRequest(Component):
            template: types.django_html = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"inner_var": kwargs["variable"]}

            class View(ComponentView):
                def post(self, request, *args, **kwargs) -> HttpResponse:
                    variable = request.POST.get("variable")
                    return self.component.render_to_response(kwargs={"variable": variable})

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.post("/test/", {"variable": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="POST">',
            response.content.decode(),
        )

    def test_post_request_shortcut(self):
        class MockComponentRequest(Component):
            template: types.django_html = """
                <form method="post">
                    {% csrf_token %}
                    <input type="text" name="variable" value="{{ inner_var }}">
                    <input type="submit">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"inner_var": kwargs["variable"]}

            def post(self, request, *args, **kwargs) -> HttpResponse:
                variable = request.POST.get("variable")
                return self.render_to_response(kwargs={"variable": variable})

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest.as_view())])
        response = client.post("/test/", {"variable": "POST"})
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="POST">',
            response.content.decode(),
        )

    def test_instantiate_component(self):
        class MockComponentRequest(Component):
            template = """
                <form method="post">
                    <input type="text" name="variable" value="{{ inner_var }}">
                </form>
                """

            def get_template_data(self, args, kwargs, slots, context):
                return {"inner_var": kwargs["variable"]}

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(kwargs={"variable": self.name})

        view = MockComponentRequest.as_view()
        client = CustomClient(urlpatterns=[path("test/", view)])
        response = client.get("/test/")
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="MockComponentRequest">',
            response.content.decode(),
        )

    def test_replace_slot_in_view(self):
        class MockComponentSlot(Component):
            template = """
                {% load component_tags %}
                <div>
                {% slot "first_slot" %}
                    Hey, I'm {{ name }}
                {% endslot %}
                {% slot "second_slot" %}
                {% endslot %}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(
                    context={"name": "Bob"},
                    slots={"second_slot": "Nice to meet you, Bob"},
                )

        client = CustomClient(urlpatterns=[path("test_slot/", MockComponentSlot.as_view())])
        response = client.get("/test_slot/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hey, I'm Bob",
            response.content,
        )
        self.assertIn(
            b"Nice to meet you, Bob",
            response.content,
        )

    def test_replace_slot_in_view_with_insecure_content(self):
        class MockInsecureComponentSlot(Component):
            template = """
                {% load component_tags %}
                <div>
                {% slot "test_slot" %}
                {% endslot %}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(
                    context={},
                    slots={"test_slot": "<script>alert(1);</script>"},
                )

        client = CustomClient(urlpatterns=[path("test_slot_insecure/", MockInsecureComponentSlot.as_view())])
        response = client.get("/test_slot_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )

    def test_replace_context_in_view(self):
        class TestComponent(Component):
            template = """
                {% load component_tags %}
                <div>
                Hey, I'm {{ name }}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"name": "Bob"})

        client = CustomClient(urlpatterns=[path("test_context_django/", TestComponent.as_view())])
        response = client.get("/test_context_django/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Hey, I'm Bob",
            response.content,
        )

    def test_replace_context_in_view_with_insecure_content(self):
        class MockInsecureComponentContext(Component):
            template = """
                {% load component_tags %}
                <div>
                {{ variable }}
                </div>
                """

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response({"variable": "<script>alert(1);</script>"})

        client = CustomClient(urlpatterns=[path("test_context_insecure/", MockInsecureComponentContext.as_view())])
        response = client.get("/test_context_insecure/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b"<script>",
            response.content,
        )

    def test_component_url(self):
        class TestComponent(Component):
            template = "Hello"

            class View:
                public = True

        # Check if the URL is correctly generated
        component_url = get_component_url(TestComponent)
        assert component_url == f"/components/ext/view/components/{TestComponent.class_id}/"

        component_url2 = get_component_url(TestComponent, query={"foo": "bar"}, fragment="baz")
        assert component_url2 == f"/components/ext/view/components/{TestComponent.class_id}/?foo=bar#baz"

        # Check that the query and fragment are correctly escaped
        component_url3 = get_component_url(TestComponent, query={"f'oo": "b ar&ba'z"}, fragment='q u"x')
        assert component_url3 == f"/components/ext/view/components/{TestComponent.class_id}/?f%27oo=b+ar%26ba%27z#q%20u%22x"  # noqa: E501

        # Merges query params from original URL
        component_url4 = format_url(
            "/components/ext/view/components/123?foo=123&bar=456#abc",
            query={"foo": "new", "baz": "new2"},
            fragment='xyz',
        )
        assert component_url4 == "/components/ext/view/components/123?foo=new&bar=456&baz=new2#xyz"

    def test_public_url(self):
        did_call_get = False
        did_call_post = False

        class TestComponent(Component):
            template = "Hello"

            class View:
                public = True

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
        assert component_url == f"/components/ext/view/components/{TestComponent.class_id}/"

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

            class View:
                public = False

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
        component_url = f"/components/ext/view/components/{TestComponent.class_id}/"

        client = Client()
        response = client.get(component_url)
        assert response.status_code == 404
        assert not did_call_get
