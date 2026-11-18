# Security policy

## Reporting a vulnerability

**Please do not open a public issue or pull request for a security problem.**

First check that the problem still happens in the latest release (see
[Supported versions](#supported-versions)). Then report it privately through
GitHub's [private vulnerability
reporting](https://github.com/django-components/django-components/security/advisories/new):
open the repository's **Security** tab and choose **Report a vulnerability**.
That opens a private advisory that only you and the maintainers can see.

Include, as far as you can:

- the versions of django-components, Django, and Python you use,
- a description of the problem and its impact,
- steps to reproduce (a minimal component or template is ideal), and
- any workaround you know of.

## What to expect

1. We acknowledge your report in the private advisory.
2. We confirm the problem and work on a fix with you in the same advisory.
   If we decide it is not a vulnerability, we tell you there.
3. We release the fix, then publish the advisory and credit you for the
   report if you want to be named.

Please give us a reasonable time to ship a fix before you disclose the
problem publicly.

## Supported versions

django-components is in [maintenance
mode](https://django-components.github.io/django-components/docs/community/development/#what-we-accept),
and security fixes come first. We fix security problems in the latest minor
release only. If you use an older release, upgrade to the latest one and check
that the problem still happens before you report it.

The latest release also stays compatible with the Django and Python versions
that Django and Python themselves still support. The [Compatibility
page](https://django-components.github.io/django-components/docs/overview/compatibility/)
lists the supported combinations of Python and Django.

## Keep request data out of templates

Template text, component `template` strings, and the Python expressions in
tag attributes (such as `disabled=(not editable)`) are written by the
template author. Treat the template author as trusted: a template can read
and call anything in the context, including the attributes of the objects in
it, and can write any HTML, including scripts. This is Django's own rule:
[the template system isn't safe against untrusted template
authors](https://docs.djangoproject.com/en/stable/topics/templates/).

Never build a template string from request data, for example with an
f-string. Pass the data in as a template variable, a keyword argument, or
slot content passed from Python, where it is escaped by default. A report is
in scope when a value you pass as data, and have not marked safe, reaches the
page as code or unescaped markup.

## Report djc-core problems

django-components relies on
[djc-core](https://github.com/django-components/djc-core) for its Rust
parsers. Report a problem in djc-core the same way: check that it still
happens in the latest djc-core release, then report it privately through the
**Security** tab of the [djc-core
repository](https://github.com/django-components/djc-core).
