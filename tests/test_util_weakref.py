import gc
import weakref

from django_components.util.weakref import GLOBAL_REFS, cached_ref


class _Dummy:
    pass


class TestCachedRef:
    def test_returns_same_reference_on_repeated_calls(self):
        obj = _Dummy()
        r1 = cached_ref(obj)
        r2 = cached_ref(obj)
        assert r1 is r2
        assert r1() is obj

    def test_does_not_stack_finalizers_on_repeated_calls(self):
        # `cached_ref` previously attached a new `weakref.finalize` on every
        # call, even on cache hit. Each `finalize` registers a weak reference
        # to the target, so the leak shows up as a growing
        # `weakref.getweakrefcount(obj)`.
        obj = _Dummy()
        cached_ref(obj)
        baseline = weakref.getweakrefcount(obj)
        for _ in range(20):
            cached_ref(obj)
        assert weakref.getweakrefcount(obj) == baseline

    def test_global_refs_entry_removed_on_collection(self):
        obj = _Dummy()
        cached_ref(obj)
        obj_id = id(obj)
        assert obj_id in GLOBAL_REFS
        del obj
        gc.collect()
        assert obj_id not in GLOBAL_REFS
