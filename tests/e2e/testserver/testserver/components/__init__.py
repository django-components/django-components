from django_components import Component, register, types


@register("inner")
class InnerComponent(Component):
    template: types.django_html = """
        Variable: <strong class="inner">{{ variable }}</strong>
    """

    css: types.css = """
        .inner {
            font-size: 4px;
        }
    """

    js: types.js = """
        globalThis.testInnerComponent = 'kapowww!'
    """

    class Defaults:
        variable2 = "default"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "variable": kwargs["variable"],
            "variable2": kwargs["variable2"],
        }

    class Media:
        css = "style.css"
        js = "script.js"


@register("outer")
class OuterComponent(Component):
    template: types.django_html = """
        {% load component_tags %}
        <div class="outer">
            {% component "inner" variable=variable / %}
            {% slot "default" default / %}
        </div>
    """

    css: types.css = """
        .outer {
            font-size: 40px;
        }
    """

    js: types.js = """
        globalThis.testOuterComponent = 'bongo!'
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {"variable": kwargs["variable"]}

    class Media:
        css = ["style.css", "style2.css"]
        js = "script2.js"


@register("other")
class OtherComponent(Component):
    template: types.django_html = """
        XYZ: <strong class="other">{{ variable }}</strong>
    """

    css: types.css = """
        .other {
            display: flex;
        }
    """

    js: types.js = """
        globalThis.testOtherComponent = 'wowzee!'
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {"variable": kwargs["variable"]}

    class Media:
        css = "style.css"
        js = "script.js"


@register("check_script_order_in_js")
class CheckScriptOrderInJs(Component):
    template = "<check_script_order>"

    # We should be able to access the global variables set by the previous components:
    # Scripts:
    # - script.js               - testMsg
    # - script2.js              - testMsg2
    # Components:
    # - InnerComponent         - testInnerComponent
    # - OuterComponent          - testOuterComponent
    # - OtherComponent          - testOtherComponent
    js: types.js = """
        globalThis.checkVars = {
            testInnerComponent,
            testOuterComponent,
            testOtherComponent,
            testMsg,
            testMsg2,
        };
    """


@register("check_script_order_in_media")
class CheckScriptOrderInMedia(Component):
    template = "<check_script_order>"

    class Media:
        js = "check_script_order.js"


# Fragment where the JS and CSS are defined on the Component
@register("frag_comp")
class FragComp(Component):
    template: types.django_html = """
        <div class="frag">
            123
            <span id="frag-text"></span>
        </div>
    """

    js = """
        document.querySelector('#frag-text').textContent = 'xxx';
    """

    css = """
        .frag {
            background: blue;
        }
    """


# Fragment where the JS and CSS are defined on the Media class
@register("frag_media")
class FragMedia(Component):
    template = """
        <div class="frag">
            123
            <span id="frag-text"></span>
        </div>
    """

    class Media:
        js = "fragment.js"
        css = "fragment.css"


# Fragment that defines an AlpineJS component
@register("frag_alpine")
class FragAlpine(Component):
    template = """
    <template x-if="false" data-name="frag">
        <div class="frag">
            123
            <span x-data="frag" x-text="fragVal">
            </span>
        </div>
    </template>
    """

    js = """
        Alpine.data('frag', () => ({
            fragVal: 'xxx',
        }));

        // Now that the component has been defined in AlpineJS, we can "activate" all instances
        // where we use the `x-data="frag"` directive.
        document.querySelectorAll('[data-name="frag"]').forEach((el) => {
            el.setAttribute('x-if', 'true');
        });
    """

    css = """
        .frag {
            background: blue;
        }
    """


@register("alpine_test_in_media")
class AlpineCompInMedia(Component):
    template: types.django_html = """
        <div x-data="alpine_test">
            ALPINE_TEST:
            <div x-text="somevalue"></div>
        </div>
    """

    class Media:
        js = "alpine_test.js"


@register("alpine_test_in_js")
class AlpineCompInJs(Component):
    template: types.django_html = """
        <div x-data="alpine_test">
            ALPINE_TEST:
            <div x-text="somevalue"></div>
        </div>
    """

    js: types.js = """
        document.addEventListener('alpine:init', () => {
            Alpine.data('alpine_test', () => ({
                somevalue: 123,
            }))
        });
    """


@register("css_vars_themed_box")
class CssVarsThemedBox(Component):
    template: types.django_html = """
        <div class="themed-box">Box</div>
    """

    css: types.css = """
        .themed-box {
            background-color: var(--bg_color);
            width: 100px;
            height: 100px;
        }
    """

    def get_css_data(self, args, kwargs, slots, context):
        return {
            "bg_color": kwargs.get("color", "blue"),
        }


@register("css_vars_sized_box")
class CssVarsSizedBox(Component):
    template: types.django_html = """
        <div class="sized-box">Box</div>
    """

    css: types.css = """
        .sized-box {
            width: var(--box_width);
            height: var(--box_height);
            background-color: var(--bg_color);
        }
    """

    def get_css_data(self, args, kwargs, slots, context):
        return {
            "box_width": kwargs.get("width", "100px"),
            "box_height": kwargs.get("height", "100px"),
            "bg_color": kwargs.get("color", "red"),
        }
