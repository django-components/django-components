from typing import NamedTuple

from django_components import Component, register, types

DESCRIPTION = "Use HTML fragments (partials) with HTMX, AlpineJS, or plain JS."


@register("simple_fragment")
class SimpleFragment(Component):
    """A simple fragment with JS and CSS."""

    class Kwargs(NamedTuple):
        type: str

    template: types.django_html = """
        <div class="frag_simple">
            Fragment with JS and CSS (plain).
            <span id="frag-text"></span>
        </div>
    """

    js: types.js = """
        document.querySelector('#frag-text').textContent = ' JavaScript has run.';
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

    class Kwargs(NamedTuple):
        type: str

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

    js: types.js = """
        Alpine.data('frag', () => ({
            message: 'Fragment with JS and CSS (AlpineJS).',
        }));

        document.querySelectorAll('[data-name="frag"]').forEach((el) => {
            el.setAttribute('x-if', 'true');
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
