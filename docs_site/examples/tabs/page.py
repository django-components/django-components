from django.http import HttpRequest, HttpResponse

from django_components import Component, types


class TabsPage(Component):
    template: types.django_html = """
      <html>
        <head>
          <title>Tabs</title>
        </head>
        <body>
          {% component "Tablist"
            id="optional-tablist-id"
            name="Bonza tablist"
            container_attrs:class="optional-container-attrs"
            tablist_attrs:class="optional-tablist-attrs"
            tab_attrs:class="optional-tab-attrs"
            tabpanel_attrs:class="optional-panel-attrs"
          %}
            {% component "Tab" id="optional-tab-id" header="I'm a tab!" %}
              {% lorem %}
            {% endcomponent %}
            {% component "Tab" header="I'm also a tab!" %}
              <p>{% lorem %}</p>
              <p>{% lorem %}</p>
            {% endcomponent %}
            {% component "Tab" header="I am a gorilla!" %}
              <p>{% lorem %}</p>
              <p>I wonder if anyone got the Monty Python reference. 🤔</p>
            {% endcomponent %}
          {% endcomponent %}
        </body>
      </html>
    """

    class View:
        def get(self, request: HttpRequest) -> HttpResponse:
            return TabsPage.render_to_response(request=request)
