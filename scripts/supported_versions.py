# ruff: noqa: T201, S310
import re
import textwrap
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple
from urllib import request

Version = Tuple[int, ...]
VersionMapping = Dict[Version, List[Version]]


def cut_by_content(content: str, cut_from: str, cut_to: str) -> str:
    return content.split(cut_from)[1].split(cut_to)[0]


def keys_from_content(content: str) -> List[str]:
    return re.findall(r"<td><p>(.*?)</p></td>", content)


def get_python_supported_version(url: str) -> List[Version]:
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")

    def parse_supported_versions(content: str) -> List[Version]:
        content = cut_by_content(
            content,
            '<section id="supported-versions">',
            "</table>",
        )
        content = cut_by_content(content, "<tbody>", "</tbody>")
        lines = content.split("<tr ")
        versions = [match[0] for line in lines[1:] if (match := re.findall(r"<p>([\d.]+)</p>", line))]
        versions_tuples = [version_to_tuple(version) for version in versions]
        return versions_tuples

    return parse_supported_versions(content)


def get_django_to_python_versions(url: str) -> VersionMapping:
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")

    def parse_supported_versions(content: str) -> VersionMapping:
        content = cut_by_content(
            content,
            '<span id="what-python-version-can-i-use-with-django">',
            "</table>",
        )
        content = cut_by_content(content, "<tbody>", "</tbody>")

        versions = keys_from_content(content)
        version_dict = dict(zip(versions[::2], versions[1::2]))

        django_to_python = {
            version_to_tuple(python_version): [
                version_to_tuple(version_string)
                for version_string in re.findall(r"(?<!\.)\d+\.\d+(?!\.)", django_versions)
            ]
            for python_version, django_versions in version_dict.items()
        }
        return django_to_python

    return parse_supported_versions(content)


def get_django_supported_versions(url: str) -> List[Tuple[int, ...]]:
    """Extract Django versions from the HTML content, e.g. `5.0` or `4.2`"""
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")
    content = cut_by_content(
        content,
        "<table class='django-supported-versions'>",
        "</table>",
    )

    rows = re.findall(r"<tr>(.*?)</tr>", content.replace("\n", " "))
    versions: List[Tuple[int, ...]] = []
    # NOTE: Skip first row as that's headers
    for row in rows[1:]:
        data: List[str] = re.findall(r"<td>(.*?)</td>", row)
        # NOTE: First column is version like `5.0` or `4.2 LTS`
        version_with_test = data[0]
        version = version_with_test.split(" ")[0]
        version_tuple = tuple(map(int, version.split(".")))
        versions.append(version_tuple)

    return versions


def get_latest_version(url: str) -> Version:
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")
    version_string = re.findall(r"The latest official version is (\d+\.\d)", content)[0]
    return version_to_tuple(version_string)


def version_to_tuple(version_string: str) -> Version:
    return tuple(int(num) for num in version_string.split("."))


def build_python_to_django(django_to_python: VersionMapping, latest_version: Version) -> VersionMapping:
    python_to_django: VersionMapping = defaultdict(list)
    for django_version, python_versions in django_to_python.items():
        for python_version in python_versions:
            if django_version <= latest_version:
                python_to_django[python_version].append(django_version)

    python_to_django = dict(python_to_django)
    return python_to_django


def env_format(version_tuple: Version, divider: str = "") -> str:
    return divider.join(str(num) for num in version_tuple)


def build_tox_envlist(python_to_django: VersionMapping) -> str:
    lines_data = [
        (
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"py{a}-django{{{b}}}" for a, b in lines_data]
    version_lines = "\n".join(version for version in lines)
    return "envlist = \n" + textwrap.indent(version_lines, prefix="  ")


def build_gh_actions_envlist(python_to_django: VersionMapping) -> str:
    lines_data = [
        (
            env_format(python_version, divider="."),
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"{a}: py{b}-django{{{c}}}" for a, b, c in lines_data]
    version_lines = "\n".join(version for version in lines)
    return "python = \n" + textwrap.indent(version_lines, prefix="  ")


def build_deps_envlist(python_to_django: VersionMapping) -> str:
    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    lines_data = [
        (
            env_format(django_version),
            env_format(django_version, divider="."),
            env_format((django_version[0], django_version[1] + 1), divider="."),
        )
        for django_version in sorted(all_django_versions)
    ]
    lines = [f"django{a}: Django>={b},<{c}" for a, b, c in sorted(lines_data)]
    return "deps = \n" + textwrap.indent("\n".join(lines), prefix="  ")


def build_pypi_classifiers(python_to_django: VersionMapping) -> str:
    classifiers = []

    all_python_versions = python_to_django.keys()
    for python_version in all_python_versions:
        classifiers.append(f'"Programming Language :: Python :: {env_format(python_version, divider=".")}",')

    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    for django_version in sorted(all_django_versions):
        classifiers.append(f'"Framework :: Django :: {env_format(django_version, divider=".")}",')

    return textwrap.indent("classifiers=[\n", prefix=" " * 4) + textwrap.indent("\n".join(classifiers), prefix=" " * 8)


def build_readme(python_to_django: VersionMapping) -> str:
    print(
        textwrap.dedent(
            """\
                | Python version | Django version           |
                |----------------|--------------------------|
            """.rstrip(),
        ),
    )
    lines_data = [
        (
            env_format(python_version, divider="."),
            ", ".join(env_format(version, divider=".") for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"| {a: <14} | {b: <24} |" for a, b in lines_data]
    version_lines = "\n".join(version for version in lines)
    return version_lines


def build_pyenv(python_to_django: VersionMapping) -> str:
    lines = []
    all_python_versions = python_to_django.keys()
    for python_version in all_python_versions:
        lines.append(f"pyenv install -s {env_format(python_version, divider='.')}")

    versions_str = " ".join(env_format(version, divider=".") for version in all_python_versions)
    lines.append(f"pyenv local {versions_str}")

    lines.append("tox -p")

    return "\n".join(lines)


def build_ci_python_versions(python_to_django: VersionMapping) -> str:
    # Outputs python-version, like: ['3.8', '3.9', '3.10', '3.11', '3.12']
    lines = [
        f"'{env_format(python_version, divider='.')}'" for python_version, django_versions in python_to_django.items()
    ]
    lines_formatted = " " * 8 + f"python-version: [{', '.join(lines)}]"
    return lines_formatted


def filter_dict(d: Dict, filter_fn: Callable[[Any], bool]) -> Dict:
    return dict(filter(filter_fn, d.items()))


def main() -> None:
    active_python = get_python_supported_version("https://devguide.python.org/versions/")
    django_to_python = get_django_to_python_versions("https://docs.djangoproject.com/en/dev/faq/install/")
    django_supported_versions = get_django_supported_versions("https://www.djangoproject.com/download/")
    latest_version = get_latest_version("https://www.djangoproject.com/download/")

    supported_django_to_python = filter_dict(django_to_python, lambda item: item[0] in django_supported_versions)
    python_to_django = build_python_to_django(supported_django_to_python, latest_version)

    python_to_django = filter_dict(python_to_django, lambda item: item[0] in active_python)

    tox_envlist = build_tox_envlist(python_to_django)
    print("Add this to tox.ini:\n")
    print("[tox]")
    print(tox_envlist)
    print()

    gh_actions_envlist = build_gh_actions_envlist(python_to_django)
    print("[gh-actions]")
    print(gh_actions_envlist)
    print()

    deps_envlist = build_deps_envlist(python_to_django)
    print("[testenv]")
    print(deps_envlist)
    print()
    print()

    print("Add this to pyproject.toml:\n")
    pypi_classifiers = build_pypi_classifiers(python_to_django)
    print(pypi_classifiers)
    print()
    print()

    print("Add this to docs/overview/compatibility.md:\n")
    readme = build_readme(python_to_django)
    print(readme)
    print()
    print()

    print("Add this to docs/community/development.md:\n")
    pyenv = build_pyenv(python_to_django)
    print(pyenv)
    print()
    print()

    print("Add this to tests.yml:\n")
    ci_python_versions = build_ci_python_versions(python_to_django)
    print(ci_python_versions)
    print()
    print()


if __name__ == "__main__":
    main()
