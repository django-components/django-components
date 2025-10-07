import random
from typing import NamedTuple, Optional

from django_components import Component, register, types

DESCRIPTION = "Dynamically render different component versions. Use for A/B testing, phased rollouts, etc."


@register("offer_card_old")
class OfferCardOld(Component):
    class Kwargs(NamedTuple):
        savings_percent: int

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "savings_percent": kwargs.savings_percent,
        }

    template: types.django_html = """
        <div class="p-4 border rounded-lg bg-gray-100">
            <h3 class="text-lg font-bold text-gray-800">
                Special Offer!
            </h3>
            <p class="text-gray-600">
                Get {{ savings_percent }}% off on your next purchase.
            </p>
        </div>
    """


@register("offer_card_new")
class OfferCardNew(OfferCardOld):
    template: types.django_html = """
        <div class="p-6 border-2 border-dashed border-blue-500 rounded-lg bg-blue-50 text-center">
            <h3 class="text-xl font-extrabold text-blue-800 animate-pulse">
                FLASH SALE!
            </h3>
            <p class="text-blue-600">
                Exclusive Offer: {{ savings_percent }}% off everything!
            </p>
        </div>
    """


@register("offer_card")
class OfferCard(Component):
    class Kwargs(NamedTuple):
        savings_percent: int
        use_new_version: Optional[bool] = None

    def on_render(self, context, template):
        # Pass all kwargs to the child component
        kwargs_for_child = self.kwargs._asdict()
        use_new = kwargs_for_child.pop("use_new_version")

        # If version not specified, choose randomly
        if use_new is None:
            use_new = random.choice([True, False])

        if use_new:
            return OfferCardNew.render(context=context, kwargs=kwargs_for_child)
        else:
            return OfferCardOld.render(context=context, kwargs=kwargs_for_child)
