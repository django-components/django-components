---
title: Security notes 🚨
url: https://django-components.github.io/django-components/v/1.0.0/docs/overview/security_notes/
description: "It is strongly recommended to read this section before using django-components in production."
---

_It is strongly recommended to read this section before using django-components in production._

## Static files

**TL;DR: No action needed on v0.100 or later. On an older release, see [Pre-v0.100 static files](../upgrading/v0.md#static-files-before-v0100).**

Components can be organized however you prefer.
That said, our prefered way is to keep the files of a component close together by bundling them in the same directory.

This means that files containing backend logic, such as Python modules and HTML templates, live in the same directory as static files, e.g. JS and CSS.

From v0.100 onwards, we keep component files (as defined by
[`COMPONENTS.dirs`][ComponentsSettings.dirs]
and [`COMPONENTS.app_dirs`][ComponentsSettings.app_dirs])
separate from the rest of the static
files (defined by `STATICFILES_DIRS`). That way, the Python and HTML files are NOT exposed by the server. Only the static JS, CSS, and
[other common formats][ComponentsSettings.static_files_allowed].

!!! note

    If you need to expose different file formats, you can configure these with
    [`COMPONENTS.static_files_allowed`][ComponentsSettings.static_files_allowed]
    and [`COMPONENTS.static_files_forbidden`][ComponentsSettings.static_files_forbidden].

For a step-by-step guide on deploying production server with static files,
[see the demo project](https://github.com/django-components/django-components/tree/master/sampleproject).

## Reporting a vulnerability

Report a security problem in django-components privately through GitHub, not in a public issue. The [security policy](https://github.com/django-components/django-components/blob/master/SECURITY.md) has the steps, says which release gets security fixes, and says what to expect.