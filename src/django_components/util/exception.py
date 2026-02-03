from collections.abc import Generator
from contextlib import contextmanager


def set_component_error_message(err: Exception, component_path: list[str]) -> None:
    """
    Format the error message to include the component path. E.g.
    ```
    KeyError: "An error occured while rendering components MyPage > MyComponent > MyComponent(slot:content)
    ```
    """
    if not hasattr(err, "_components"):
        err._components = []  # type: ignore[attr-defined]

    components = getattr(err, "_components", [])
    components = err._components = [*component_path, *components]  # type: ignore[attr-defined]

    # Format component path as
    # "MyPage > MyComponent > MyComponent(slot:content) > Base(slot:tab)"
    comp_path = " > ".join(components)
    prefix = f"An error occured while rendering components {comp_path}:\n"

    # Access the exception's message, see https://stackoverflow.com/a/75549200/9788634
    if len(err.args) and err.args[0] is not None:
        orig_msg = str(err.args[0])
        if components and "An error occured while rendering components" in orig_msg:
            orig_msg = str(err.args[0]).split("\n", 1)[-1]
    else:
        # When the exception has no message, it may be that the exception
        # does NOT rely on the `args` attribute. Such case is for example
        # Pydantic exceptions.
        #
        # In this case, we still try to use the `args` attribute, but
        # it's not guaranteed to work. So we also print out the component
        # path ourselves.
        print(prefix)  # noqa: T201
        orig_msg = str(err)

    err.args = (prefix + orig_msg,)  # tuple of one


@contextmanager
def with_component_error_message(component_path: list[str]) -> Generator[None, None, None]:
    """
    If an error occurs within the context, format the error message to include
    the component path. E.g.
    ```
    KeyError: "An error occured while rendering components MyPage > MyComponent > MyComponent(slot:content)
    ```
    """
    try:
        yield
    except Exception as err:
        set_component_error_message(err, component_path)

        # `from None` should still raise the original error, but without showing this
        # line in the traceback.
        raise err from None


@contextmanager
def add_slot_to_error_message(component_name: str, slot_name: str) -> Generator[None, None, None]:
    """
    This complements `with_component_error_message()` and is used inside SlotNode to add
    the slots to the component path in the error message, e.g.:

    ```
    KeyError: "An error occured while rendering components MyPage > MyComponent > MyComponent(slot:content)
    ```
    """
    try:
        yield
    except Exception as err:
        if not hasattr(err, "_components"):
            err._components = []  # type: ignore[attr-defined]

        err._components.insert(0, f"{component_name}(slot:{slot_name})")  # type: ignore[attr-defined]
        raise err from None
