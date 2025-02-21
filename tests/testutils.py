import contextlib
import functools
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import Mock, patch

from django.template import Context, Node
from django.template.loader import engines
from django.template.response import TemplateResponse
from django.test import SimpleTestCase, override_settings

from django_components.app_settings import ContextBehavior
from django_components.autodiscovery import autodiscover
from django_components.component_registry import registry
from django_components.middleware import ComponentDependencyMiddleware

# Create middleware instance
response_stash = None
middleware = ComponentDependencyMiddleware(get_response=lambda _: response_stash)


class GenIdPatcher:
    def __init__(self):
        self._gen_id_count = 10599485

    # Mock the `generate` function used inside `gen_id` so it returns deterministic IDs
    def start(self):
        # Random number so that the generated IDs are "hex-looking", e.g. a1bc3d
        self._gen_id_count = 10599485

        def mock_gen_id(*args, **kwargs):
            self._gen_id_count += 1
            return hex(self._gen_id_count)[2:]

        self._gen_id_patch = patch("django_components.util.misc.generate", side_effect=mock_gen_id)
        self._gen_id_patch.start()

    def stop(self):
        self._gen_id_patch.stop()
        self._gen_id_count = 10599485


class CsrfTokenPatcher:
    def __init__(self):
        self._csrf_token = "predictabletoken"

    def start(self):
        self._csrf_token_patch = patch("django.middleware.csrf.get_token", return_value=self._csrf_token)
        self._csrf_token_patch.start()

    def stop(self):
        self._csrf_token_patch.stop()


class BaseTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.gen_id_patcher = GenIdPatcher()
        self.gen_id_patcher.start()
        self.csrf_token_patcher = CsrfTokenPatcher()
        self.csrf_token_patcher.start()

    def tearDown(self):
        self.gen_id_patcher.stop()
        self.csrf_token_patcher.stop()
        super().tearDown()
        registry.clear()

        from django_components.cache import component_media_cache, template_cache

        # NOTE: There are 1-2 tests which check Templates, so we need to clear the cache
        if template_cache:
            template_cache.clear()

        if component_media_cache:
            component_media_cache.clear()

        from django_components.component import component_node_subclasses_by_name
        component_node_subclasses_by_name.clear()


request = Mock()
mock_template = Mock()


def create_and_process_template_response(template, context=None, use_middleware=True):
    context = context if context is not None else Context({})
    mock_template.render = lambda context, _: template.render(context)
    response = TemplateResponse(request, mock_template, context)
    if use_middleware:
        response.render()
        global response_stash
        response_stash = response
        response = middleware(request)
    else:
        response.render()
    return response.content.decode("utf-8")


def print_nodes(nodes: List[Node], indent=0) -> None:
    """
    Render a Nodelist, inlining child nodes with extra on separate lines and with
    extra indentation.
    """
    for node in nodes:
        child_nodes: List[Node] = []
        for attr in node.child_nodelists:
            attr_child_nodes = getattr(node, attr, None) or []
            if attr_child_nodes:
                child_nodes.extend(attr_child_nodes)

        repr = str(node)
        repr = "\n".join([(" " * 4 * indent) + line for line in repr.split("\n")])
        print(repr)
        if child_nodes:
            print_nodes(child_nodes, indent=indent + 1)


# TODO: Make sure that this is done before/after each test automatically?
@contextlib.contextmanager
def autodiscover_with_cleanup(*args, **kwargs):
    """
    Use this in place of regular `autodiscover` in test files to ensure that
    the autoimport does not pollute the global state.
    """
    imported_modules = autodiscover(*args, **kwargs)
    try:
        yield imported_modules
    finally:
        # Teardown - delete autoimported modules, so the module is executed also the
        # next time one of the tests calls `autodiscover`.
        for mod in imported_modules:
            del sys.modules[mod]


ContextBehStr = Union[ContextBehavior, str]
ContextBehParam = Union[ContextBehStr, Tuple[ContextBehStr, Any]]


def parametrize_context_behavior(cases: List[ContextBehParam], settings: Optional[Dict] = None):
    """
    Use this decorator to run a test function with django_component's
    context_behavior settings set to given values.

    You can set only a single mode:
    ```py
    @parametrize_context_behavior(["isolated"])
    def test_bla_bla(self):
        # do something with app_settings.CONTEXT_BEHAVIOR set
        # to "isolated"
        ...
    ```

    Or you can set a test to run in both modes:
    ```py
    @parametrize_context_behavior(["django", "isolated"])
    def test_bla_bla(self):
        # Runs this test function twice. Once with
        # app_settings.CONTEXT_BEHAVIOR set to "django",
        # the other time set to "isolated"
        ...
    ```

    If you need to pass parametrized data to the tests,
    pass a tuple of (mode, data) instead of plain string.
    To access the data as a fixture, add `context_behavior_data`
    as a function argument:
    ```py
    @parametrize_context_behavior([
        ("django", "result for django"),
        ("isolated", "result for isolated"),
    ])
    def test_bla_bla(self, context_behavior_data):
        # Runs this test function twice. Once with
        # app_settings.CONTEXT_BEHAVIOR set to "django",
        # the other time set to "isolated".
        #
        # `context_behavior_data` will first have a value
        # of "result for django", then of "result for isolated"
        print(context_behavior_data)
        ...
    ```

    NOTE: Use only on functions and methods. This decorator was NOT tested on classes
    """

    def decorator(test_func):
        # NOTE: Ideally this decorator would parametrize the test function
        # with `pytest.mark.parametrize`, so all test cases would be treated as separate
        # tests and thus isolated. But I wasn't able to get it to work. Hence,
        # as a workaround, we run multiple test cases within the same test run.
        # Because of this, we need to clear the loader cache, and, on error, we need to
        # propagate the info on which test case failed.
        @functools.wraps(test_func)
        def wrapper(self: BaseTestCase, *args, **kwargs):
            for case in cases:
                # Clear loader cache, see https://stackoverflow.com/a/77531127/9788634
                for engine in engines.all():
                    engine.engine.template_loaders[0].reset()

                # Reset gen_id
                self.gen_id_patcher.stop()
                self.gen_id_patcher.start()

                # Reset template cache
                from django_components.cache import component_media_cache, template_cache

                if template_cache:  # May be None if the cache was not initialized
                    template_cache.clear()

                if component_media_cache:
                    component_media_cache.clear()

                from django_components.component import component_node_subclasses_by_name
                component_node_subclasses_by_name.clear()

                case_has_data = not isinstance(case, str)

                if isinstance(case, str):
                    context_beh, fixture = case, None
                else:
                    context_beh, fixture = case

                # Set `COMPONENTS={"context_behavior": context_beh}`, but do so carefully,
                # so we override only that single setting, and so that we operate on copies
                # to avoid spilling settings across the test cases
                merged_settings = {} if not settings else settings.copy()
                if "COMPONENTS" in merged_settings:
                    merged_settings["COMPONENTS"] = merged_settings["COMPONENTS"].copy()
                else:
                    merged_settings["COMPONENTS"] = {}
                merged_settings["COMPONENTS"]["context_behavior"] = context_beh

                with override_settings(**merged_settings):
                    # Call the test function with the fixture as an argument
                    try:
                        if case_has_data:
                            test_func(self, *args, context_behavior_data=fixture, **kwargs)
                        else:
                            test_func(self, *args, **kwargs)
                    except Exception as err:
                        # Give a hint on which iteration the test failed
                        raise RuntimeError(
                            f"An error occured in test function '{test_func.__name__}' with"
                            f" context_behavior='{context_beh}'. See the original error above."
                        ) from err

        return wrapper

    return decorator
