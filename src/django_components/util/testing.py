import gc
import inspect
import sys
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)
from unittest.mock import patch
from weakref import ReferenceType

import django
from django.conf import settings as _django_settings
from django.core.cache import BaseCache, caches
from django.template import engines
from django.test import override_settings

from django_components import ComponentsSettings
from django_components.component import ALL_COMPONENTS, Component, component_node_subclasses_by_name
from django_components.component_registry import ALL_REGISTRIES, ComponentRegistry
from django_components.extension import extensions
from django_components.perfutil.provide import provide_cache
from django_components.template import _reset_component_template_file_cache, loading_components

if TYPE_CHECKING:
    from django.template.backends.django import DjangoTemplates

    from django_components.component_media import ComponentMedia

# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):
    RegistryRef = ReferenceType[ComponentRegistry]
    RegistriesCopies = List[Tuple[ReferenceType[ComponentRegistry], List[str]]]
    InitialComponents = List[ReferenceType[Type[Component]]]
else:
    RegistriesCopies = List[Tuple[ReferenceType, List[str]]]
    InitialComponents = List[ReferenceType]
    RegistryRef = ReferenceType


# Whether we're inside a test that was wrapped with `djc_test`.
# This is used so that we capture which modules we imported only if inside a test.
IS_TESTING = False


def is_testing() -> bool:
    return IS_TESTING


class GenIdPatcher:
    def __init__(self) -> None:
        self._gen_id_count = 10599485
        self._gen_id_patch: Any = None

    # Mock the `generate` function used inside `gen_id` so it returns deterministic IDs
    def start(self) -> None:
        # Random number so that the generated IDs are "hex-looking", e.g. a1bc3d
        self._gen_id_count = 10599485

        def mock_gen_id(*_args: Any, **_kwargs: Any) -> str:
            self._gen_id_count += 1
            return f"{self._gen_id_count:x}"

        self._gen_id_patch = patch("django_components.util.misc.generate", side_effect=mock_gen_id)
        self._gen_id_patch.start()

    def stop(self) -> None:
        if not self._gen_id_patch:
            return

        self._gen_id_patch.stop()
        self._gen_id_patch = None


class CsrfTokenPatcher:
    def __init__(self) -> None:
        self._csrf_token = "predictabletoken"  # noqa: S105
        self._csrf_token_patch: Any = None

    def start(self) -> None:
        self._csrf_token_patch = patch("django.middleware.csrf.get_token", return_value=self._csrf_token)
        self._csrf_token_patch.start()

    def stop(self) -> None:
        if self._csrf_token_patch:
            self._csrf_token_patch.stop()
            self._csrf_token_patch = None


def djc_test(
    django_settings: Union[Optional[Dict], Callable, Type] = None,
    components_settings: Optional[Dict] = None,
    # Input to `@pytest.mark.parametrize`
    parametrize: Optional[
        Union[
            Tuple[
                # names
                Sequence[str],
                # values
                Sequence[Sequence[Any]],
            ],
            Tuple[
                # names
                Sequence[str],
                # values
                Sequence[Sequence[Any]],
                # ids
                Optional[
                    Union[
                        Iterable[Union[None, str, float, int, bool]],
                        Callable[[Any], Optional[object]],
                    ]
                ],
            ],
        ]
    ] = None,
    gc_collect: bool = True,
) -> Callable:
    """
    Decorator for testing components from django-components.

    `@djc_test` manages the global state of django-components, ensuring that each test is properly
    isolated and that components registered in one test do not affect other tests.

    This decorator can be applied to a function, method, or a class. If applied to a class,
    it will search for all methods that start with `test_`, and apply the decorator to them.
    This is applied recursively to nested classes as well.

    Examples:

    Applying to a function:
    ```python
    from django_components.testing import djc_test

    @djc_test
    def test_my_component():
        @register("my_component")
        class MyComponent(Component):
            template = "..."
        ...
    ```

    Applying to a class:
    ```python
    from django_components.testing import djc_test

    @djc_test
    class TestMyComponent:
        def test_something(self):
            ...

        class Nested:
            def test_something_else(self):
                ...
    ```

    Applying to a class is the same as applying the decorator to each `test_` method individually:
    ```python
    from django_components.testing import djc_test

    class TestMyComponent:
        @djc_test
        def test_something(self):
            ...

        class Nested:
            @djc_test
            def test_something_else(self):
                ...
    ```

    To use `@djc_test`, Django must be set up first:

    ```python
    import django
    from django_components.testing import djc_test

    django.setup()

    @djc_test
    def test_my_component():
        ...
    ```

    **Arguments:**

    - `django_settings`: Django settings, a dictionary passed to Django's
      [`@override_settings`](https://docs.djangoproject.com/en/5.2/topics/testing/tools/#django.test.override_settings).
      The test runs within the context of these overridden settings.

        If `django_settings` contains django-components settings (`COMPONENTS` field), these are merged.
        Other Django settings are simply overridden.

    - `components_settings`: Instead of defining django-components settings under `django_settings["COMPONENTS"]`,
        you can simply set the Components settings here.

        These settings are merged with the django-components settings from `django_settings["COMPONENTS"]`.

        Fields in `components_settings` override fields in `django_settings["COMPONENTS"]`.

    - `parametrize`: Parametrize the test function with
        [`pytest.mark.parametrize`](https://docs.pytest.org/en/stable/how-to/parametrize.html#pytest-mark-parametrize).
        This requires [pytest](https://docs.pytest.org/) to be installed.

        The input is a tuple of:

        - `(param_names, param_values)` or
        - `(param_names, param_values, ids)`

    Example:
        ```py
        from django_components.testing import djc_test

        @djc_test(
            parametrize=(
                 ["input", "expected"],
                 [[1, "<div>1</div>"], [2, "<div>2</div>"]],
                 ids=["1", "2"]
             )
        )
        def test_component(input, expected):
            rendered = MyComponent(input=input).render()
            assert rendered == expected
        ```

        You can parametrize the Django or Components settings by setting up parameters called
        `django_settings` and `components_settings`. These will be merged with the respetive settings
        from the decorator.

        Example of parametrizing context_behavior:
        ```python
        from django_components.testing import djc_test

        @djc_test(
            components_settings={
                # Settings shared by all tests
                "app_dirs": ["custom_dir"],
            },
            parametrize=(
                # Parametrized settings
                ["components_settings"],
                [
                    [{"context_behavior": "django"}],
                    [{"context_behavior": "isolated"}],
                ],
                ["django", "isolated"],
            )
        )
        def test_context_behavior(components_settings):
            rendered = MyComponent.render()
            ...
        ```

    - `gc_collect`: By default `djc_test` runs garbage collection after each test to force the state cleanup.
      Set this to `False` to skip this.

    **Settings resolution:**

    `@djc_test` accepts settings from different sources. The settings are resolved in the following order:

    - Django settings:

        1. The defaults are the Django settings that Django was set up with.
        2. Those are then overriden with fields in the `django_settings` kwarg.
        3. The parametrized `django_settings` override the fields on the `django_settings` kwarg.

        Priority: `django_settings` (parametrized) > `django_settings` > `django.conf.settings`

    - Components settings:

        1. Same as above, except that the `django_settings["COMPONENTS"]` field is merged instead of overridden.
        2. The `components_settings` kwarg is then merged with the `django_settings["COMPONENTS"]` field.
        3. The parametrized `components_settings` override the fields on the `components_settings` kwarg.

        Priority: `components_settings` (parametrized) > `components_settings` > `django_settings["COMPONENTS"]` > `django.conf.settings.COMPONENTS`

    """  # noqa: E501

    def decorator(func: Callable) -> Callable:
        if isinstance(func, type) and func.__name__.lower().startswith("test"):
            # If `djc_test` is applied to a class, we need to apply it to each test method
            # individually.
            # The rest of this function addresses `func` being a function
            decorator = djc_test(
                # Check for callable in case `@djc_test` was applied without calling it as `djc_test(settings)`.
                django_settings=django_settings if not callable(django_settings) else None,
                components_settings=components_settings,
                parametrize=parametrize,
            )
            for name, attr in func.__dict__.items():
                if isinstance(attr, type):
                    # If the attribute is a class, apply the decorator to its methods:
                    djc_test(
                        django_settings=django_settings if not callable(django_settings) else None,
                        components_settings=components_settings,
                        parametrize=parametrize,
                    )(attr)
                if callable(attr) and name.startswith("test_"):
                    method = decorator(attr)
                    setattr(func, name, method)
            return func

        if getattr(func, "_djc_test_wrapped", False):
            return func

        gen_id_patcher = GenIdPatcher()
        csrf_token_patcher = CsrfTokenPatcher()

        # Contents of this function will run as the test
        def _wrapper_impl(*args: Any, **kwargs: Any) -> Any:
            # If Django is not yet configured, do so now, because we'll need to access
            # Django's settings when merging the given settings.
            if not _django_settings.configured:
                django.setup()

            # Merge the settings
            current_django_settings = django_settings if not callable(django_settings) else None
            current_django_settings = current_django_settings.copy() if current_django_settings else {}
            if parametrize and "django_settings" in kwargs:
                current_django_settings.update(kwargs["django_settings"])

            current_component_settings = components_settings.copy() if components_settings else {}
            if parametrize and "components_settings" in kwargs:
                # We've received a parametrized test function, so we need to
                # apply the parametrized settings to the test function.
                current_component_settings.update(kwargs["components_settings"])

            merged_settings = _merge_django_settings(
                current_django_settings,
                current_component_settings,
            )

            with override_settings(**merged_settings):
                # Make a copy of `ALL_COMPONENTS` and `ALL_REGISTRIES` as they were before the test.
                # Since the tests require Django to be configured, this should contain any
                # components that were registered with autodiscovery / at `AppConfig.ready()`.
                _all_components = ALL_COMPONENTS.copy()
                _all_registries_copies: RegistriesCopies = []
                for reg_ref in ALL_REGISTRIES:
                    reg = reg_ref()
                    if not reg:
                        continue
                    _all_registries_copies.append((reg_ref, list(reg._registry.keys())))

                # Prepare global state
                _setup_djc_global_state(gen_id_patcher, csrf_token_patcher)

                def cleanup() -> None:
                    _clear_djc_global_state(
                        gen_id_patcher,
                        csrf_token_patcher,
                        _all_components,  # type: ignore[arg-type]
                        _all_registries_copies,
                        gc_collect,
                    )

                try:
                    # Execute
                    result = func(*args, **kwargs)
                except Exception as err:
                    # On failure
                    cleanup()
                    raise err from None

                # On success
                cleanup()
                return result

        # Handle async test functions
        if inspect.iscoroutinefunction(func):

            async def wrapper_outer(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
                return await _wrapper_impl(*args, **kwargs)

        else:

            def wrapper_outer(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
                return _wrapper_impl(*args, **kwargs)

        wrapper = wraps(func)(wrapper_outer)

        # Allow to parametrize tests with pytest. This will effectively run the test multiple times,
        # with the different parameter values, and will display these as separte tests in the report.
        if parametrize:
            # We optionally allow to pass in the `ids` kwarg. Since `ids` is kwarg-only,
            # we can't just spread all tuple elements into the `parametrize` call, but we have
            # to manually apply it.
            if len(parametrize) == 3:
                # @pytest.mark.parametrize("a,b,expected", testdata, ids=["forward", "backward"])
                param_names, values, ids = parametrize
            else:
                # @pytest.mark.parametrize("a,b,expected", testdata)
                param_names, values = parametrize
                ids = None

            # NOTE: Lazily import pytest, so user can still run tests with plain `unittest`
            #       if they choose not to use parametrization.
            import pytest  # noqa: PLC0415

            wrapper = pytest.mark.parametrize(param_names, values, ids=ids)(wrapper)

        wrapper._djc_test_wrapped = True  # type: ignore[attr-defined]
        return wrapper

    # Handle `@djc_test` (no arguments, func passed directly)
    if callable(django_settings):
        return decorator(django_settings)

    # Handle `@djc_test(settings)`
    return decorator


def _merge_django_settings(
    django_settings: Optional[Mapping[str, Any]] = None,
    components_settings: Optional[Union[Mapping[str, Any], "ComponentsSettings"]] = None,
) -> Dict[str, Any]:
    """
    Merge settings such that the fields in the `COMPONENTS` setting are merged.
    Use components_settings to override fields in the django COMPONENTS setting.
    """
    merged_settings: Dict[str, Any] = dict(django_settings or {})

    defaults = _components_to_mapping(_django_settings.COMPONENTS if _django_settings.configured else {})
    current = _components_to_mapping(merged_settings.get("COMPONENTS"))
    overrides = _components_to_mapping(components_settings)

    merged_settings["COMPONENTS"] = {**defaults, **current, **overrides}
    return merged_settings


def _components_to_mapping(
    value: Optional[Union[Mapping[str, Any], "ComponentsSettings"]],
) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, ComponentsSettings):
        return dict(value._asdict())
    raise TypeError("COMPONENTS must be a mapping or ComponentsSettings")


def _setup_djc_global_state(
    gen_id_patcher: GenIdPatcher,
    csrf_token_patcher: CsrfTokenPatcher,
) -> None:
    # Declare that the code is running in test mode - this is used
    # by the import / autodiscover mechanism to clean up loaded modules
    # between tests.
    global IS_TESTING  # noqa: PLW0603
    IS_TESTING = True

    gen_id_patcher.start()
    csrf_token_patcher.start()

    # Re-load the settings, so that the test-specific settings overrides are applied
    from django_components.app_settings import app_settings  # noqa: PLC0415

    app_settings._load_settings()
    extensions._initialized = False
    extensions._init_app()


def _clear_djc_global_state(
    gen_id_patcher: GenIdPatcher,
    csrf_token_patcher: CsrfTokenPatcher,
    initial_components: InitialComponents,
    initial_registries_copies: RegistriesCopies,
    gc_collect: bool = False,
) -> None:
    gen_id_patcher.stop()
    csrf_token_patcher.stop()

    # Clear loader cache - That is, templates that were loaded with Django's `get_template()`.
    # This applies to components that had the `template_name` / `template_field` field set.
    # See https://stackoverflow.com/a/77531127/9788634
    #
    # If we don't do this, then, since the templates are cached, the next test might fail
    # beause the IDs count will reset to 0, but we won't generate IDs for the Nodes of the cached
    # templates. Thus, the IDs will be out of sync between the tests.
    for engine in engines.all():
        if not hasattr(engine, "engine"):
            continue
        django_engine = cast("DjangoTemplates", engine)
        for loader in django_engine.engine.template_loaders:
            if hasattr(loader, "reset"):
                loader.reset()

    # NOTE: There are 1-2 tests which check Templates, so we need to clear the cache
    from django_components.cache import component_media_cache, template_cache  # noqa: PLC0415

    if template_cache:
        template_cache.clear()

    if component_media_cache:
        component_media_cache.clear()

    if provide_cache:
        provide_cache.clear()

    # Remove cached Node subclasses
    component_node_subclasses_by_name.clear()

    # Clean up any loaded media (HTML, JS, CSS)
    for comp_cls_ref in ALL_COMPONENTS:
        comp_cls = comp_cls_ref()
        if comp_cls is None:
            continue

        for file_attr, value_attr in [("template_file", "template"), ("js_file", "js"), ("css_file", "css")]:
            # If both fields are set, then the value was set from the file field.
            # Since we have some tests that check for these, we need to reset the state.
            comp_media: ComponentMedia = comp_cls._component_media  # type: ignore[attr-defined]
            if getattr(comp_media, file_attr, None) and getattr(comp_media, value_attr, None):
                # Remove the value field, so it's not used in the next test
                setattr(comp_media, value_attr, None)
                comp_media.reset()

    # Remove components that were created during the test
    initial_components_set = set(initial_components)
    all_comps_len = len(ALL_COMPONENTS)
    for index in range(all_comps_len):
        reverse_index = all_comps_len - index - 1
        comp_cls_ref = ALL_COMPONENTS[reverse_index]
        is_ref_deleted = comp_cls_ref() is None
        if is_ref_deleted or comp_cls_ref not in initial_components_set:
            del ALL_COMPONENTS[reverse_index]

    # Remove registries that were created during the test
    initial_registries_set: Set[RegistryRef] = {reg_ref for reg_ref, init_keys in initial_registries_copies}
    for index in range(len(ALL_REGISTRIES)):
        registry_ref = ALL_REGISTRIES[len(ALL_REGISTRIES) - index - 1]
        is_ref_deleted = registry_ref() is None
        if is_ref_deleted or registry_ref not in initial_registries_set:
            del ALL_REGISTRIES[len(ALL_REGISTRIES) - index - 1]

    # For the remaining registries, unregistr components that were registered
    # during tests.
    # NOTE: The approach below does NOT take into account:
    # - If a component was UNregistered during the test
    # - If a previously-registered component was overwritten with different registration.
    for reg_ref, init_keys in initial_registries_copies:
        registry_original = reg_ref()
        if not registry_original:
            continue

        # Get the keys that were registered during the test
        initial_registered_keys = set(init_keys)
        after_test_registered_keys = set(registry_original._registry.keys())
        keys_registered_during_test = after_test_registered_keys - initial_registered_keys
        # Remove them
        for key in keys_registered_during_test:
            registry_original.unregister(key)

    # Delete autoimported modules from memory, so the module
    # is executed also the next time one of the tests calls `autodiscover`.
    from django_components.autodiscovery import LOADED_MODULES  # noqa: PLC0415

    for mod in LOADED_MODULES:
        sys.modules.pop(mod, None)
    LOADED_MODULES.clear()

    # Clear extensions caches
    extensions._route_to_url.clear()

    # Clear other djc state
    _reset_component_template_file_cache()
    loading_components.clear()

    # Clear Django caches
    all_caches: List[BaseCache] = list(caches.all())
    for cache in all_caches:
        cache.clear()

    # Force garbage collection, so that any finalizers are run.
    # If garbage collection is skipped, then in some cases the finalizers
    # are run too late, in the context of the next test, causing flaky tests.
    if gc_collect:
        gc.collect()

    global IS_TESTING  # noqa: PLW0603
    IS_TESTING = False
