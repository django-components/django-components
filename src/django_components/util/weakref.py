from typing import Any, Dict, TypeVar
from weakref import ReferenceType, finalize, ref

GLOBAL_REFS: Dict[Any, ReferenceType] = {}


T = TypeVar("T")


def cached_ref(obj: T) -> ReferenceType[T]:
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
