from dataclasses import field

from django.template import Context

from django_components import Component, Default
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


@djc_test
class TestComponentDefaults:
    def test_input_defaults(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Defaults:
                variable = "test"
                another = 1
                extra = "extra"
                fn = lambda: "fn_as_val"  # noqa: E731

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert kwargs == {
                    "variable": "test",  # User-given
                    "another": 1,  # Default because missing
                    "extra": "extra",  # Default because `None` was given
                    "fn": self.Defaults.fn,  # Default because missing
                }
                assert self.raw_kwargs == {
                    "variable": "test",  # User-given
                    "another": 1,  # Default because missing
                    "extra": "extra",  # Default because `None` was given
                    "fn": self.Defaults.fn,  # Default because missing
                }

                # Check that args and slots are NOT affected by the defaults
                assert args == [123]
                assert [*slots.keys()] == ["my_slot"]
                assert slots["my_slot"](Context(), None, None) == "MY_SLOT"  # type: ignore[arg-type]

                assert self.raw_args == [123]
                assert [*self.raw_slots.keys()] == ["my_slot"]
                assert self.raw_slots["my_slot"](Context(), None, None) == "MY_SLOT"  # type: ignore[arg-type]

                assert isinstance(self.context, Context)

                return {
                    "variable": kwargs["variable"],
                }

        TestComponent.render(
            args=(123,),
            kwargs={"variable": "test", "extra": None},
            slots={"my_slot": "MY_SLOT"},
        )

        assert did_call_context

    def test_factory_from_class(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Defaults:
                variable = "test"
                fn = Default(lambda: "fn_as_factory")

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert kwargs == {
                    "variable": "test",  # User-given
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert self.raw_kwargs == {
                    "variable": "test",  # User-given
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert isinstance(self.context, Context)

                return {
                    "variable": kwargs["variable"],
                }

        TestComponent.render(
            kwargs={"variable": "test"},
        )

        assert did_call_context

    def test_factory_from_dataclass_field_value(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Defaults:
                variable = "test"
                fn = field(default=lambda: "fn_as_factory")

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: NOT a factory, because it was set as `field(default=...)`
                    "fn": self.Defaults.fn.default,  # type: ignore[attr-defined]
                }
                assert self.raw_kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: NOT a factory, because it was set as `field(default=...)`
                    "fn": self.Defaults.fn.default,  # type: ignore[attr-defined]
                }
                assert isinstance(self.context, Context)

                return {
                    "variable": kwargs["variable"],
                }

        TestComponent.render(
            kwargs={"variable": "test"},
        )

        assert did_call_context

    def test_factory_from_dataclass_field_factory(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Defaults:
                variable = "test"
                fn = field(default_factory=lambda: "fn_as_factory")

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: IS a factory, because it was set as `field(default_factory=...)`
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert self.raw_kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: IS a factory, because it was set as `field(default_factory=...)`
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert isinstance(self.context, Context)

                return {
                    "variable": kwargs["variable"],
                }

        TestComponent.render(
            kwargs={"variable": "test"},
        )

        assert did_call_context
