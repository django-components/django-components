from dataclasses import dataclass, field
from typing import NamedTuple

from django.template import Context

from django_components import Component, Default, get_component_defaults
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

    def test_defaults_from_kwargs_namedtuple(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Kwargs(NamedTuple):
                another: int
                variable: str = "default_from_kwargs"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert self.raw_kwargs == {
                    "variable": "default_from_kwargs",
                    "another": 123,
                }
                return {}

        TestComponent.render(
            kwargs={"another": 123},
        )

        assert did_call_context

    def test_defaults_from_kwargs_dataclass(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            @dataclass
            class Kwargs:
                another: int
                variable: str = "default_from_kwargs"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert self.raw_kwargs == {
                    "variable": "default_from_kwargs",
                    "another": 123,
                }
                return {}

        TestComponent.render(
            kwargs={"another": 123},
        )

        assert did_call_context

    def test_defaults_from_kwargs_other_class(self):
        did_call_context = False

        class CustomKwargs:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
                self._kwargs = kwargs

            def _asdict(self):
                return self._kwargs

        class TestComponent(Component):
            template = ""

            class Kwargs(CustomKwargs):
                another: int
                variable: str = "default_from_kwargs"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                # No defaults should be applied from a plain class
                assert self.raw_kwargs == {
                    "another": 123,
                }
                return {}

        TestComponent.render(
            kwargs={"another": 123},
        )

        assert did_call_context

    def test_defaults_from_defaults_and_kwargs_namedtuple(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            class Kwargs(NamedTuple):
                from_defaults_only: str
                variable: str = "from_kwargs"
                from_kwargs_only: str = "kwargs_default"

            class Defaults:
                variable = "from_defaults"
                from_defaults_only = "defaults_default"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert self.raw_kwargs == {
                    "variable": "from_kwargs",  # Overridden by Kwargs
                    "from_defaults_only": "defaults_default",
                    "from_kwargs_only": "kwargs_default",
                }
                return {}

        TestComponent.render(kwargs={})
        assert did_call_context

    def test_defaults_from_defaults_and_kwargs_dataclass(self):
        did_call_context = False

        class TestComponent(Component):
            template = ""

            @dataclass
            class Kwargs:
                from_defaults_only: str
                variable: str = "from_kwargs"
                from_kwargs_only: str = "kwargs_default"

            class Defaults:
                variable = "from_defaults"
                from_defaults_only = "defaults_default"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert self.raw_kwargs == {
                    "variable": "from_kwargs",  # Overridden by Kwargs
                    "from_defaults_only": "defaults_default",
                    "from_kwargs_only": "kwargs_default",
                }
                return {}

        TestComponent.render(kwargs={})
        assert did_call_context

    def test_defaults_from_defaults_and_kwargs_other_class(self):
        did_call_context = False

        class CustomKwargs:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
                self._kwargs = kwargs

            def _asdict(self):
                return self._kwargs

        class TestComponent(Component):
            template = ""

            class Kwargs(CustomKwargs):
                variable: str = "from_kwargs"

            class Defaults:
                variable = "from_defaults"
                from_defaults_only = "defaults_default"

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                assert self.raw_kwargs == {
                    "variable": "from_defaults",  # No override
                    "from_defaults_only": "defaults_default",
                }
                return {}

        TestComponent.render(kwargs={})
        assert did_call_context

    def test_nested_dataclass_remains_as_instance(self):
        """
        Test that nested dataclasses in Kwargs remain as dataclass instances,
        not converted to dictionaries.
        """
        did_call_context = False

        @dataclass
        class User:
            name: str

        class TestComponent(Component):
            template = ""

            @dataclass
            class Kwargs:
                user: User
                count: int

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal did_call_context
                did_call_context = True

                # The nested dataclass should remain as a User instance, not a dict
                assert isinstance(kwargs.user, User)
                assert kwargs.user.name == "John"
                assert kwargs.count == 5

                return {}

        TestComponent.render(
            kwargs={
                "user": User(name="John"),
                "count": 5,
            }
        )

        assert did_call_context


@djc_test
class TestGetComponentDefaults:
    def test_defaults_with_factory(self):
        class MyComponent(Component):
            template = ""

            class Defaults:
                val = "static"
                factory_val = Default(lambda: "from_factory")

        defaults = get_component_defaults(MyComponent)
        assert defaults == {
            "val": "static",
            "factory_val": "from_factory",
        }

    def test_kwargs_dataclass_with_factory(self):
        class MyComponent(Component):
            template = ""

            @dataclass
            class Kwargs:
                val: str = "static"
                factory_val: str = field(default_factory=lambda: "from_factory")

        defaults = get_component_defaults(MyComponent)
        assert defaults == {
            "val": "static",
            "factory_val": "from_factory",
        }

    def test_defaults_and_kwargs_overrides_with_factories(self):
        class MyComponent(Component):
            template = ""

            @dataclass
            class Kwargs:
                val_both: str = field(default_factory=lambda: "from_kwargs_factory")
                val_kwargs: str = field(default_factory=lambda: "kwargs_only")

            class Defaults:
                val_both = Default(lambda: "from_defaults_factory")
                val_defaults = Default(lambda: "defaults_only")

        defaults = get_component_defaults(MyComponent)
        assert defaults == {
            "val_both": "from_kwargs_factory",
            "val_kwargs": "kwargs_only",
            "val_defaults": "defaults_only",
        }

    def test_kwargs_namedtuple_with_defaults(self):
        class MyComponent(Component):
            template = ""

            class Kwargs(NamedTuple):
                val_no_default: int
                val_defaults: str
                val_kwargs: str = "kwargs_default"

            class Defaults:
                val_defaults = "defaults_default"

        defaults = get_component_defaults(component=MyComponent)
        assert defaults == {
            "val_kwargs": "kwargs_default",
            "val_defaults": "defaults_default",
        }
