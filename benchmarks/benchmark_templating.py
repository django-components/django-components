# Write the benchmarking functions here
# See "Writing benchmarks" in the asv docs for more information.

import re
from pathlib import Path
from types import ModuleType
from typing import Literal

# Fix for for https://github.com/airspeed-velocity/asv_runner/pull/44
import benchmarks.monkeypatch_asv  # noqa: F401

from benchmarks.utils import benchmark, create_virtual_module


DJC_VS_DJ_GROUP = "Components vs Django"
DJC_ISOLATED_VS_NON_GROUP = "isolated vs django modes"
OTHER_GROUP = "Other"


DjcContextMode = Literal["isolated", "django"]
TemplatingRenderer = Literal["django", "django-components", "none"]
TemplatingTestSize = Literal["lg", "sm"]
TemplatingTestType = Literal[
    "first",  # Testing performance of the first time the template is rendered
    "subsequent",  # Testing performance of the subsequent times the template is rendered
    "startup",  # Testing performance of the startup time (e.g. defining classes and templates)
]


def _get_templating_filepath(renderer: TemplatingRenderer, size: TemplatingTestSize) -> Path:
    if renderer == "none":
        raise ValueError("Cannot get filepath for renderer 'none'")
    elif renderer not in ["django", "django-components"]:
        raise ValueError(f"Invalid renderer: {renderer}")

    if size not in ("lg", "sm"):
        raise ValueError(f"Invalid size: {size}, must be one of ('lg', 'sm')")

    # At this point, we know the renderer is either "django" or "django-components"
    root = file_path = Path(__file__).parent.parent
    if renderer == "django":
        if size == "lg":
            file_path = root / "tests" / "test_benchmark_django.py"
        else:
            file_path = root / "tests" / "test_benchmark_django_small.py"
    else:
        if size == "lg":
            file_path = root / "tests" / "test_benchmark_djc.py"
        else:
            file_path = root / "tests" / "test_benchmark_djc_small.py"

    return file_path


def _get_templating_script(
    renderer: TemplatingRenderer,
    size: TemplatingTestSize,
    context_mode: DjcContextMode,
    imports_only: bool,
) -> str:
    if renderer == "none":
        return ""
    elif renderer not in ["django", "django-components"]:
        raise ValueError(f"Invalid renderer: {renderer}")

    # At this point, we know the renderer is either "django" or "django-components"
    file_path = _get_templating_filepath(renderer, size)
    contents = file_path.read_text()

    # The files with benchmarked code also have a section for testing them with pytest.
    # We remove that pytest section, so the script is only the benchmark code.
    contents = contents.split("# ----------- TESTS START ------------ #")[0]

    if imports_only:
        # There is a benchmark test for measuring the time it takes to import the module.
        # For that, we exclude from the code everything AFTER this line
        contents = contents.split("# ----------- IMPORTS END ------------ #")[0]
    else:
        # Set the context mode by replacing variable in the script
        contents = re.sub(r"CONTEXT_MODE.*?\n", f"CONTEXT_MODE = '{context_mode}'\n", contents, count=1)

    return contents


def _get_templating_module(
    renderer: TemplatingRenderer,
    size: TemplatingTestSize,
    context_mode: DjcContextMode,
    imports_only: bool,
) -> ModuleType:
    if renderer not in ("django", "django-components"):
        raise ValueError(f"Invalid renderer: {renderer}")

    file_path = _get_templating_filepath(renderer, size)
    script = _get_templating_script(renderer, size, context_mode, imports_only)

    # This makes it possible to import the module in the benchmark function
    # as `import test_templating`
    module = create_virtual_module("test_templating", script, str(file_path))
    return module


# The `timeraw_` tests run in separate processes. But when running memory benchmarks,
# the tested logic runs in the same process as the where we run the benchmark functions
# (e.g. `peakmem_render_lg_first()`). Thus, the `peakmem_` functions have access to this file
# when the tested logic runs.
#
# Secondly, `asv` doesn't offer any way to pass data from `setup` to actual test.
#
# And so we define this global, which, when running memory benchmarks, the `setup` function
# populates. And then we trigger the actual render from within the test body.
do_render = lambda: None  # noqa: E731


def setup_templating_memory_benchmark(
    renderer: TemplatingRenderer,
    size: TemplatingTestSize,
    test_type: TemplatingTestType,
    context_mode: DjcContextMode,
    imports_only: bool = False,
):
    global do_render
    module = _get_templating_module(renderer, size, context_mode, imports_only)
    data = module.gen_render_data()
    render = module.render
    do_render = lambda: render(data)  # noqa: E731

    # Do the first render as part of setup if we're testing the subsequent renders
    if test_type == "subsequent":
        do_render()


# The timing benchmarks run the actual code in a separate process, by using the `timeraw_` prefix.
# As such, we don't actually load the code in this file. Instead, we only prepare a script (raw string)
# that will be run in the new process.
def prepare_templating_benchmark(
    renderer: TemplatingRenderer,
    size: TemplatingTestSize,
    test_type: TemplatingTestType,
    context_mode: DjcContextMode,
    imports_only: bool = False,
):
    global do_render
    setup_script = _get_templating_script(renderer, size, context_mode, imports_only)

    # If we're testing the startup time, then the setup is actually the tested code
    if test_type == "startup":
        return setup_script
    else:
        # Otherwise include also data generation as part of setup
        setup_script += "\n\n" "render_data = gen_render_data()\n"

        # Do the first render as part of setup if we're testing the subsequent renders
        if test_type == "subsequent":
            setup_script += "render(render_data)\n"

        benchmark_script = "render(render_data)\n"
        return benchmark_script, setup_script


# - Group: django-components vs django
#    - time: djc vs django (startup lg)
#    - time: djc vs django (lg - FIRST)
#    - time: djc vs django (sm - FIRST)
#    - time: djc vs django (lg - SUBSEQUENT)
#    - time: djc vs django (sm - SUBSEQUENT)
#    - mem:  djc vs django (lg - FIRST)
#    - mem:  djc vs django (sm - FIRST)
#    - mem:  djc vs django (lg - SUBSEQUENT)
#    - mem:  djc vs django (sm - SUBSEQUENT)
#
# NOTE: While the name suggests we're comparing Django and Django-components, be aware that
#       in our "Django" tests, we still install and import django-components. We also use
#       django-components's `{% html_attrs %}` tag in the Django scenario. `{% html_attrs %}`
#       was used because the original sample code was from django-components.
#
#       As such, these tests should seen not as "Using Django vs Using Components". But instead,
#       it should be "What is the relative cost of using Components?".
#
#       As an example, the benchmarking for the startup time and memory usage is not comparing
#       two independent approaches. Rather, the test is checking if defining Components classes
#       is more expensive than vanilla Django templates.
class DjangoComponentsVsDjangoTests:
    # Testing startup time (e.g. defining classes and templates)
    @benchmark(
        pretty_name="startup - large",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
    )
    def timeraw_startup_lg(self, renderer: TemplatingRenderer):
        return prepare_templating_benchmark(renderer, "lg", "startup", "isolated")

    @benchmark(
        pretty_name="render - small - first render",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
    )
    def timeraw_render_sm_first(self, renderer: TemplatingRenderer):
        return prepare_templating_benchmark(renderer, "sm", "first", "isolated")

    @benchmark(
        pretty_name="render - small - second render",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
    )
    def timeraw_render_sm_subsequent(self, renderer: TemplatingRenderer):
        return prepare_templating_benchmark(renderer, "sm", "subsequent", "isolated")

    @benchmark(
        pretty_name="render - large - first render",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
    )
    def timeraw_render_lg_first(self, renderer: TemplatingRenderer):
        return prepare_templating_benchmark(renderer, "lg", "first", "isolated")

    @benchmark(
        pretty_name="render - large - second render",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
    )
    def timeraw_render_lg_subsequent(self, renderer: TemplatingRenderer):
        return prepare_templating_benchmark(renderer, "lg", "subsequent", "isolated")

    @benchmark(
        pretty_name="render - small - first render (mem)",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
        setup=lambda renderer: setup_templating_memory_benchmark(renderer, "sm", "first", "isolated"),
    )
    def peakmem_render_sm_first(self, renderer: TemplatingRenderer):
        do_render()

    @benchmark(
        pretty_name="render - small - second render (mem)",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
        setup=lambda renderer: setup_templating_memory_benchmark(renderer, "sm", "subsequent", "isolated"),
    )
    def peakmem_render_sm_subsequent(self, renderer: TemplatingRenderer):
        do_render()

    @benchmark(
        pretty_name="render - large - first render (mem)",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
        setup=lambda renderer: setup_templating_memory_benchmark(renderer, "lg", "first", "isolated"),
    )
    def peakmem_render_lg_first(self, renderer: TemplatingRenderer):
        do_render()

    @benchmark(
        pretty_name="render - large - second render (mem)",
        group_name=DJC_VS_DJ_GROUP,
        number=1,
        rounds=5,
        params={
            "renderer": ["django", "django-components"],
        },
        setup=lambda renderer: setup_templating_memory_benchmark(renderer, "lg", "subsequent", "isolated"),
    )
    def peakmem_render_lg_subsequent(self, renderer: TemplatingRenderer):
        do_render()


# - Group: Django-components "isolated" vs "django" modes
#    - time: Isolated vs django djc (startup lg)
#    - time: Isolated vs django djc (lg - FIRST)
#    - time: Isolated vs django djc (sm - FIRST)
#    - time: Isolated vs django djc (lg - SUBSEQUENT)
#    - time: Isolated vs django djc (sm - SUBSEQUENT)
#    - mem:  Isolated vs django djc (lg - FIRST)
#    - mem:  Isolated vs django djc (sm - FIRST)
#    - mem:  Isolated vs django djc (lg - SUBSEQUENT)
#    - mem:  Isolated vs django djc (sm - SUBSEQUENT)
class IsolatedVsDjangoContextModesTests:
    # Testing startup time (e.g. defining classes and templates)
    @benchmark(
        pretty_name="startup - large",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
    )
    def timeraw_startup_lg(self, context_mode: DjcContextMode):
        return prepare_templating_benchmark("django-components", "lg", "startup", context_mode)

    @benchmark(
        pretty_name="render - small - first render",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
    )
    def timeraw_render_sm_first(self, context_mode: DjcContextMode):
        return prepare_templating_benchmark("django-components", "sm", "first", context_mode)

    @benchmark(
        pretty_name="render - small - second render",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
    )
    def timeraw_render_sm_subsequent(self, context_mode: DjcContextMode):
        return prepare_templating_benchmark("django-components", "sm", "subsequent", context_mode)

    @benchmark(
        pretty_name="render - large - first render",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
    )
    def timeraw_render_lg_first(self, context_mode: DjcContextMode):
        return prepare_templating_benchmark("django-components", "lg", "first", context_mode)

    @benchmark(
        pretty_name="render - large - second render",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
    )
    def timeraw_render_lg_subsequent(self, context_mode: DjcContextMode):
        return prepare_templating_benchmark("django-components", "lg", "subsequent", context_mode)

    @benchmark(
        pretty_name="render - small - first render (mem)",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
        setup=lambda context_mode: setup_templating_memory_benchmark("django-components", "sm", "first", context_mode),
    )
    def peakmem_render_sm_first(self, context_mode: DjcContextMode):
        do_render()

    @benchmark(
        pretty_name="render - small - second render (mem)",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
        setup=lambda context_mode: setup_templating_memory_benchmark(
            "django-components",
            "sm",
            "subsequent",
            context_mode,
        ),
    )
    def peakmem_render_sm_subsequent(self, context_mode: DjcContextMode):
        do_render()

    @benchmark(
        pretty_name="render - large - first render (mem)",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
        setup=lambda context_mode: setup_templating_memory_benchmark(
            "django-components",
            "lg",
            "first",
            context_mode,
        ),
    )
    def peakmem_render_lg_first(self, context_mode: DjcContextMode):
        do_render()

    @benchmark(
        pretty_name="render - large - second render (mem)",
        group_name=DJC_ISOLATED_VS_NON_GROUP,
        number=1,
        rounds=5,
        params={
            "context_mode": ["isolated", "django"],
        },
        setup=lambda context_mode: setup_templating_memory_benchmark(
            "django-components",
            "lg",
            "subsequent",
            context_mode,
        ),
    )
    def peakmem_render_lg_subsequent(self, context_mode: DjcContextMode):
        do_render()


class OtherTests:
    @benchmark(
        pretty_name="import time",
        group_name=OTHER_GROUP,
        number=1,
        rounds=5,
    )
    def timeraw_import_time(self):
        return prepare_templating_benchmark("django-components", "lg", "startup", "isolated", imports_only=True)
