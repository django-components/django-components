---
title: Settings
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/settings/
description: "API reference - the django-components settings."
---

# Settings

Configure django-components through the `COMPONENTS` dict (or a [`ComponentsSettings`][ComponentsSettings] instance) in your Django settings. Every field below is one such setting.

## Settings defaults

An overview of all settings and their default values:


```py
defaults = ComponentsSettings(
    autodiscover=True,
    cache=None,
    context_behavior=ContextBehavior.DJANGO.value,  # "django" | "isolated"
    # Root-level "components" dirs, e.g. `/path/to/proj/components/`
    dirs=[Path(settings.BASE_DIR) / "components"],
    # App-level "components" dirs, e.g. `[app]/components/`
    app_dirs=["components"],
    debug_highlight_components=False,
    debug_highlight_slots=False,
    dynamic_component_name="dynamic",
    extensions=[],
    extensions_defaults={},
    libraries=[],  # E.g. ["mysite.components.forms", ...]
    multiline_tags=True,
    reload_on_file_change="hot",
    static_files_allowed=[
        ".css",
        ".js", ".jsx", ".ts", ".tsx",
        # Images
        ".apng", ".png", ".avif", ".gif", ".jpg",
        ".jpeg", ".jfif", ".pjpeg", ".pjp", ".svg",
        ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff",
        # Fonts
        ".eot", ".ttf", ".woff", ".otf", ".svg",
    ],
    static_files_forbidden=[
        # See https://marketplace.visualstudio.com/items?itemName=junstyle.vscode-django-support
        ".html", ".django", ".dj", ".tpl",
        # Python files
        ".py", ".pyc",
    ],
    tag_formatter="django_components.component_formatter",
    template_cache_size=128,
    vars_cache_max_age=24 * 60 * 60,
    vars_cache_max_bytes=64 * 1024 * 1024,
)
```





<div class="doc doc-object doc-setting" data-djc-id-ce8jUku="">
<h2 id="extensions" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.extensions" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">extensions</span>
<a class="headerlink" href="#extensions" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>extensions: <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#ComponentExtension">ComponentExtension</a>] | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>] | None</code></pre></div>
<p>List of <a href="../concepts/advanced/extensions.md">extensions</a> to be loaded.</p>
<p>The extensions can be specified as:</p>
<ul>
<li>Python import path, e.g. <code>"path.to.my_extension.MyExtension"</code>.</li>
<li>Extension class, e.g. <code>my_extension.MyExtension</code>.</li>
</ul>
<p>Read more about <a href="../concepts/advanced/extensions.md">extensions</a>.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">extensions</span><span class="o">=</span><span class="p">[</span>
        <span class="s2">"path.to.my_extension.MyExtension"</span><span class="p">,</span>
        <span class="n">StorybookExtension</span><span class="p">,</span>
    <span class="p">],</span>
<span class="p">)</span>
</code></pre></div></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cM9aQK3="">
<h2 id="extensions_defaults" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.extensions_defaults" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">extensions_defaults</span>
<a class="headerlink" href="#extensions_defaults" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>extensions_defaults: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>] | None</code></pre></div>
<p>Global defaults for the extension classes.</p>
<p>Read more about <a href="../concepts/advanced/extensions.md#extension-defaults">Extension defaults</a>.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">extensions_defaults</span><span class="o">=</span><span class="p">{</span>
        <span class="s2">"my_extension"</span><span class="p">:</span> <span class="p">{</span>
            <span class="s2">"my_setting"</span><span class="p">:</span> <span class="s2">"my_value"</span><span class="p">,</span>
        <span class="p">},</span>
        <span class="s2">"cache"</span><span class="p">:</span> <span class="p">{</span>
            <span class="s2">"enabled"</span><span class="p">:</span> <span class="kc">True</span><span class="p">,</span>
            <span class="s2">"ttl"</span><span class="p">:</span> <span class="mi">60</span><span class="p">,</span>
        <span class="p">},</span>
    <span class="p">},</span>
<span class="p">)</span>
</code></pre></div></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-ctli8dq="">
<h2 id="autodiscover" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.autodiscover" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">autodiscover</span>
<a class="headerlink" href="#autodiscover" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>autodiscover: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | None</code></pre></div>
<p>Toggle whether to run <a href="../concepts/fundamentals/autodiscovery.md">autodiscovery</a> at the Django server startup.</p>
<p>Defaults to <code>True</code></p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">autodiscover</span><span class="o">=</span><span class="kc">False</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cekUVFu="">
<h2 id="dirs" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.dirs" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">dirs</span>
<a class="headerlink" href="#dirs" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>dirs: <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/library/os.html#os.PathLike">PathLike</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>] | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/library/os.html#os.PathLike">PathLike</a>]] | None</code></pre></div>
<p>Specify the directories that contain your components.</p>
<p>Defaults to <code>[Path(settings.BASE_DIR) / "components"]</code>. That is, the root <code>components/</code> app.</p>
<p>Directories must be full paths, same as with
<a href="https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STATICFILES_DIRS">STATICFILES_DIRS</a>.</p>
<p>These locations are searched during <a href="../concepts/fundamentals/autodiscovery.md">autodiscovery</a>,
or when you <a href="../concepts/fundamentals/html_js_css_files.md">define HTML, JS, or CSS as separate files</a>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">dirs</span><span class="o">=</span><span class="p">[</span><span class="n">BASE_DIR</span> <span class="o">/</span> <span class="s2">"components"</span><span class="p">],</span>
<span class="p">)</span>
</code></pre></div>
<p>Set to empty list to disable global components directories:</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">dirs</span><span class="o">=</span><span class="p">[],</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-ckAIzrU="">
<h2 id="app_dirs" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.app_dirs" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">app_dirs</span>
<a class="headerlink" href="#app_dirs" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>app_dirs: <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>] | None</code></pre></div>
<p>Specify the app-level directories that contain your components.</p>
<p>Defaults to <code>["components"]</code>. That is, for each Django app, we search <code>&lt;app&gt;/components/</code> for components.</p>
<p>The paths must be relative to app, e.g.:</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">app_dirs</span><span class="o">=</span><span class="p">[</span><span class="s2">"my_comps"</span><span class="p">],</span>
<span class="p">)</span>
</code></pre></div>
<p>To search for <code>&lt;app&gt;/my_comps/</code>.</p>
<p>These locations are searched during <a href="../concepts/fundamentals/autodiscovery.md">autodiscovery</a>,
or when you <a href="../concepts/fundamentals/html_js_css_files.md">define HTML, JS, or CSS as separate files</a>.</p>
<p>Set to empty list to disable app-level components:</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">app_dirs</span><span class="o">=</span><span class="p">[],</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cnb8qcf="">
<h2 id="cache" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.cache" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">cache</span>
<a class="headerlink" href="#cache" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>cache: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p>Name of the <a href="https://docs.djangoproject.com/en/5.2/topics/cache/">Django cache</a>
to be used for storing component's JS and CSS files.</p>
<p>If <code>None</code>, a <a href="https://docs.djangoproject.com/en/5.2/topics/cache/#local-memory-caching"><code>LocMemCache</code></a>
stores each component's JS and CSS, and a separate in-memory store holds the JS and CSS variables
from <a href="../api/#Component.get_js_data"><code>get_js_data()</code></a> and <a href="../api/#Component.get_css_data"><code>get_css_data()</code></a>.
<a href="#vars_cache_max_age"><code>vars_cache_max_age</code></a> and
<a href="#vars_cache_max_bytes"><code>vars_cache_max_bytes</code></a> limit that second store.</p>
<p>If set, everything goes in the named cache, and that cache's own <code>TIMEOUT</code> and limits apply.
Variables can hold data from your users, so set a <code>TIMEOUT</code> or a size limit on that cache.
With <code>"TIMEOUT": None</code> and no limit, each new value that <code>get_js_data()</code> or <code>get_css_data()</code>
returns adds an entry that stays for good.</p>
<p>Defaults to <code>None</code>.</p>
<p>Read more about <a href="../guides/setup/caching.md">caching</a>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">cache</span><span class="o">=</span><span class="s2">"my_cache"</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-ciOQR19="">
<h2 id="context_behavior" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.context_behavior" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">context_behavior</span>
<a class="headerlink" href="#context_behavior" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>context_behavior: ContextBehaviorType | None</code></pre></div>
<p>Configure whether, inside a component template, you can use variables from the outside
(<a href="../api/#ContextBehavior.DJANGO"><code>"django"</code></a>)
or not (<a href="../api/#ContextBehavior.ISOLATED"><code>"isolated"</code></a>).
This also affects what variables are available inside the <a href="./template_tags.md#fill"><code>{% fill %}</code></a>
tags.</p>
<p>Also see <a href="../concepts/advanced/component_context_scope.md#context-behavior">Component context and scope</a>.</p>
<p>Defaults to <code>"django"</code>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">context_behavior</span><span class="o">=</span><span class="s2">"isolated"</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
<blockquote>
<p>NOTE: <code>context_behavior</code> and <code>slot_context_behavior</code> options were merged in v0.70.</p>
<p>If you are migrating from BEFORE v0.67, set <code>context_behavior</code> to <code>"django"</code>.
From v0.67 to v0.78 (incl) the default value was <code>"isolated"</code>.</p>
<p>For v0.79 and later, the default is again <code>"django"</code>. See
<a href="https://github.com/django-components/django-components/issues/498">the rationale for this change</a>.</p>
</blockquote>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cuFUUxN="">
<h2 id="debug_highlight_components" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.debug_highlight_components" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">debug_highlight_components</span>
<a class="headerlink" href="#debug_highlight_components" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>debug_highlight_components: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | None</code></pre></div>
<p>DEPRECATED. Use
<a href="#extensions_defaults"><code>extensions_defaults</code></a>
instead. Will be removed in 2.0.</p>
<p>Enable / disable component highlighting.
See <a href="../guides/other/troubleshooting.md#component-and-slot-highlighting">Troubleshooting</a> for more details.</p>
<p>Defaults to <code>False</code>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">debug_highlight_components</span><span class="o">=</span><span class="kc">True</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cTsI5zN="">
<h2 id="debug_highlight_slots" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.debug_highlight_slots" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">debug_highlight_slots</span>
<a class="headerlink" href="#debug_highlight_slots" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>debug_highlight_slots: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | None</code></pre></div>
<p>DEPRECATED. Use
<a href="#extensions_defaults"><code>extensions_defaults</code></a>
instead. Will be removed in 2.0.</p>
<p>Enable / disable slot highlighting.
See <a href="../guides/other/troubleshooting.md#component-and-slot-highlighting">Troubleshooting</a> for more details.</p>
<p>Defaults to <code>False</code>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">debug_highlight_slots</span><span class="o">=</span><span class="kc">True</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cBvpVVw="">
<h2 id="dynamic_component_name" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.dynamic_component_name" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">dynamic_component_name</span>
<a class="headerlink" href="#dynamic_component_name" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>dynamic_component_name: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p>By default, the <a href="../components/#DynamicComponent">dynamic component</a>
is registered under the name <code>"dynamic"</code>.</p>
<p>In case of a conflict, you can use this setting to change the component name used for
the dynamic components.</p>
<div class="highlight"><pre><span></span><code><span class="c1"># settings.py</span>
<span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">dynamic_component_name</span><span class="o">=</span><span class="s2">"my_dynamic"</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
<p>After which you will be able to use the dynamic component with the new name:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_dynamic"</span> <span class="k">is</span><span class="o">=</span><span class="nv">table_comp</span> <span class="nv">data</span><span class="o">=</span><span class="nv">table_data</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">table_headers</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cjlUTdG="">
<h2 id="libraries" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.libraries" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">libraries</span>
<a class="headerlink" href="#libraries" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>libraries: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>] | None</code></pre></div>
<p>Configure extra python modules that should be loaded.</p>
<p>This may be useful if you are not using the <a href="../concepts/fundamentals/autodiscovery.md">autodiscovery feature</a>,
or you need to load components from non-standard locations. Thus you can have
a structure of components that is independent from your apps.</p>
<p>Expects a list of python module paths. Defaults to empty list.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">libraries</span><span class="o">=</span><span class="p">[</span>
        <span class="s2">"mysite.components.forms"</span><span class="p">,</span>
        <span class="s2">"mysite.components.buttons"</span><span class="p">,</span>
        <span class="s2">"mysite.components.cards"</span><span class="p">,</span>
    <span class="p">],</span>
<span class="p">)</span>
</code></pre></div>
<p>This would be the equivalent of importing these modules from within Django's
<a href="https://docs.djangoproject.com/en/5.2/ref/applications/#django.apps.AppConfig.ready"><code>AppConfig.ready()</code></a>:</p>
<div class="highlight"><pre><span></span><code><span class="k">class</span><span class="w"> </span><span class="nc">MyAppConfig</span><span class="p">(</span><span class="n">AppConfig</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">ready</span><span class="p">(</span><span class="bp">self</span><span class="p">):</span>
        <span class="kn">import</span><span class="w"> </span><span class="s2">"mysite.components.forms"</span>
        <span class="kn">import</span><span class="w"> </span><span class="s2">"mysite.components.buttons"</span>
        <span class="kn">import</span><span class="w"> </span><span class="s2">"mysite.components.cards"</span>
</code></pre></div></div>
<h3>Manually loading libraries</h3>
<p>In the rare case that you need to manually trigger the import of libraries, you can use
the <a href="../api/#import_libraries"><code>import_libraries()</code></a> function:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">import_libraries</span>

<span class="n">import_libraries</span><span class="p">()</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cEKIluh="">
<h2 id="multiline_tags" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.multiline_tags" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">multiline_tags</span>
<a class="headerlink" href="#multiline_tags" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>multiline_tags: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | None</code></pre></div>
<p>Enable / disable
<a href="../concepts/fundamentals/template_tag_syntax.md#multiline-tags">multiline support for template tags</a>.
If <code>True</code>, template tags like <code>{% component %}</code> or <code>{{ my_var }}</code> can span multiple lines.</p>
<p>Defaults to <code>True</code>.</p>
<p>Disable this setting if you are making custom modifications to Django's
regular expression for parsing templates at <code>django.template.base.tag_re</code>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">multiline_tags</span><span class="o">=</span><span class="kc">False</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cGd7wVL="">
<h2 id="reload_on_template_change" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.reload_on_template_change" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">reload_on_template_change</span>
<a class="headerlink" href="#reload_on_template_change" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>reload_on_template_change: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | None</code></pre></div>
<p>Deprecated. Use
<a href="#reload_on_file_change"><code>COMPONENTS.reload_on_file_change</code></a>
instead.</p>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cMl5urh="">
<h2 id="reload_on_file_change" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.reload_on_file_change" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">reload_on_file_change</span>
<a class="headerlink" href="#reload_on_file_change" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>reload_on_file_change: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> | <a class="doc-type-link" href="../api/#ReloadModeType">ReloadModeType</a> | None</code></pre></div>
<p>Configure how django_components reacts when component files
(HTML templates, JS, CSS) change on disk while the dev server is running.</p>
<p>See <a href="../guides/setup/development_server.md#hot-reloading-component-files-during-development">Hot-reloading component files during development</a>.</p>
<p><strong>Options:</strong></p>
<ul>
<li><code>False</code> or <code>"off"</code> - No file watching. Changes are not picked up until the server
is manually restarted.</li>
<li><code>True</code> or <code>"hot"</code> - Clear the in-memory component cache so the next render reads fresh
content from disk. The dev server keeps running without a restart.</li>
<li><code>"restart"</code> - Same as <code>"hot"</code>, but also triggers a full dev server restart.
Deprecated, will be removed in 2.0.</li>
</ul>
<p>Defaults to <code>"hot"</code>.</p>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>This setting should be used only in the dev environment!</p>
</div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-c2wFo1a="">
<h2 id="static_files_allowed" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.static_files_allowed" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">static_files_allowed</span>
<a class="headerlink" href="#static_files_allowed" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>static_files_allowed: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/library/re.html#re.Pattern">Pattern</a>] | None</code></pre></div>
<p>A list of file extensions (including the leading dot) that define which files within
<a href="#dirs"><code>COMPONENTS.dirs</code></a>
or
<a href="#app_dirs"><code>COMPONENTS.app_dirs</code></a>
are treated as <a href="https://docs.djangoproject.com/en/5.2/howto/static-files/">static files</a>.</p>
<p>If a file is matched against any of the patterns, it's considered a static file. Such files are collected
when running <a href="https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#collectstatic"><code>collectstatic</code></a>,
and can be accessed under the
<a href="https://docs.djangoproject.com/en/5.2/ref/settings/#static-url">static file endpoint</a>.</p>
<p>You can also pass in compiled regexes (<a href="https://docs.python.org/3/library/re.html#re.Pattern"><code>re.Pattern</code></a>)
for more advanced patterns.</p>
<p>By default, JS, CSS, and common image and font file formats are considered static files:</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">static_files_allowed</span><span class="o">=</span><span class="p">[</span>
        <span class="s2">".css"</span><span class="p">,</span>
        <span class="s2">".js"</span><span class="p">,</span> <span class="s2">".jsx"</span><span class="p">,</span> <span class="s2">".ts"</span><span class="p">,</span> <span class="s2">".tsx"</span><span class="p">,</span>
        <span class="c1"># Images</span>
        <span class="s2">".apng"</span><span class="p">,</span> <span class="s2">".png"</span><span class="p">,</span> <span class="s2">".avif"</span><span class="p">,</span> <span class="s2">".gif"</span><span class="p">,</span> <span class="s2">".jpg"</span><span class="p">,</span>
        <span class="s2">".jpeg"</span><span class="p">,</span>  <span class="s2">".jfif"</span><span class="p">,</span> <span class="s2">".pjpeg"</span><span class="p">,</span> <span class="s2">".pjp"</span><span class="p">,</span> <span class="s2">".svg"</span><span class="p">,</span>
        <span class="s2">".webp"</span><span class="p">,</span> <span class="s2">".bmp"</span><span class="p">,</span> <span class="s2">".ico"</span><span class="p">,</span> <span class="s2">".cur"</span><span class="p">,</span> <span class="s2">".tif"</span><span class="p">,</span> <span class="s2">".tiff"</span><span class="p">,</span>
        <span class="c1"># Fonts</span>
        <span class="s2">".eot"</span><span class="p">,</span> <span class="s2">".ttf"</span><span class="p">,</span> <span class="s2">".woff"</span><span class="p">,</span> <span class="s2">".otf"</span><span class="p">,</span> <span class="s2">".svg"</span><span class="p">,</span>
    <span class="p">],</span>
<span class="p">)</span>
</code></pre></div>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>Exposing your Python files can be a security vulnerability.
See <a href="../overview/security_notes.md">Security notes</a>.</p>
</div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-c8qCfzr="">
<h2 id="forbidden_static_files" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.forbidden_static_files" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">forbidden_static_files</span>
<a class="headerlink" href="#forbidden_static_files" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>forbidden_static_files: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/library/re.html#re.Pattern">Pattern</a>] | None</code></pre></div>
<p>Deprecated. Use
<a href="#static_files_forbidden"><code>COMPONENTS.static_files_forbidden</code></a>
instead.</p>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cUKbfxg="">
<h2 id="static_files_forbidden" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.static_files_forbidden" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">static_files_forbidden</span>
<a class="headerlink" href="#static_files_forbidden" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>static_files_forbidden: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/library/re.html#re.Pattern">Pattern</a>] | None</code></pre></div>
<p>A list of file extensions (including the leading dot) that define which files within
<a href="#dirs"><code>COMPONENTS.dirs</code></a>
or
<a href="#app_dirs"><code>COMPONENTS.app_dirs</code></a>
will NEVER be treated as <a href="https://docs.djangoproject.com/en/5.2/howto/static-files/">static files</a>.</p>
<p>If a file is matched against any of the patterns, it will never be considered a static file,
even if the file matches a pattern in
<a href="#static_files_allowed"><code>static_files_allowed</code></a>.</p>
<p>Use this setting together with
<a href="#static_files_allowed"><code>static_files_allowed</code></a>
for a fine control over what file types will be exposed.</p>
<p>You can also pass in compiled regexes (<a href="https://docs.python.org/3/library/re.html#re.Pattern"><code>re.Pattern</code></a>)
for more advanced patterns.</p>
<p>By default, any HTML and Python are considered NOT static files:</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">static_files_forbidden</span><span class="o">=</span><span class="p">[</span>
        <span class="s2">".html"</span><span class="p">,</span> <span class="s2">".django"</span><span class="p">,</span> <span class="s2">".dj"</span><span class="p">,</span> <span class="s2">".tpl"</span><span class="p">,</span>
        <span class="c1"># Python files</span>
        <span class="s2">".py"</span><span class="p">,</span> <span class="s2">".pyc"</span><span class="p">,</span>
    <span class="p">],</span>
<span class="p">)</span>
</code></pre></div>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>Exposing your Python files can be a security vulnerability.
See <a href="../overview/security_notes.md">Security notes</a>.</p>
</div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cmtZ43W="">
<h2 id="tag_formatter" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.tag_formatter" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">tag_formatter</span>
<a class="headerlink" href="#tag_formatter" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>tag_formatter: <a class="doc-type-link" href="../api/#TagFormatterABC">TagFormatterABC</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p>Configure what syntax is used inside Django templates to render components.
See the <a href="./tag_formatters.md">available tag formatters</a>.</p>
<p>Defaults to <code>"django_components.component_formatter"</code>.</p>
<p>Learn more about <a href="../concepts/advanced/tag_formatters.md">Customizing component tags with TagFormatter</a>.</p>
<p>Can be set either as direct reference:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">component_formatter</span>

<span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="s2">"tag_formatter"</span><span class="p">:</span> <span class="n">component_formatter</span>
<span class="p">)</span>
</code></pre></div>
<p>Or as an import string;</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="s2">"tag_formatter"</span><span class="p">:</span> <span class="s2">"django_components.component_formatter"</span>
<span class="p">)</span>
</code></pre></div>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><ul>
<li>
<p><code>"django_components.component_formatter"</code></p>
<p>Set</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="s2">"tag_formatter"</span><span class="p">:</span> <span class="s2">"django_components.component_formatter"</span>
<span class="p">)</span>
</code></pre></div>
<p>To write components like this:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"button"</span> <span class="nv">href</span><span class="o">=</span><span class="s2">"..."</span> <span class="cp">%}</span>
<span class="x">    Click me!</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
</li>
<li>
<p><code>django_components.component_shorthand_formatter</code></p>
<p>Set</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="s2">"tag_formatter"</span><span class="p">:</span> <span class="s2">"django_components.component_shorthand_formatter"</span>
<span class="p">)</span>
</code></pre></div>
<p>To write components like this:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">button</span> <span class="nv">href</span><span class="o">=</span><span class="s2">"..."</span> <span class="cp">%}</span>
<span class="x">    Click me!</span>
<span class="cp">{%</span> <span class="k">endbutton</span> <span class="cp">%}</span>
</code></pre></div>
</li>
</ul></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cwabbJr="">
<h2 id="template_cache_size" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.template_cache_size" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">template_cache_size</span>
<a class="headerlink" href="#template_cache_size" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>template_cache_size: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#int">int</a> | None</code></pre></div>
<p>DEPRECATED. Template caching will be removed in 2.0.</p>
<p>Configure the maximum amount of Django templates to be cached.</p>
<p>Defaults to <code>128</code>.</p>
<p>Each time a <a href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template">Django template</a>
is rendered, it is cached to a global in-memory cache (using Python's
<a href="https://docs.python.org/3/library/functools.html#functools.lru_cache"><code>lru_cache</code></a>
decorator). This speeds up the next render of the component.
As the same component is often used many times on the same page, these savings add up.</p>
<p>By default the cache holds 128 component templates in memory, which should be enough for most sites.
But if you have a lot of components, or if you are overriding
<a href="../api/#Component.get_template"><code>Component.get_template()</code></a>
to render many dynamic templates, you can increase this number.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">template_cache_size</span><span class="o">=</span><span class="mi">256</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
<p>To remove the cache limit altogether and cache everything, set <code>template_cache_size</code> to <code>None</code>.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">template_cache_size</span><span class="o">=</span><span class="kc">None</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
<p>If you want to add templates to the cache yourself, you can use
<a href="../api/#cached_template"><code>cached_template()</code></a>:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">cached_template</span>

<span class="n">cached_template</span><span class="p">(</span><span class="s2">"Variable: {{ variable }}"</span><span class="p">)</span>

<span class="c1"># You can optionally specify Template class, and other Template inputs:</span>
<span class="k">class</span><span class="w"> </span><span class="nc">MyTemplate</span><span class="p">(</span><span class="n">Template</span><span class="p">):</span>
    <span class="k">pass</span>

<span class="n">cached_template</span><span class="p">(</span>
    <span class="s2">"Variable: {{ variable }}"</span><span class="p">,</span>
    <span class="n">template_cls</span><span class="o">=</span><span class="n">MyTemplate</span><span class="p">,</span>
    <span class="n">name</span><span class="o">=...</span>
    <span class="n">origin</span><span class="o">=...</span>
    <span class="n">engine</span><span class="o">=...</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-c4ekRYI="">
<h2 id="vars_cache_max_age" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.vars_cache_max_age" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">vars_cache_max_age</span>
<a class="headerlink" href="#vars_cache_max_age" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>vars_cache_max_age: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#int">int</a> | None</code></pre></div>
<p>How many seconds to keep the JS and CSS variables from
<a href="../api/#Component.get_js_data"><code>get_js_data()</code></a> and <a href="../api/#Component.get_css_data"><code>get_css_data()</code></a>
after they were last used.</p>
<p>Defaults to <code>86400</code> (24 hours).</p>
<p>This applies only to the default in-memory store. When you set
<a href="#cache"><code>COMPONENTS.cache</code></a>, that cache's own <code>TIMEOUT</code> applies instead.</p>
<p>Rendering a component counts as using its variables, and so does replaying its HTML from
<a href="../concepts/advanced/component_caching.md"><code>{% cache %}</code></a> or
<a href="../api/#Component.Cache"><code>Component.Cache</code></a>. A whole page that you keep in a cache of your own
does not count. HTML rendered with the <code>"fragment"</code> strategy fetches the variables when
it loads, so keep this longer than you keep such HTML.</p>
<p>When a render finds that the variables are gone, the component's <code>$onComponent</code> callbacks
do not run, or its CSS variables are unset, and a warning is logged.</p>
<p>Must be <code>None</code>, which uses the default, or a positive integer of at most <code>sys.maxsize</code>.
Any other value raises a <code>ValueError</code> when Django starts. There is no way to turn
the limit off, but you can set a very large number.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">vars_cache_max_age</span><span class="o">=</span><span class="mi">7</span> <span class="o">*</span> <span class="mi">24</span> <span class="o">*</span> <span class="mi">60</span> <span class="o">*</span> <span class="mi">60</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cHUR8TC="">
<h2 id="vars_cache_max_bytes" class="doc doc-heading">
<span id="django_components.app_settings.ComponentsSettings.vars_cache_max_bytes" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">vars_cache_max_bytes</span>
<a class="headerlink" href="#vars_cache_max_bytes" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>vars_cache_max_bytes: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#int">int</a> | None</code></pre></div>
<p>How much memory each server process may use to keep the JS and CSS variables from
<a href="../api/#Component.get_js_data"><code>get_js_data()</code></a> and <a href="../api/#Component.get_css_data"><code>get_css_data()</code></a>.</p>
<p>Defaults to <code>67108864</code> (64 MiB).</p>
<p>This applies only to the default in-memory store. When you set
<a href="#cache"><code>COMPONENTS.cache</code></a>, that cache's own limits apply instead.</p>
<p>This is an estimate of the memory used, and it is close to the real figure.</p>
<p>Each distinct set of variables is stored once. When the store is full, it drops the variables
that were used longest ago, and they are missing as described in
<a href="#vars_cache_max_age"><code>COMPONENTS.vars_cache_max_age</code></a>, until a render
produces the same variables again. So if your components produce many distinct values,
raise this limit.</p>
<p>Variables larger than the whole limit are not stored, and a warning is logged.</p>
<p>Must be <code>None</code>, which uses the default, or a positive integer of at most <code>sys.maxsize</code>.
Any other value raises a <code>ValueError</code> when Django starts. There is no way to turn
the limit off, but you can set a very large number.</p>
<div class="highlight"><pre><span></span><code><span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">vars_cache_max_bytes</span><span class="o">=</span><span class="mi">256</span> <span class="o">*</span> <span class="mi">1024</span> <span class="o">*</span> <span class="mi">1024</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
</div>
</div>


