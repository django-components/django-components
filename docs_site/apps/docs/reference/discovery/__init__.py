"""
Layer 1 of the API reference: discovery.

This package walks the public ``django_components`` API with griffe and produces
JSON-serializable ``ReferencePage`` / ``ReferenceEntry`` structures (see
``kinds.py``). It renders nothing - that is Layer 2's job (the per-kind
components under ``apps/docs/components/reference/``). Keeping discovery as a
sibling of ``components/`` enforces the discovery -> rendering split described in
``docs_site/design/DESIGN_spike_5.md`` section 5.

The contract is a plain data structure on purpose: it can be dumped to disk,
diffed between versions, and snapshot-tested without rendering anything.
"""
