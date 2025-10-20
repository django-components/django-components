import re
from dataclasses import dataclass
from typing import NamedTuple, Optional

import pytest
from django.template import Context
from typing_extensions import NotRequired, TypedDict

from django_components import Component, Empty, Slot, SlotInput
from django_components.testing import djc_test

from .testutils import setup_test_config

setup_test_config()


@djc_test
class TestComponentTyping:
    def test_data_methods_input_typed_custom_classes(self):
        template_called = False
        js_called = False
        css_called = False

        class ButtonFooterSlotData(TypedDict):
            value: int

        class Button(Component):
            class Args(NamedTuple):
                arg1: str
                arg2: str

            @dataclass
            class Kwargs:
                name: str
                age: int
                maybe_var: Optional[int] = None

            class Slots(TypedDict):
                # Use `SlotInput` when you want to pass slot as string
                header: SlotInput
                # Use `Slot` for slot functions.
                # The generic specifies the data available to the slot function
                footer: NotRequired[Slot[ButtonFooterSlotData]]

            def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal template_called
                template_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            def get_js_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal js_called
                js_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            def get_css_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal css_called
                css_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            template = "<button>Click me!</button>"

        Button.render(
            args=Button.Args(arg1="arg1", arg2="arg2"),
            kwargs=Button.Kwargs(name="name", age=123),
            slots=Button.Slots(
                header="HEADER",
                footer=Slot(lambda _ctx: "FOOTER"),
            ),
        )

        assert template_called
        assert js_called
        assert css_called

    def test_data_methods_input_typed_default_classes(self):
        template_called = False
        js_called = False
        css_called = False

        class ButtonFooterSlotData(TypedDict):
            value: int

        class Button(Component):
            class Args:
                arg1: str
                arg2: str

            class Kwargs:
                name: str
                age: int
                maybe_var: Optional[int] = None

            class Slots:
                header: SlotInput
                footer: Optional[Slot[ButtonFooterSlotData]]

            def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal template_called
                template_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, Button.Slots)
                assert isinstance(context, Context)

            def get_js_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal js_called
                js_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, Button.Slots)
                assert isinstance(context, Context)

            def get_css_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                nonlocal css_called
                css_called = True

                assert isinstance(args, Button.Args)
                assert isinstance(kwargs, Button.Kwargs)
                assert isinstance(slots, Button.Slots)
                assert isinstance(context, Context)

            template = "<button>Click me!</button>"

        assert issubclass(Button.Args, tuple)
        assert issubclass(Button.Kwargs, tuple)
        assert issubclass(Button.Slots, tuple)

        Button.render(
            args=Button.Args(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            kwargs=Button.Kwargs(name="name", age=123),  # type: ignore[call-arg]
            slots=Button.Slots(  # type: ignore[call-arg]
                header="HEADER",
                footer=Slot(lambda _ctx: "FOOTER"),
            ),
        )

        assert template_called
        assert js_called
        assert css_called

    def test_data_methods_input_not_typed_by_default(self):
        template_called = False
        js_called = False
        css_called = False

        class Button(Component):
            def get_template_data(self, args, kwargs, slots, context):
                nonlocal template_called
                template_called = True

                assert isinstance(args, list)
                assert isinstance(kwargs, dict)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            def get_js_data(self, args, kwargs, slots, context):
                nonlocal js_called
                js_called = True

                assert isinstance(args, list)
                assert isinstance(kwargs, dict)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            def get_css_data(self, args, kwargs, slots, context):
                nonlocal css_called
                css_called = True

                assert isinstance(args, list)
                assert isinstance(kwargs, dict)
                assert isinstance(slots, dict)
                assert isinstance(context, Context)

            template = "<button>Click me!</button>"

        Button.render(
            args=["arg1", "arg2"],
            kwargs={"name": "name", "age": 123},
            slots={
                "header": "HEADER",
                "footer": Slot(lambda _ctx: "FOOTER"),
            },
        )

        assert template_called
        assert js_called
        assert css_called

    def test_data_methods_output_typed_default_classes(self):
        template_called = False
        js_called = False
        css_called = False

        class Button(Component):
            class TemplateData:
                data1: str
                data2: int

            class JsData:
                js_data1: str
                js_data2: int

            class CssData:
                css_data1: str
                css_data2: int

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal template_called
                template_called = True

                return {
                    "data1": "data1",
                    "data2": 123,
                }

            def get_js_data(self, args, kwargs, slots, context):
                nonlocal js_called
                js_called = True

                return {
                    "js_data1": "js_data1",
                    "js_data2": 123,
                }

            def get_css_data(self, args, kwargs, slots, context):
                nonlocal css_called
                css_called = True

                return {
                    "css_data1": "css_data1",
                    "css_data2": 123,
                }

            template = "<button>Click me!</button>"

        assert issubclass(Button.TemplateData, tuple)
        assert issubclass(Button.JsData, tuple)
        assert issubclass(Button.CssData, tuple)

        Button.render(
            args=["arg1", "arg2"],
            kwargs={"name": "name", "age": 123},
            slots={
                "header": "HEADER",
                "footer": Slot(lambda _ctx: "FOOTER"),
            },
        )

        assert template_called
        assert js_called
        assert css_called

    def test_data_methods_output_typed_custom_classes(self):
        template_called = False
        js_called = False
        css_called = False

        template_data_instance = None
        js_data_instance = None
        css_data_instance = None

        class Button(Component):
            # Data returned from `get_template_data`
            @dataclass
            class TemplateData:
                data1: str
                data2: int

                def __post_init__(self):
                    nonlocal template_data_instance
                    template_data_instance = self

            # Data returned from `get_js_data`
            @dataclass
            class JsData:
                js_data1: str
                js_data2: int

                def __post_init__(self):
                    nonlocal js_data_instance
                    js_data_instance = self

            # Data returned from `get_css_data`
            @dataclass
            class CssData:
                css_data1: str
                css_data2: int

                def __post_init__(self):
                    nonlocal css_data_instance
                    css_data_instance = self

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal template_called
                template_called = True

                return {
                    "data1": "data1",
                    "data2": 123,
                }

            def get_js_data(self, args, kwargs, slots, context):
                nonlocal js_called
                js_called = True

                return {
                    "js_data1": "js_data1",
                    "js_data2": 123,
                }

            def get_css_data(self, args, kwargs, slots, context):
                nonlocal css_called
                css_called = True

                return {
                    "css_data1": "css_data1",
                    "css_data2": 123,
                }

            template = "<button>Click me!</button>"

        Button.render(
            args=["arg1", "arg2"],
            kwargs={"name": "name", "age": 123},
            slots={
                "header": "HEADER",
                "footer": Slot(lambda _ctx: "FOOTER"),
            },
        )

        assert template_called
        assert js_called
        assert css_called

        assert isinstance(template_data_instance, Button.TemplateData)
        assert isinstance(js_data_instance, Button.JsData)
        assert isinstance(css_data_instance, Button.CssData)

        assert template_data_instance == Button.TemplateData(data1="data1", data2=123)
        assert js_data_instance == Button.JsData(js_data1="js_data1", js_data2=123)
        assert css_data_instance == Button.CssData(css_data1="css_data1", css_data2=123)

    def test_data_methods_output_typed_reuses_instances(self):
        template_called = False
        js_called = False
        css_called = False

        template_data_instance = None
        js_data_instance = None
        css_data_instance = None

        class Button(Component):
            # Data returned from `get_template_data`
            @dataclass
            class TemplateData:
                data1: str
                data2: int

                def __post_init__(self):
                    nonlocal template_data_instance
                    template_data_instance = self

            # Data returned from `get_js_data`
            @dataclass
            class JsData:
                js_data1: str
                js_data2: int

                def __post_init__(self):
                    nonlocal js_data_instance
                    js_data_instance = self

            # Data returned from `get_css_data`
            @dataclass
            class CssData:
                css_data1: str
                css_data2: int

                def __post_init__(self):
                    nonlocal css_data_instance
                    css_data_instance = self

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal template_called
                template_called = True

                data = Button.TemplateData(
                    data1="data1",
                    data2=123,
                )

                # Reset the instance to None to check if the instance is reused
                nonlocal template_data_instance
                template_data_instance = None

                return data

            def get_js_data(self, args, kwargs, slots, context):
                nonlocal js_called
                js_called = True

                data = Button.JsData(
                    js_data1="js_data1",
                    js_data2=123,
                )

                # Reset the instance to None to check if the instance is reused
                nonlocal js_data_instance
                js_data_instance = None

                return data

            def get_css_data(self, args, kwargs, slots, context):
                nonlocal css_called
                css_called = True

                data = Button.CssData(
                    css_data1="css_data1",
                    css_data2=123,
                )

                # Reset the instance to None to check if the instance is reused
                nonlocal css_data_instance
                css_data_instance = None

                return data

            template = "<button>Click me!</button>"

        Button.render(
            args=["arg1", "arg2"],
            kwargs={"name": "name", "age": 123},
            slots={
                "header": "HEADER",
                "footer": Slot(lambda _ctx: "FOOTER"),
            },
        )

        assert template_called
        assert js_called
        assert css_called

        assert template_data_instance is not None
        assert js_data_instance is not None
        assert css_data_instance is not None

    def test_builtin_classes(self):
        class ButtonFooterSlotData(TypedDict):
            value: int

        class Button(Component):
            class Args(NamedTuple):
                arg1: str
                arg2: str

            @dataclass
            class Kwargs:
                name: str
                age: int
                maybe_var: Optional[int] = None

            class Slots(TypedDict):
                # Use `SlotInput` when you want to pass slot as string
                header: SlotInput
                # Use `Slot` for slot functions.
                # The generic specifies the data available to the slot function
                footer: NotRequired[Slot[ButtonFooterSlotData]]

            # Data returned from `get_template_data`
            class TemplateData(NamedTuple):
                data1: str
                data2: int
                data3: str

            # Data returned from `get_js_data`
            @dataclass
            class JsData:
                js_data1: str
                js_data2: int
                js_data3: str

            # Data returned from `get_css_data`
            @dataclass
            class CssData:
                css_data1: str
                css_data2: int
                css_data3: str

            def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                return self.TemplateData(
                    data1=kwargs.name,
                    data2=kwargs.age,
                    data3=args.arg1,
                )

            def get_js_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                return self.JsData(
                    js_data1=kwargs.name,
                    js_data2=kwargs.age,
                    js_data3=args.arg1,
                )

            def get_css_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
                return self.CssData(
                    css_data1=kwargs.name,
                    css_data2=kwargs.age,
                    css_data3=args.arg1,
                )

            template = "<button>Click me!</button>"

        # Success case
        Button.render(
            args=Button.Args(arg1="arg1", arg2="arg2"),
            kwargs=Button.Kwargs(name="name", age=123),
            slots=Button.Slots(
                header="HEADER",
                footer=Slot(lambda _ctx: "FOOTER"),
            ),
        )

        # Failure case 1: NamedTuple raises error when a required argument is missing
        with pytest.raises(
            TypeError,
            match=re.escape("missing 1 required positional argument: 'arg2'"),
        ):
            Button.render(
                # Missing arg2
                args=Button.Args(arg1="arg1"),  # type: ignore[call-arg]
                kwargs=Button.Kwargs(name="name", age=123),
                slots=Button.Slots(
                    header="HEADER",
                    footer=Slot(lambda _ctx: "FOOTER"),
                ),
            )

        # Failure case 2: Dataclass raises error when a required argument is missing
        with pytest.raises(
            TypeError,
            match=re.escape("missing 1 required positional argument: 'name'"),
        ):
            Button.render(
                args=Button.Args(arg1="arg1", arg2="arg2"),
                # Name missing
                kwargs=Button.Kwargs(age=123),  # type: ignore[call-arg]
                slots=Button.Slots(
                    header="HEADER",
                    footer=Slot(lambda _ctx: "FOOTER"),
                ),
            )

        # Failure case 3
        # NOTE: While we would expect this to raise, seems that TypedDict (`Slots`)
        #       does NOT raise an error when a required key is missing.
        Button.render(
            args=Button.Args(arg1="arg1", arg2="arg2"),
            kwargs=Button.Kwargs(name="name", age=123),
            slots=Button.Slots(  # type: ignore[typeddict-item]
                footer=Slot(lambda _ctx: "FOOTER"),  # Missing header
            ),
        )

        # Failure case 4: Data object is not of the expected type
        class ButtonBad(Button):
            class TemplateData(NamedTuple):
                data1: str
                data2: int  # Removed data3

        with pytest.raises(
            TypeError,
            match=re.escape("got an unexpected keyword argument 'data3'"),
        ):
            ButtonBad.render(
                args=ButtonBad.Args(arg1="arg1", arg2="arg2"),
                kwargs=ButtonBad.Kwargs(name="name", age=123),
            )

    def test_empty_type(self):
        template_called = False

        class Button(Component):
            template = "Hello"

            Args = Empty
            Kwargs = Empty

            def get_template_data(self, args, kwargs, slots, context):
                nonlocal template_called
                template_called = True

                assert isinstance(args, Empty)
                assert isinstance(kwargs, Empty)

        # Success case
        Button.render()
        assert template_called

        # Failure cases
        with pytest.raises(TypeError, match=re.escape("got an unexpected keyword argument 'arg1'")):
            Button.render(
                args=Button.Args(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

        with pytest.raises(TypeError, match=re.escape("got an unexpected keyword argument 'arg1'")):
            Button.render(
                kwargs=Button.Kwargs(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

    def test_custom_args_class_raises_on_invalid(self):
        class Parent:
            pass

        class Button(Component):
            template = "Hello"

            class Args(Parent):
                arg1: str
                arg2: str

        assert issubclass(Button.Args, Parent)
        assert not issubclass(Button.Args, tuple)

        with pytest.raises(TypeError, match=re.escape("Args() takes no arguments")):
            Button.render(
                args=Button.Args(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

        class Parent2:
            def __init__(self, arg1: str, arg2: str):
                self.arg1 = arg1
                self.arg2 = arg2

        class Button2(Component):
            template = "Hello"

            class Args(Parent2):
                arg1: str
                arg2: str

        assert not issubclass(Button2.Args, tuple)
        assert issubclass(Button2.Args, Parent2)

        with pytest.raises(TypeError, match=re.escape("'Args' object is not iterable")):
            Button2.render(
                args=Button2.Args(arg1="arg1", arg2="arg2"),
            )

        class Parent3:
            def __iter__(self):
                return iter([self.arg1, self.arg2])  # type: ignore[attr-defined]

        class Button3(Component):
            template = "Hello"

            class Args(Parent3):
                arg1: str
                arg2: str

        assert not issubclass(Button3.Args, tuple)
        assert issubclass(Button3.Args, Parent3)

        with pytest.raises(TypeError, match=re.escape("Args() takes no arguments")):
            Button3.render(
                args=Button3.Args(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

    def test_custom_args_class_custom(self):
        class Parent:
            def __init__(self, arg1: str, arg2: str):
                self.arg1 = arg1
                self.arg2 = arg2

            def __iter__(self):
                return iter([self.arg1, self.arg2])

        class Button(Component):
            template = "Hello"

            class Args(Parent):
                arg1: str
                arg2: str

        Button.render(
            args=Button.Args(arg1="arg1", arg2="arg2"),
        )

    def test_custom_kwargs_class_raises_on_invalid(self):
        class Parent:
            pass

        class Button(Component):
            template = "Hello"

            class Kwargs(Parent):
                arg1: str
                arg2: str

        assert not issubclass(Button.Kwargs, tuple)
        assert issubclass(Button.Kwargs, Parent)

        with pytest.raises(TypeError, match=re.escape("Kwargs() takes no arguments")):
            Button.render(
                kwargs=Button.Kwargs(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

        class Parent2:
            def __init__(self, arg1: str, arg2: str):
                self.arg1 = arg1
                self.arg2 = arg2

        class Button2(Component):
            template = "Hello"

            class Kwargs(Parent2):
                arg1: str
                arg2: str

        assert not issubclass(Button2.Kwargs, tuple)
        assert issubclass(Button2.Kwargs, Parent2)

        with pytest.raises(TypeError, match=re.escape("'Kwargs' object is not iterable")):
            Button2.render(
                kwargs=Button2.Kwargs(arg1="arg1", arg2="arg2"),
            )

        class Parent3:
            def _asdict(self):
                return {"arg1": self.arg1, "arg2": self.arg2}  # type: ignore[attr-defined]

        class Button3(Component):
            template = "Hello"

            class Kwargs(Parent3):
                arg1: str
                arg2: str

        assert not issubclass(Button3.Kwargs, tuple)
        assert issubclass(Button3.Kwargs, Parent3)

        with pytest.raises(TypeError, match=re.escape("Kwargs() takes no arguments")):
            Button3.render(
                kwargs=Button3.Kwargs(arg1="arg1", arg2="arg2"),  # type: ignore[call-arg]
            )

    def test_custom_kwargs_class_custom(self):
        class Parent:
            def __init__(self, arg1: str, arg2: str):
                self.arg1 = arg1
                self.arg2 = arg2

            def _asdict(self):
                return {"arg1": self.arg1, "arg2": self.arg2}

        class Button(Component):
            template = "Hello"

            class Kwargs(Parent):
                arg1: str
                arg2: str

        assert not issubclass(Button.Kwargs, tuple)
        assert issubclass(Button.Kwargs, Parent)

        Button.render(
            kwargs=Button.Kwargs(arg1="arg1", arg2="arg2"),
        )

    def test_subclass_overrides_parent_type(self):
        class Button(Component):
            template = "Hello"

            class Args:
                size: int

            class Kwargs:
                color: str

        class ButtonExtra(Button):
            class Args:
                name: str
                size: int

            def get_template_data(self, args: Args, kwargs: "ButtonExtra.Kwargs", slots, context):
                assert isinstance(args, ButtonExtra.Args)
                assert isinstance(kwargs, ButtonExtra.Kwargs)
                assert ButtonExtra.Kwargs is Button.Kwargs

        ButtonExtra.render(
            args=ButtonExtra.Args(name="John", size=30),  # type: ignore[call-arg]
            kwargs=ButtonExtra.Kwargs(color="red"),  # type: ignore[call-arg]
        )
