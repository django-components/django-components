from django.template import Context, Template
from pytest_django.asserts import assertHTMLEqual

from django_components import Component, register, types
from django_components.testing import djc_test

from .testutils import PARAMETRIZE_CONTEXT_BEHAVIOR, setup_test_config

setup_test_config()


@djc_test(parametrize=PARAMETRIZE_CONTEXT_BEHAVIOR)
class TestJsVariables:
    def test_js_variables_basic(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="interactive-button">Button</div>
                {% component_js_dependencies %}
            """
            js = """
                $onComponent(({ message }) => {
                    console.log(message);
                });
            """

            def get_js_data(self, args, kwargs, slots, context):
                return {
                    "message": "Hello from JS",
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            """
            <div class="interactive-button" data-djc-id-ca1bc3e="">Button</div>
            <script src="django_components/django_components.min.js"></script>
            <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF9hNjdmOWYuNTQ0MGU0Lmpz",
                    "L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF9hNjdmOWYuanM="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": [["VGVzdENvbXBvbmVudF9hNjdmOWY=", "Y2ExYmMzZQ==", "NTQ0MGU0"]]}</script>
            <script>
                DjangoComponents.manager.registerComponent("TestComponent_a67f9f", ({ message }) => {
                    console.log(message);
                });
            </script>
            <script type="text/javascript">
                (function() {
                    DjangoComponents.manager._loadComponentScripts({"cssUrls__markAsLoaded": [],
                        "jsUrls__markAsLoaded": [],
                        "cssTags__toFetch": [],
                        "jsTags__toFetch": [],
                        "componentJsVars": [["VGVzdENvbXBvbmVudF9hNjdmOWY=", "NTQ0MGU0", "eyJtZXNzYWdlIjogIkhlbGxvIGZyb20gSlMifQ=="]],
                        "componentJsCalls": []});
                })();
            </script>
            """,  # noqa: E501
            rendered,
        )

    def test_js_variables_multiple_instances_different_values(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="box">{{ label }}</div>
            """
            js = """
                $onComponent(({ value }) => {
                    console.log('Value:', value);
                });
            """

            class Kwargs:
                label: str
                value: int

            def get_template_data(self, args, kwargs: Kwargs, slots, context):
                return {"label": kwargs.label}

            def get_js_data(self, args, kwargs: Kwargs, slots, context):
                return {
                    "value": kwargs.value,
                }

        # Render two instances with different values
        template = Template(
            """
            {% load component_tags %}
            {% component "test_component" label="First" value=10 %}
            {% endcomponent %}
            {% component "test_component" label="Second" value=20 %}
            {% endcomponent %}
            {% component_js_dependencies %}
        """
        )

        @register("test_component")
        class TestComponentRegistered(TestComponent):
            pass

        rendered = template.render(Context({}))

        assertHTMLEqual(
            """
            <div class="box" data-djc-id-ca1bc41="">First</div>
            <div class="box" data-djc-id-ca1bc42="">Second</div>

            <script src="django_components/django_components.min.js"></script>
            <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0LmE2ZmY4Mi5qcw==",
                    "L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0LmMwY2FhMS5qcw==",
                    "L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0Lmpz"],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": [["VGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0", "Y2ExYmM0MQ==", "YTZmZjgy"],
                    ["VGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0", "Y2ExYmM0Mg==", "YzBjYWEx"]]}</script>
            <script>
                DjangoComponents.manager.registerComponent("TestComponentRegistered_ce45d4", ({ value }) => {
                    console.log('Value:', value);
                });
            </script>
            <script type="text/javascript">
                (function() {
                    DjangoComponents.manager._loadComponentScripts({"cssUrls__markAsLoaded": [],
                        "jsUrls__markAsLoaded": [],
                        "cssTags__toFetch": [],
                        "jsTags__toFetch": [],
                        "componentJsVars": [["VGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0", "YTZmZjgy", "eyJ2YWx1ZSI6IDEwfQ=="]],
                        "componentJsCalls": []});
                })();
            </script>
            <script type="text/javascript">
                (function() {
                    DjangoComponents.manager._loadComponentScripts({"cssUrls__markAsLoaded": [],
                        "jsUrls__markAsLoaded": [],
                        "cssTags__toFetch": [],
                        "jsTags__toFetch": [],
                        "componentJsVars": [["VGVzdENvbXBvbmVudFJlZ2lzdGVyZWRfY2U0NWQ0", "YzBjYWEx", "eyJ2YWx1ZSI6IDIwfQ=="]],
                        "componentJsCalls": []});
                })();
            </script>
            """,  # noqa: E501
            rendered,
        )

    def test_js_variables_with_complex_data(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="map-container">Map</div>
                {% component_js_dependencies %}
            """
            js = """
                $onComponent(({ lat, lng, zoom, markers }) => {
                    console.log(`Map at ${lat}, ${lng}, zoom: ${zoom}`);
                    console.log(`Markers: ${markers.length}`);
                });
            """

            def get_js_data(self, args, kwargs, slots, context):
                return {
                    "lat": 40.7128,
                    "lng": -74.0060,
                    "zoom": 13,
                    "markers": [
                        {"lat": 40.7128, "lng": -74.0060, "title": "Marker 1"},
                        {"lat": 40.7580, "lng": -73.9855, "title": "Marker 2"},
                    ],
                }

        rendered = TestComponent.render()

        assertHTMLEqual(
            """
            <div class="map-container" data-djc-id-ca1bc3e="">Map</div>
            <script src="django_components/django_components.min.js"></script>
            <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF8yZTY4MDYuN2FjZmI5Lmpz",
                    "L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF8yZTY4MDYuanM="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": [["VGVzdENvbXBvbmVudF8yZTY4MDY=", "Y2ExYmMzZQ==", "N2FjZmI5"]]}</script>
            <script>
                DjangoComponents.manager.registerComponent("TestComponent_2e6806", ({ lat, lng, zoom, markers }) => {
                    console.log(`Map at ${lat}, ${lng}, zoom: ${zoom}`);
                    console.log(`Markers: ${markers.length}`);
                });
            </script>
            <script type="text/javascript">
                (function() {
                    DjangoComponents.manager._loadComponentScripts({"cssUrls__markAsLoaded": [],
                        "jsUrls__markAsLoaded": [],
                        "cssTags__toFetch": [],
                        "jsTags__toFetch": [],
                        "componentJsVars": [["VGVzdENvbXBvbmVudF8yZTY4MDY=", "N2FjZmI5",
                            "eyJsYXQiOiA0MC43MTI4LCAibG5nIjogLTc0LjAwNiwgInpvb20iOiAxMywgIm1hcmtlcnMiOiBbeyJsYXQiOiA0MC43MTI4LCAibG5nIjogLTc0LjAwNiwgInRpdGxlIjogIk1hcmtlciAxIn0sIHsibGF0IjogNDAuNzU4LCAibG5nIjogLTczLjk4NTUsICJ0aXRsZSI6ICJNYXJrZXIgMiJ9XX0="]],
                        "componentJsCalls": []});
                })();
            </script>
            """,
            rendered,
        )

    def test_js_variables_no_data(self, components_settings):
        class TestComponent(Component):
            template: types.django_html = """
                {% load component_tags %}
                <div class="simple">Simple</div>
                {% component_js_dependencies %}
            """
            js = """
                $onComponent(() => {
                    console.log('No data');
                });
            """

            def get_js_data(self, args, kwargs, slots, context):
                return None

        rendered = TestComponent.render()

        assertHTMLEqual(
            """
            <div class="simple" data-djc-id-ca1bc3e="">Simple</div>
            <script src="django_components/django_components.min.js"></script>
            <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF9hOGI3NjYuanM="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": [["VGVzdENvbXBvbmVudF9hOGI3NjY=", "Y2ExYmMzZQ==", null]]}</script>
            <script>
                DjangoComponents.manager.registerComponent("TestComponent_a8b766", () => {
                    console.log('No data');
                });
            </script>
            """,
            rendered,
        )

    def test_js_variables_with_type_hints(self, components_settings):
        from django.template import Context

        class TestComponent(Component):
            class Kwargs:
                user_id: int
                api_key: str

            template: types.django_html = """
                {% load component_tags %}
                <div class="user-widget">User Widget</div>
                {% component_js_dependencies %}
            """
            js = """
                $onComponent(({ user_id, api_key }) => {
                    fetch(`/api/users/${user_id}`, {
                        headers: { 'Authorization': `Bearer ${api_key}` }
                    });
                });
            """

            def get_js_data(self, args, kwargs: Kwargs, slots, context: Context):
                assert isinstance(kwargs, TestComponent.Kwargs)
                return {
                    "user_id": kwargs.user_id,
                    "api_key": kwargs.api_key,
                }

        rendered = TestComponent.render(kwargs={"user_id": 123, "api_key": "secret-key"})

        assertHTMLEqual(
            """
            <div class="user-widget" data-djc-id-ca1bc3e="">User Widget</div>
            <script src="django_components/django_components.min.js"></script>
            <script type="application/json" data-djc>{"cssUrls__markAsLoaded": [],
                "jsUrls__markAsLoaded": ["L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF84MTFlNzAuYmEyZDkxLmpz",
                    "L2NvbXBvbmVudHMvY2FjaGUvVGVzdENvbXBvbmVudF84MTFlNzAuanM="],
                "cssTags__toFetch": [],
                "jsTags__toFetch": [],
                "componentJsVars": [],
                "componentJsCalls": [["VGVzdENvbXBvbmVudF84MTFlNzA=", "Y2ExYmMzZQ==", "YmEyZDkx"]]}</script>
            <script>
                DjangoComponents.manager.registerComponent("TestComponent_811e70", ({ user_id, api_key }) => {
                    fetch(`/api/users/${user_id}`, {
                        headers: { 'Authorization': `Bearer ${api_key}` }
                    });
                });
            </script>
            <script type="text/javascript">
                (function() {
                    DjangoComponents.manager._loadComponentScripts({"cssUrls__markAsLoaded": [],
                        "jsUrls__markAsLoaded": [],
                        "cssTags__toFetch": [],
                        "jsTags__toFetch": [],
                        "componentJsVars": [["VGVzdENvbXBvbmVudF84MTFlNzA=", "YmEyZDkx", "eyJ1c2VyX2lkIjogMTIzLCAiYXBpX2tleSI6ICJzZWNyZXQta2V5In0="]],
                        "componentJsCalls": []});
                })();
            </script>
            """,  # noqa: E501
            rendered,
        )
