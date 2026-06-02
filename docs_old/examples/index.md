# Overview

`django-components` makes it easy to share components between projects
([See how to package components](../concepts/advanced/component_libraries.md)).

Here you will find public examples of components and component libraries.

If you have components that would be useful to others, open a [pull request](https://github.com/django-components/django-components/pulls) to add them to this collection.

## Scenarios

- [Form Submission](./form_submission/README.md) - Handle the entire form submission flow in a single file and without Django's Form class.
- [HTML fragments](./fragments/README.md) - Load HTML fragments using different client-side techniques: vanilla JavaScript, AlpineJS, and HTMX.
- [Error handling](./error_fallback/README.md) - A component that catches errors and displays fallback content, similar to React's ErrorBoundary.
- [Recursion](./recursion/README.md) - 100 nested components? Not a problem! Handle recursive rendering out of the box.
- [A/B Testing](./ab_testing/README.md) - Dynamically render different component versions. Use for A/B testing, phased rollouts, etc.
- [Analytics](./analytics/README.md) - Track component errors or success rates to send them to Sentry or other services.

## Components

- [FormGrid](./form_grid/README.md) - A form component that automatically generates labels and arranges fields in a grid.
- [Tabs (AlpineJS)](./tabs/README.md) - Dynamic tabs with [AlpineJS](https://alpinejs.dev/).

## Packages

Packages or projects that define components for django-components:

- [`djc-heroicons`](https://pypi.org/project/djc-heroicons/) - Icons from HeroIcons.com for django-components.
- [`django-htmx-components`](https://github.com/iwanalabs/django-htmx-components) - A set of components for use with [htmx](https://htmx.org/).
