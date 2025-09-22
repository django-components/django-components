import sys
from typing import Any, Dict, TypeVar, overload
from weakref import ReferenceType, finalize, ref

GLOBAL_REFS: Dict[int, ReferenceType] = {}


T = TypeVar("T")

# NOTE: `ReferenceType` is NOT a generic pre-3.9
if sys.version_info >= (3, 9):

    @overload  # type: ignore[misc]
    def cached_ref(obj: T) -> ReferenceType[T]: ...  # type: ignore[misc]


def cached_ref(obj: Any) -> ReferenceType:
    """
    Same as `weakref.ref()`, creating a weak reference to a given object.
    But unlike `weakref.ref()`, this function also caches the result,
    so it returns the same reference for the same object.
    """
    obj_id = id(obj)
    if obj_id not in GLOBAL_REFS:
        GLOBAL_REFS[obj_id] = ref(obj)

    # Remove this entry from GLOBAL_REFS when the object is deleted.
    finalize(obj, lambda: GLOBAL_REFS.pop(obj_id, None))

    return GLOBAL_REFS[obj_id]
