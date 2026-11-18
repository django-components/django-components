---
title: v0.126 (2025-01-29)
url: https://django-components.github.io/django-components/v/0.153.0/docs/releases/v0.126/
description: "- Replaced BeautifulSoup4 with a custom HTML parser.
- The heuristic for inserting JS and CSS dependenies into the default place has changed.
    - JS..."
---

# v0.126 (2025-01-29)

#### Refactor

- Replaced [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) with a custom HTML parser.
- The heuristic for inserting JS and CSS dependenies into the default place has changed.
    - JS is still inserted at the end of the `<body>`, and CSS at the end of `<head>`.
    - However, we find end of `<body>` by searching for **last** occurrence of `</body>`
    - And for the end of `<head>` we search for the **first** occurrence of `</head>`