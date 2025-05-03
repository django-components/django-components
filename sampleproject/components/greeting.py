from django_components import Component, register, types


@register("greeting")
class Greeting(Component):
    template: types.django_html = """
        <div id="greeting">Hello, {{ name }}!</div>
        {% slot "message" %}{% endslot %}
    """

    css: types.css = """
        #greeting {
            display: inline-block;
            color: blue;
            font-size: 2em;
        }
    """

    js: types.js = """
        document.getElementById("greeting").addEventListener("click", (event) => {
            alert("Hello!");
        });
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {"name": kwargs["name"]}

    class View:
        def get(self, request, *args, **kwargs):
            slots = {"message": "Hello, world!"}
            return Greeting.render_to_response(
                request=request,
                slots=slots,
                kwargs={
                    "name": request.GET.get("name", ""),
                },
            )
