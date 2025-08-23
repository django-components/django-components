import os
import sys
from importlib.abc import Loader
from importlib.util import module_from_spec, spec_from_loader
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional


# NOTE: benchmark_name constraints:
# - MUST BE UNIQUE
# - MUST NOT CONTAIN `-`
# - MUST START WITH `time_`, `mem_`, `peakmem_`
# See https://github.com/airspeed-velocity/asv/pull/1470
def benchmark(
    *,
    pretty_name: Optional[str] = None,
    timeout: Optional[int] = None,
    group_name: Optional[str] = None,
    params: Optional[Dict[str, List[Any]]] = None,
    number: Optional[int] = None,
    min_run_count: Optional[int] = None,
    include_in_quick_benchmark: bool = False,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # For pull requests, we want to run benchmarks only for a subset of tests,
        # because the full set of tests takes about 10 minutes to run (5 min per commit).
        # This is done by setting DJC_BENCHMARK_QUICK=1 in the environment.
        if os.getenv("DJC_BENCHMARK_QUICK") and not include_in_quick_benchmark:
            # By setting the benchmark name to something that does NOT start with
            # valid prefixes like `time_`, `mem_`, or `peakmem_`, this function will be ignored by asv.
            func.benchmark_name = "noop"  # type: ignore[attr-defined]
            return func

        # "group_name" is our custom field, which we actually convert to asv's "benchmark_name"
        if group_name is not None:
            benchmark_name = f"{group_name}.{func.__name__}"
            func.benchmark_name = benchmark_name  # type: ignore[attr-defined]

        # Also "params" is custom, so we normalize it to "params" and "param_names"
        if params is not None:
            func.params, func.param_names = list(params.values()), list(params.keys())  # type: ignore[attr-defined]

        if pretty_name is not None:
            func.pretty_name = pretty_name  # type: ignore[attr-defined]
        if timeout is not None:
            func.timeout = timeout  # type: ignore[attr-defined]
        if number is not None:
            func.number = number  # type: ignore[attr-defined]
        if min_run_count is not None:
            func.min_run_count = min_run_count  # type: ignore[attr-defined]

        # Additional, untyped kwargs
        for k, v in kwargs.items():
            setattr(func, k, v)

        return func

    return decorator


class VirtualModuleLoader(Loader):
    def __init__(self, code_string: str) -> None:
        self.code_string = code_string

    def exec_module(self, module: ModuleType) -> None:
        exec(self.code_string, module.__dict__)  # noqa: S102


def create_virtual_module(name: str, code_string: str, file_path: str) -> ModuleType:
    """
    To avoid the headaches of importing the tested code from another diretory,
    we create a "virtual" module that we can import from anywhere.

    E.g.
    ```py
    from benchmarks.utils import create_virtual_module

    create_virtual_module("my_module", "print('Hello, world!')", __file__)

    # Now you can import my_module from anywhere
    import my_module
    ```
    """
    # Create the module specification
    spec = spec_from_loader(name, VirtualModuleLoader(code_string))

    # Create the module
    module = module_from_spec(spec)  # type: ignore[arg-type]
    module.__file__ = file_path
    module.__name__ = name

    # Add it to sys.modules
    sys.modules[name] = module

    # Execute the module
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    return module
