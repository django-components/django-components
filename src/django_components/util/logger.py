import logging
import sys
from typing import Any, Literal

DEFAULT_TRACE_LEVEL_NUM = 5  # NOTE: MUST be lower than DEBUG which is 10

logger = logging.getLogger("django_components")
actual_trace_level_num = -1


def setup_logging() -> None:
    # Check if "TRACE" level was already defined. And if so, use its log level.
    # See https://docs.python.org/3/howto/logging.html#custom-levels
    global actual_trace_level_num  # noqa: PLW0603
    log_levels = _get_log_levels()

    if "TRACE" in log_levels:
        actual_trace_level_num = log_levels["TRACE"]
    else:
        actual_trace_level_num = DEFAULT_TRACE_LEVEL_NUM
        logging.addLevelName(actual_trace_level_num, "TRACE")


def _get_log_levels() -> dict[str, int]:
    # Use official API if possible
    if sys.version_info >= (3, 11):
        return logging.getLevelNamesMapping()
    return logging._nameToLevel.copy()


def trace(message: str, *args: Any, **kwargs: Any) -> None:
    """
    TRACE level logger.

    To display TRACE logs, set the logging level to 5.

    Example:
    ```py
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "django_components": {
                "level": 5,
                "handlers": ["console"],
            },
        },
    }
    ```

    """
    if actual_trace_level_num == -1:
        setup_logging()
    if logger.isEnabledFor(actual_trace_level_num):
        logger.log(actual_trace_level_num, message, *args, **kwargs)


def trace_node_msg(
    action: Literal["PARSE", "RENDER"],
    node_type: str,
    node_id: str,
    msg: str = "",
) -> None:
    """
    TRACE level logger with opinionated format for tracing interaction of nodes.
    Formats messages like so:

    `"PARSE slot ID 0088 ...Done!"`
    """
    action_normalized = action.ljust(6, " ")
    full_msg = f"{action_normalized} NODE {node_type} ID {node_id} {msg}"

    # NOTE: When debugging tests during development, it may be easier to change
    # this to `print()`
    trace(full_msg)


def trace_component_msg(
    action: str,
    component_name: str,
    component_id: str | None = None,
    slot_name: str | None = None,
    component_path: list[str] | None = None,
    slot_fills: dict[str, Any] | None = None,
    extra: str = "",
) -> None:
    """
    TRACE level logger with opinionated format for tracing interaction of components
    and slots. Formats messages like so:

    `"RENDER_SLOT COMPONENT 'component_name' SLOT: 'slot_name' FILLS: 'fill_name' PATH: Root > Child > Grandchild "`
    """
    component_id_str = f"ID {component_id}" if component_id else ""
    slot_name_str = f"SLOT: '{slot_name}'" if slot_name else ""
    component_path_str = "PATH: " + " > ".join(component_path) if component_path else ""
    slot_fills_str = "FILLS: " + ", ".join(slot_fills.keys()) if slot_fills else ""

    full_msg = f"{action} COMPONENT: '{component_name}' {component_id_str} {slot_name_str} {slot_fills_str} {component_path_str} {extra}"  # noqa: E501

    # NOTE: When debugging tests during development, it may be easier to change
    # this to `print()`
    trace(full_msg)
