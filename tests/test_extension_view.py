from typing import Any, Dict

from django.conf import settings
from django.http import HttpResponse
from django.template import Context, Template
from django.test import Client, SimpleTestCase
from django.urls import path

from django_components import Component, ComponentView, register, types
from django_components.urls import urlpatterns as dc_urlpatterns

from django_components.testing import djc_test
from .testutils import setup_test_config

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

            def get_context_data(self, variable, *args, **kwargs) -> Dict[str, Any]:
                return {"variable": variable}

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

            def get_context_data(self, variable):
                return {"inner_var": variable}

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

            def get_context_data(self, variable):
                return {"inner_var": variable}

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

            def get_context_data(self, variable):
                return {"inner_var": variable}

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

            def get_context_data(self, variable):
                return {"inner_var": variable}

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

            def get_context_data(self, variable):
                return {"inner_var": variable}

            def get(self, request, *args, **kwargs) -> HttpResponse:
                return self.render_to_response(kwargs={"variable": self.name})

        client = CustomClient(urlpatterns=[path("test/", MockComponentRequest("my_comp").as_view())])
        response = client.get("/test/")
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<input type="text" name="variable" value="my_comp">',
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
                return self.render_to_response({"name": "Bob"}, {"second_slot": "Nice to meet you, Bob"})

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
                return self.render_to_response({}, {"test_slot": "<script>alert(1);</script>"})

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
