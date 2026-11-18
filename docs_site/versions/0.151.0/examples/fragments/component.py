from django_components import Component, register, types

DESCRIPTION = "Use HTML fragments (partials) with HTMX, AlpineJS, or plain JS."


@register("simple_fragment")
class SimpleFragment(Component):
    """A simple fragment with JS and CSS."""

    class Kwargs:
        type: str
        message: str = "JavaScript has run."

    template: types.django_html = """
        <div class="frag_simple">
            Fragment with JS and CSS (plain).
            <span id="frag-text"></span>
        </div>
    """

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "message": kwargs.message,
        }

    js: types.js = """
        $onComponent(({ message }, ctx) => {
            document.querySelector('#frag-text').textContent = ' ' + message;
        });
    """

    css: types.css = """
        .frag_simple {
            background: #f0f8ff;
            border: 1px solid #add8e6;
            padding: 1rem;
            border-radius: 5px;
        }
    """


@register("alpine_fragment")
class AlpineFragment(Component):
    """A fragment that defines an AlpineJS component."""

    class Kwargs:
        type: str
        message: str = "Fragment with JS and CSS (AlpineJS)."

    # The fragment is wrapped in `<template x-if="false">` so that we prevent
    # AlpineJS from inserting the HTML right away. Instead, we want to load it
    # only once this component's JS has been loaded.
    template: types.django_html = """
        <template x-if="false" data-name="frag">
            <div
                class="frag_alpine"
                x-data="frag"
                x-text="message"
                x-init="() => {
                    document.querySelectorAll('#loader-alpine').forEach((el) => {
                        el.innerHTML = 'Fragment loaded!';
                        el.disabled = true;
                    });
                }"
            ></div>
        </template>
    """

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "message": kwargs.message,
        }

    js: types.js = """
        $onComponent(({ message }, ctx) => {
            Alpine.data('frag', () => ({
                message: message,
            }));

            document.querySelectorAll('[data-name="frag"]').forEach((el) => {
                el.setAttribute('x-if', 'true');
            });
        });
    """

    css: types.css = """
        .frag_alpine {
            background: #f0fff0;
            border: 1px solid #98fb98;
            padding: 1rem;
            border-radius: 5px;
        }
    """
