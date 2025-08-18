from typing import Any

from asv_runner.benchmarks.timeraw import TimerawBenchmark, _SeparateProcessTimer


# Fix for https://github.com/airspeed-velocity/asv_runner/pull/44
def _get_timer(self: Any, *param: Any) -> _SeparateProcessTimer:
    """
    Returns a timer that runs the benchmark function in a separate process.

    #### Parameters
    **param** (`tuple`)
    : The parameters to pass to the benchmark function.

    #### Returns
    **timer** (`_SeparateProcessTimer`)
    : A timer that runs the function in a separate process.
    """
    if param:

        def func() -> Any:
            # ---------- OUR CHANGES: ADDED RETURN STATEMENT ----------
            return self.func(*param)
            # ---------- OUR CHANGES END ----------

    else:
        func = self.func
    return _SeparateProcessTimer(func)


TimerawBenchmark._get_timer = _get_timer
