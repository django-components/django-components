---
title: v0.117 (2024-12-08)
url: https://django-components.github.io/django-components/v/0.152.1/docs/releases/v0.117/
description: "- The HTML parser no longer erronously inserts <html><head><body> on some occasions, and
  no longer tries to close unclosed HTML tags."
---

# v0.117 (2024-12-08)

#### Fix

- The HTML parser no longer erronously inserts `<html><head><body>` on some occasions, and
  no longer tries to close unclosed HTML tags.

#### Refactor

- Replaced [Selectolax](https://github.com/rushter/selectolax) with [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) as project dependencies.