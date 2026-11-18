---
title: v0.152.1
url: https://django-components.github.io/django-components/v/1.0.0/docs/releases/v0.152.1/
description: "This release fixes several security problems. Most of them matter only when data from a request or from storage reaches a component, or when a page..."
---

# v0.152.1

This release fixes several security problems. Most of them matter only when data from a request or from storage reaches a component, or when a page already has an HTML injection problem. Some fixes change behavior: read "What you may need to change" below before you upgrade.

#### Fix

- **Data from a request can no longer run code or change the page through attributes, CSS or error fallbacks**

    This fixes several ways for data from a request or from storage to run in the browser or change the page.

    - A `get_css_data()` value or key can no longer end its declaration, add a CSS rule, or end the `<style>`
      tag, and such a value no longer makes the page fail with a 500. Text that does not read as one CSS value
      becomes a quoted CSS string, so `red;}body{display:none}` is now plain text.

    - `{% html_attrs %}`, `{% attrs %}`, `format_attributes()`, `compose_attrs()` and `merge_attributes()` now
      raise `ValueError` for an attribute name in a mapping that can run code or that django-components reserves:
      any name that starts with `on` or `data-djc-`, and the names `srcdoc`, `innerHTML`, `outerHTML`, `data-djc`
      and `djc-render-id`, in any letter case. Control characters such as a form feed and quotes are refused in
      every name.

    - `{% html_attrs %}`, `{% attrs %}`, `AttrsDict`, `format_attributes()` and django-components' `Script` and
      `Style` tags now escape an attribute value marked safe, such as the result of `mark_safe()` or `format_html()`. Before, a `"`
      in it ended the attribute and could add another one, such as `onmouseover`. django-components first turns
      the character references in such a value back into characters, so `mark_safe("Tom &amp; Jerry")` still
      shows `Tom & Jerry`. An ESC character in any attribute value is now written as `&#27;`, so a page read as
      ISO-2022-JP keeps its quotes.

    - The `fallback` argument of `ErrorFallback` is now escaped.

    - Component JS and CSS files served from `/components/cache/` now say `charset=utf-8`.

    - With debug highlighting on, a slot or component name can no longer end the `<style>` tag.

    These checks do not know the names that run code in other libraries, such as `@click` in Alpine.js, and
    they do not check a URL in `href`. Do not pass a mapping whose keys come from a request. See
    [HTML attributes](https://django-components.github.io/django-components/docs/concepts/fundamentals/html_attributes/).

- **Values from `get_js_data()` and `get_css_data()` no longer reach the wrong visitor**

    These values are stored under a key made from the values, and that key was short. Two different values could get the same key, and then a page got the values that were stored first, which could be another visitor's. Anyone could also read every stored value by trying all the keys.

    The key is now 128 bits long, which puts both out of reach in practice. Pages that use these values get a little larger.

    Nobody can check a guess at your values through their URL anymore. Before, anyone could work out the URL for values that they guessed, and the response from that URL told them whether some visitor's page used those values. The URL now depends on your `SECRET_KEY`.

    The values stay public: anyone with their URL can read them, with no login, and so can other websites that load the URL in a page. So never return a secret from these methods. Read more in [JS and CSS variables are public](https://django-components.github.io/django-components/docs/concepts/fundamentals/html_js_css_variables/#js-and-css-variables-are-public).

- **`Component.Cache` no longer mixes up inputs that look alike**

    With the default `Cache.hash()`, the inputs `name="a,role-b", role="c"` and `name="a", role="b,role-c"` shared one cache entry, so the second render returned the HTML of the first. The same happened with `None` and `"None"`, and with `1` and `"1"`.

- **A long URL under `/components/cache/` no longer keeps the server busy**

    Rejecting a long URL took time that grew with the cube of its length. These URLs now accept only the file names that django-components generates: the extension must be `js` or `css`, and for values from `get_js_data()` or `get_css_data()`, the part between the component ID and the extension must be exactly 32 lowercase hexadecimal characters. Other paths give a 404.

- **Long `style` values no longer keep the server busy**

    In `{% html_attrs %}`, `{% attrs %}` and `parse_string_style()`, the time grew with the square of the length. It now grows in step with the length, and the parsed result does not change.

- **Values from `get_js_data()` and `get_css_data()` no longer fill up the server's memory**

    With the default in-memory cache, each server process now keeps them for 24 hours after they were last used, and uses at most about 64 MiB for them. Your `Component.js` and `Component.css` are not affected.

- **A failed render no longer stays in memory**

    When a component raised an error while other components in the same render were still waiting their turn, those components and their inputs stayed in memory for the life of the server process.

- **One component's missing JS variables no longer stop the rest of the page**

    Before, `$onComponent` callbacks of that component and of every later component on the page did not run, and nothing was logged. Now only that component's callbacks are skipped, and a warning is logged.

- **Injected HTML has fewer ways to change how the dependency manager loads**

    The dependency manager is `django_components.min.js`, the file that loads each component's JS and CSS in the browser. This fix matters when a page has an HTML injection problem and uses a Content Security Policy with a nonce.

    An injected `<base>` tag can no longer make the browser run `django_components.min.js`, or a fragment's files from `/components/cache/`, from another site. These tags now carry `integrity` and `crossorigin="anonymous"`, and the URL of `django_components.min.js` gets a `?v=` version.

    On a page whose policy refuses scripts without a nonce, an injected `<script data-djc>` block no longer tells the dependency manager what to load or which components to call. When the dependency manager's tag has a nonce, it obeys only a block with the same nonce in its JSON. django-components writes that nonce for you, from the nonce your hook puts on its scripts.

- **On a page without a nonce, injected HTML can no longer make the dependency manager load scripts from anywhere**

    This matters when a page has an HTML injection problem and its Content Security Policy lists hashes or `'self'` instead of a nonce. With hashes and `'strict-dynamic'`, an injected `<script data-djc>` block could run a script from any site. With `'self'`, HTML that your own JS inserts could run any file on your site, such as one a visitor uploaded.

    When the dependency manager's tag has no nonce, a `<script data-djc>` block now loads only component JS files from `/components/cache/` on the page's origin and files under `STATIC_URL`. It ignores a block that holds JS variables, which django-components never writes.

- **Python expressions in template tags refuse Django lazy objects and Django's formatting functions**

    Python expressions now raise `SecurityError` when they read an attribute of a Django lazy object, such as
    the result of `_("...")` or `gettext_lazy()`, or when they call `format_html()`, `format_html_join()` or
    `format_lazy()`. This includes a function from the context that wraps one of these, for example with
    `functools.partial()`, `functools.lru_cache()` or Django's `lazy()`. These could fill in placeholders that
    read values such as settings.

    django-components now requires djc-core 1.4.0 or later, which closes related gaps in its own checks, and also refuses tag values nested more than 16 levels deep (lists, dicts, parentheses and filters each count as a level).

- `ComponentMediaInputPath` now includes Django's `Script` from `django.forms.widgets`, so `django-stubs` accepts `Script("calendar/x.js", type="module")` where `ComponentMediaInputPath` is expected.

- `@djc_test` no longer causes `KeyError` on imports from a component directory without `__init__.py`. The error could appear in a later test, depending on test order, for example under `pytest-xdist`.

#### Refactor

- Add support for Django 6.1 (on Python 3.12 and newer). If you set a custom `Component.media_class`, see "What you may need to change" below.

#### What you may need to change

**Attribute names from Python code.** Names written in a template tag keep working, such as `{% html_attrs onclick="save()" %}` and `attrs:onclick="save()"`. If your Python code puts such a name in a mapping, wrap it in `TrustedAttrName`. Never wrap a name that comes from a request. For a dictionary written in a tag, use `attrs:onclick="..."`, or write `onclick="..."` on the element itself:


```py
# Before
attrs = {"onclick": "save()"}

# After
from django_components import TrustedAttrName

attrs = {TrustedAttrName("onclick"): "save()"}
```


**Attribute values marked safe.** If you used one value marked safe to write several attributes, such as `mark_safe('a" data-x="b')`, pass each attribute as its own key instead. The browser reads other marked-safe values as before, but the HTML may be spelled differently, for example `&#x27;` for `'`, so HTML snapshots in your tests may need updating.

**`get_css_data()` values.** A value such as `red;` or `red!important` is now quoted, and no longer works as a color. CSS variables are now written from the JSON form of the values, so `(1, 2)` gives `[1, 2]`, and a key of `True` or `None` gives `--true` or `--null`. If your CSS uses `var(--True)`, use a string key.

**`ErrorFallback`.** If your `fallback` contains HTML, mark it as safe, or use the `fallback` slot:


```django
{% component "error_fallback" fallback="<b>Oops</b>"|safe %}
```


**URLs of `get_js_data()` and `get_css_data()` values.** After you change `SECRET_KEY`, new pages get new URLs, and the URLs in older pages keep working for as long as the server still has their values in its cache. If `SECRET_KEY` is empty, each server process makes its own random secret, so the same values get a different URL in each process and after each restart, and pages keep working. Tests that compare rendered HTML with these URLs need a fixed `SECRET_KEY`.

**Cached HTML from 0.152.0 or earlier.** Versions 0.152.0 and earlier stored `get_js_data()` and `get_css_data()` values under a 6-character name, which anyone can guess. The server now refuses such names and never reads the values stored under them, even while they are still in the cache. So HTML that one of those versions rendered and that is still cached, for example by `{% cache %}` or `Component.Cache`, loses these values until it expires: a warning is logged, that component's `$onComponent` callbacks do not run, and its CSS variables are unset. To render those pages again sooner, clear the cache that holds their HTML.

If you set `COMPONENTS.cache`, the old values stay in it until they expire, and with `"TIMEOUT": None` they never do. Nobody can read them anymore, but they take up space, and going back to an older version would serve them again. To remove them, clear that cache. This removes everything in it, so take care if your app uses it for other data.

**`Component.Cache` entries.** Each entry already in your cache gets a new key, so it is rendered again once, and the old entry stays until it expires. If your `Cache.hash()` or `Cache.hash_slots()` calls `super()` and reads the result, note that `hash()` now returns two JSON arrays joined by a colon, and `hash_slots()` returns one JSON array.

**How long `get_js_data()` and `get_css_data()` values are kept.** If values are gone when a page needs them, a warning is logged, that component's `$onComponent` callbacks do not run, and its CSS variables are unset, until a render produces the same values again. This can affect `{% cache %}` fragments and `Component.Cache` entries that go unused for 24 hours, and very busy sites. To raise these limits, set the new `vars_cache_max_age` and `vars_cache_max_bytes` settings.

If you set `COMPONENTS.cache`, nothing changes: that cache's own `TIMEOUT` and size limits still apply. With `"TIMEOUT": None` and no size limit, these entries are never removed, so set at least one of them.

**`django_components.min.js` and fragment files now carry `integrity`.** Run `collectstatic` when you upgrade and clear any CDN or whole-page cache, because the browser refuses a file with different bytes. A proxy that rewrites JS files breaks the same way. A `STATIC_URL` that is a full URL keeps its plain tag. If a hook compares `script.url` with the URL of this file, allow for the `?v=`.

**Pages with a nonce.** If you add a nonce with the `on_dependencies` hook and use fragments or swap whole pages with JS, render the new HTML with the nonce of the page it goes into. Other HTML no longer starts, and the browser console shows an error. See [Content Security Policy](https://django-components.github.io/django-components/docs/concepts/advanced/rendering_js_css/#content-security-policy).

Add `base-uri 'self'` to your policy as well. It is what protects files from `Component.Media`, which carry no hash.

**Pages without a nonce.** A fragment's `Component.Media.js` now loads only files under `STATIC_URL`. A script from a CDN or from another path on your site, such as `/jsi18n/`, doesn't load, even on a site with no policy. With `STATIC_URL = "/"`, a `type="module"` dependency manager tag, a tag on another host that a hook gave an `integrity`, a dependency manager file served from another folder, or a dependency manager URL with `%` in its path, even files under `STATIC_URL` don't load. The fragment's components still run, but their JS fails where it needs the skipped script. The browser console shows an error, and the server logs a warning. Load the script on the page itself, serve it from `STATIC_URL`, or give the page a nonce. See [Pages without a nonce](https://django-components.github.io/django-components/docs/concepts/advanced/rendering_js_css/#pages-without-a-nonce).

**Lazy strings and formatting in Python expressions in template tags.** To use string methods on a lazy string, put it in an f-string first: `(f"{text}".upper())`. To fill in placeholders, or to call `format_html()`, do it in `get_template_data()`. The error message says which of these to do.

**A custom `Component.media_class` on Django 6.1.** If you set [`Component.media_class`](https://django-components.github.io/django-components/docs/concepts/fundamentals/secondary_js_css_files/#change-how-every-file-is-rendered) to a `Media` subclass that overrides `render_js()` or `render_css()`, update it for Django 6.1:

- Accept the `attrs` keyword argument. Without it, `print(MyComponent.media)` raises `TypeError`.


    ```py
    class MyMedia(Media):
        def render_js(self, *, attrs=None):
            ...
    ```


- Handle Django's `Script` and `Stylesheet` objects, which `self._js` and `self._css` now hold instead of strings. Otherwise `absolute_path()` raises `AttributeError`, or your custom tags are lost with no error.

The docs show overrides that work on Django 5.2, 6.0 and 6.1.