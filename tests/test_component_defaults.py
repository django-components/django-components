from dataclasses import field
from typing import Any

from django.template import Context

from django_components import Component, Default

from django_components.testing import djc_test
from .testutils import setup_test_config

setup_test_config({"autodiscover": False})


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

            def get_context_data(self, arg1: Any, variable: Any, another: Any, **attrs: Any):
                nonlocal did_call_context
                did_call_context = True

                # Check that args and slots are NOT affected by the defaults
                assert self.input.args == [123]
                assert [*self.input.slots.keys()] == ["my_slot"]
                assert self.input.slots["my_slot"](Context(), None, None) == "MY_SLOT"  # type: ignore[arg-type]

                assert self.input.kwargs == {
                    "variable": "test",  # User-given
                    "another": 1,  # Default because missing
                    "extra": "extra",  # Default because `None` was given
                    "fn": self.Defaults.fn,  # Default because missing
                }
                assert isinstance(self.input.context, Context)

                return {
                    "variable": variable,
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

            def get_context_data(self, variable: Any, **attrs: Any):
                nonlocal did_call_context
                did_call_context = True

                assert self.input.kwargs == {
                    "variable": "test",  # User-given
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert isinstance(self.input.context, Context)

                return {
                    "variable": variable,
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

            def get_context_data(self, variable: Any, **attrs: Any):
                nonlocal did_call_context
                did_call_context = True

                assert self.input.kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: NOT a factory, because it was set as `field(default=...)`
                    "fn": self.Defaults.fn.default,  # type: ignore[attr-defined]
                }
                assert isinstance(self.input.context, Context)

                return {
                    "variable": variable,
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

            def get_context_data(self, variable: Any, **attrs: Any):
                nonlocal did_call_context
                did_call_context = True

                assert self.input.kwargs == {
                    "variable": "test",  # User-given
                    # NOTE: IS a factory, because it was set as `field(default_factory=...)`
                    "fn": "fn_as_factory",  # Default because missing
                }
                assert isinstance(self.input.context, Context)

                return {
                    "variable": variable,
                }

        TestComponent.render(
            kwargs={"variable": "test"},
        )

        assert did_call_context
