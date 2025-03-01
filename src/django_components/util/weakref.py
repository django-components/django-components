import sys
from typing import Any, Dict, TypeVar, overload
from weakref import ReferenceType, finalize, ref

GLOBAL_REFS: Dict[Any, ReferenceType] = {}


T = TypeVar("T")

# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):

    @overload  # type: ignore[misc]
    def cached_ref(obj: T) -> ReferenceType[T]: ...  # noqa: E704


def cached_ref(obj: Any) -> ReferenceType:
    """
    Same as `weakref.ref()`, creating a weak reference to a given objet.
    But unlike `weakref.ref()`, this function also caches the result,
    so it returns the same reference for the same object.
    """
    if obj not in GLOBAL_REFS:
        GLOBAL_REFS[obj] = ref(obj)

    # Remove this entry from GLOBAL_REFS when the object is deleted.
    finalize(obj, lambda: GLOBAL_REFS.pop(obj))

    return GLOBAL_REFS[obj]
