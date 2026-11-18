---
title: v0.141.3 (2025-08-14)
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.141.3/
description: "- You no longer need to render the whole page with the document strategy to use HTML fragments."
---

# v0.141.3 (2025-08-14)

#### Feat

- You no longer need to render the whole page with the `document` strategy to use HTML fragments.

    Previously, if you wanted to insert rendered components as HTML fragments, you had to ensure
    that the HTML document it was being inserted into was rendered with the `document` strategy.

    Now, when you render components with `fragment` strategy, they know how to fetch their own JS / CSS dependencies.

#### Fix

- Fix compatibility with django-template-partials ([#1322](https://github.com/django-components/django-components/issues/1322))