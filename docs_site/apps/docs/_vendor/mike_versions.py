# Vendored from mike 2.1.3 (https://github.com/jimporter/mike), file
# `mike/versions.py`.
#
# Copyright (c) 2017-2024, Jim Porter. Licensed under the BSD-3-Clause License.
# See LICENSE-mike.txt in this directory for the full license text.
#
# Why vendored: django-components persists built docs versions to `master`
# (under docs_site/versions/) rather than a gh-pages branch, so we don't need
# mike's git or mkdocs machinery - only its version-manifest data model and the
# version ordering (dev/sentinel versions sort above releases). See
# docs_site/design/DESIGN_spike_7.md section 2.
#
# Changes from upstream:
#   - Removed `VersionInfo.get_property` / `set_property` and the `jsonpath`
#     import (mike's `props` feature; unused here).
#   - Replaced mike's `verspec.loose.LooseVersion` with the `Version` shim below,
#     backed by `packaging` (already a near-universal dep, actively maintained)
#     instead of the stale single-release `verspec`. Release versions compare as
#     PEP 440; non-PEP-440 labels (the `dev` sentinel) fall back to string
#     comparison and sort above releases - the same effect LooseVersion gave.
#   - Otherwise verbatim. Excluded from ruff/mypy (see pyproject.toml) as
#     vendored code.

import json
import re

from packaging.version import InvalidVersion
from packaging.version import Version as _Pep440Version


class Version:
    """
    Orders doc-version identifiers (drop-in for verspec's ``LooseVersion``).

    Valid PEP 440 versions (the release tags) are parsed and compared by
    ``packaging``. Identifiers that aren't valid PEP 440 - notably the ``dev``
    sentinel - keep their raw string and sort *above* any real release, matching
    the prior behavior where non-numeric labels float to the top.
    """

    _raw: str
    _parsed: "_Pep440Version | None"

    def __init__(self, version):
        if isinstance(version, Version):
            self._raw = version._raw
            self._parsed = version._parsed
            return
        self._raw = str(version)
        try:
            self._parsed = _Pep440Version(self._raw)
        except InvalidVersion:
            self._parsed = None

    def _key(self):
        # Leading flag keeps the two classes from ever being compared directly
        # (no PEP440-vs-str type error): non-PEP-440 (1) sorts above PEP 440 (0).
        # The raw string is the final tiebreaker so distinct labels never collide
        # (e.g. "0.151" vs "0.151.0", which PEP 440 considers equal).
        if self._parsed is None:
            return (1, self._raw)
        return (0, self._parsed, self._raw)

    def __str__(self):
        return self._raw

    def __repr__(self):
        return "Version({!r})".format(self._raw)

    def __hash__(self):
        return hash(self._raw)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._raw == other._raw

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() <= other._key()

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() > other._key()

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() >= other._key()


def _ensure_version(version):
    if not isinstance(version, Version):
        return Version(version)
    return version


class VersionInfo:
    def __init__(self, version, title=None, aliases=[], properties=None):
        self._check_version(str(version), 'version')
        for i in aliases:
            self._check_version(i, 'alias')

        version_name = str(version)
        self.version = _ensure_version(version)
        self.title = version_name if title is None else title
        self.aliases = set(aliases)
        self.properties = properties

        if str(self.version) in self.aliases:
            raise ValueError('duplicated version and alias')

    @classmethod
    def from_json(cls, data):
        return cls(data['version'], data['title'], data['aliases'],
                   data.get('properties'))

    def to_json(self):
        data = {'version': str(self.version),
                'title': self.title,
                'aliases': list(self.aliases)}
        if self.properties:
            data['properties'] = self.properties
        return data

    @classmethod
    def loads(cls, data):
        return cls.from_json(json.loads(data))

    def dumps(self):
        return json.dumps(self.to_json(), indent=2)

    @staticmethod
    def _check_version(version, kind):
        if ( not version or version in ['.', '..'] or
             re.search(r'[\\/]', version) ):
            raise ValueError('{!r} is not a valid {}'.format(version, kind))

    def __eq__(self, rhs):
        return (str(self.version) == str(rhs.version) and
                self.title == rhs.title and
                self.aliases == rhs.aliases and
                self.properties == rhs.properties)

    def __repr__(self):
        return '<VersionInfo({!r}, {!r}, {{{}}}{})>'.format(
            self.version, self.title, ', '.join(repr(i) for i in self.aliases),
            ', {!r}'.format(self.properties) if self.properties else ''
        )

    def update(self, title=None, aliases=[]):
        for i in aliases:
            self._check_version(i, 'alias')
        if title is not None:
            self.title = title

        aliases = set(aliases)
        if str(self.version) in aliases:
            raise ValueError('duplicated version and alias')

        added = aliases - self.aliases
        self.aliases |= aliases
        return added


class Versions:
    def __init__(self):
        self._data = {}

    @classmethod
    def from_json(cls, data):
        result = cls()
        for i in data:
            version = VersionInfo.from_json(i)
            version_str = str(version.version)
            result._ensure_unique_aliases(version_str, version.aliases)
            result._data[version_str] = version
        return result

    def to_json(self):
        return [i.to_json() for i in iter(self)]

    @classmethod
    def loads(cls, data):
        return cls.from_json(json.loads(data))

    def dumps(self):
        return json.dumps(self.to_json(), indent=2)

    def __iter__(self):
        def key(info):
            # Development versions (i.e. those without a leading digit) should
            # be treated as newer than release versions.
            return (0 if re.match(r'v?\d', str(info.version))
                    else 1, info.version)

        return (i for i in sorted(self._data.values(), reverse=True, key=key))

    def __len__(self):
        return len(self._data)

    def __getitem__(self, k):
        return self._data[str(k)]

    def find(self, identifier, strict=False):
        identifier = str(identifier)
        if identifier in self._data:
            return (identifier,)
        for k, v in self._data.items():
            if identifier in v.aliases:
                return (k, identifier)
        if strict:
            raise KeyError(identifier)
        return None

    def _ensure_unique_aliases(self, version, aliases, update_aliases=False):
        removed_aliases = []

        # Check whether `version` is already defined as an alias.
        key = self.find(version)
        if key and len(key) == 2:
            if not update_aliases:
                raise ValueError('version {!r} already exists'.format(version))
            removed_aliases.append(key)

        # Check whether any `aliases` are already defined.
        for i in aliases:
            key = self.find(i)
            if key and key[0] != version:
                if len(key) == 1:
                    raise ValueError(
                        'alias {!r} already specified as a version'.format(i)
                    )
                if not update_aliases:
                    raise ValueError(
                        'alias {!r} already exists for version {!r}'
                        .format(i, str(key[0]))
                    )
                removed_aliases.append(key)

        return removed_aliases

    def add(self, version, title=None, aliases=[], update_aliases=False):
        v = str(version)
        removed_aliases = self._ensure_unique_aliases(
            v, aliases, update_aliases
        )

        if v in self._data:
            self._data[v].update(title, aliases)
        else:
            self._data[v] = VersionInfo(version, title, aliases)

        # Remove aliases from old versions that we've moved to this version.
        for i in removed_aliases:
            self._data[i[0]].aliases.remove(i[1])

        return self._data[v]

    def update(self, identifier, title=None, aliases=[], update_aliases=False):
        key = self.find(identifier, strict=True)
        removed_aliases = self._ensure_unique_aliases(
            key[0], aliases, update_aliases
        )

        # Remove aliases from old versions that we've moved to this version.
        for i in removed_aliases:
            self._data[i[0]].aliases.remove(i[1])

        return self._data[key[0]].update(title, aliases)

    def _remove_by_key(self, key):
        if len(key) == 1:
            item = self._data[key[0]]
            del self._data[key[0]]
        else:
            item = key[1]
            self._data[key[0]].aliases.remove(key[1])
        return item

    def remove(self, identifier):
        key = self.find(identifier, strict=True)
        return self._remove_by_key(key)

    def difference_update(self, identifiers):
        keys = [self.find(i, strict=True) for i in identifiers]
        return [self._remove_by_key(i) for i in keys]
