---
title: Extension URLs
url: https://django-components.github.io/django-components/v/0.152.1/docs/reference/extension_urls/
description: "API reference - Extension URLs."
---

# Extension URLs

Overview of all classes, functions, and other objects related to defining extension URLs.

Read more on [Extensions](../concepts/advanced/extensions.md).




<div class="doc doc-object doc-class" data-djc-id-c7ofZ8n="">
<h2 id="URLRoute" class="doc doc-heading">
<span id="django_components.URLRoute" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">URLRoute</span>
<a class="headerlink" href="#URLRoute" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>URLRoute(
    path: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>,
    handler: <a class="doc-type-link" href="#URLRouteHandler">URLRouteHandler</a> | None = None,
    children: <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Iterable">Iterable</a>[<a class="doc-type-link" href="#URLRoute">URLRoute</a>] = list(),
    name: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None = None,
    extra: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>] = dict()
)</code></pre></div>
<p class="doc doc-class-bases">Bases: <code>object</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/util/routing.py#L22" target="_blank">See source code</a></p>
<p>Framework-agnostic route definition.</p>
<p>This is similar to Django's <code>URLPattern</code> object created with
<a href="https://docs.djangoproject.com/en/5.2/ref/urls/#path"><code>django.urls.path()</code></a>.</p>
<p>The <code>URLRoute</code> must either define a <code>handler</code> function or have a list of child routes <code>children</code>.
If both are defined, an error will be raised.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="n">URLRoute</span><span class="p">(</span><span class="s2">"/my/path"</span><span class="p">,</span> <span class="n">handler</span><span class="o">=</span><span class="n">my_handler</span><span class="p">,</span> <span class="n">name</span><span class="o">=</span><span class="s2">"my_name"</span><span class="p">,</span> <span class="n">extra</span><span class="o">=</span><span class="p">{</span><span class="s2">"kwargs"</span><span class="p">:</span> <span class="p">{</span><span class="s2">"my_extra"</span><span class="p">:</span> <span class="s2">"my_value"</span><span class="p">}})</span>
</code></pre></div>
<p>Is equivalent to:</p>
<div class="highlight"><pre><span></span><code><span class="n">django</span><span class="o">.</span><span class="n">urls</span><span class="o">.</span><span class="n">path</span><span class="p">(</span><span class="s2">"/my/path"</span><span class="p">,</span> <span class="n">my_handler</span><span class="p">,</span> <span class="n">name</span><span class="o">=</span><span class="s2">"my_name"</span><span class="p">,</span> <span class="n">kwargs</span><span class="o">=</span><span class="p">{</span><span class="s2">"my_extra"</span><span class="p">:</span> <span class="s2">"my_value"</span><span class="p">})</span>
</code></pre></div>
<p>With children:</p>
<div class="highlight"><pre><span></span><code><span class="n">URLRoute</span><span class="p">(</span>
    <span class="s2">"/my/path"</span><span class="p">,</span>
    <span class="n">name</span><span class="o">=</span><span class="s2">"my_name"</span><span class="p">,</span>
    <span class="n">extra</span><span class="o">=</span><span class="p">{</span><span class="s2">"kwargs"</span><span class="p">:</span> <span class="p">{</span><span class="s2">"my_extra"</span><span class="p">:</span> <span class="s2">"my_value"</span><span class="p">}},</span>
    <span class="n">children</span><span class="o">=</span><span class="p">[</span>
        <span class="n">URLRoute</span><span class="p">(</span>
            <span class="s2">"/child/&lt;str:name&gt;/"</span><span class="p">,</span>
            <span class="n">handler</span><span class="o">=</span><span class="n">my_handler</span><span class="p">,</span>
            <span class="n">name</span><span class="o">=</span><span class="s2">"my_name"</span><span class="p">,</span>
            <span class="n">extra</span><span class="o">=</span><span class="p">{</span><span class="s2">"kwargs"</span><span class="p">:</span> <span class="p">{</span><span class="s2">"my_extra"</span><span class="p">:</span> <span class="s2">"my_value"</span><span class="p">}},</span>
        <span class="p">),</span>
        <span class="n">URLRoute</span><span class="p">(</span><span class="s2">"/other/&lt;int:id&gt;/"</span><span class="p">,</span> <span class="n">handler</span><span class="o">=</span><span class="n">other_handler</span><span class="p">),</span>
    <span class="p">],</span>
<span class="p">)</span>
</code></pre></div></div>
                <div class="doc-members"><h3 class="doc-group-label">Attributes</h3><div class="doc doc-member"><h4 id="URLRoute.path" class="doc-member-heading"><span id="django_components.URLRoute.path"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">path</span><a class="headerlink" href="#URLRoute.path" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>path: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></code></pre></div></div></div><div class="doc doc-member"><h4 id="URLRoute.handler" class="doc-member-heading"><span id="django_components.URLRoute.handler"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">handler</span><a class="headerlink" href="#URLRoute.handler" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>handler: <a class="doc-type-link" href="#URLRouteHandler">URLRouteHandler</a> | None</code></pre></div></div></div><div class="doc doc-member"><h4 id="URLRoute.children" class="doc-member-heading"><span id="django_components.URLRoute.children"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">children</span><a class="headerlink" href="#URLRoute.children" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>children: <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Iterable">Iterable</a>[<a class="doc-type-link" href="#URLRoute">URLRoute</a>]</code></pre></div></div></div><div class="doc doc-member"><h4 id="URLRoute.name" class="doc-member-heading"><span id="django_components.URLRoute.name"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">name</span><a class="headerlink" href="#URLRoute.name" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>name: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div></div></div><div class="doc doc-member"><h4 id="URLRoute.extra" class="doc-member-heading"><span id="django_components.URLRoute.extra"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">extra</span><a class="headerlink" href="#URLRoute.extra" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>extra: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>]</code></pre></div></div></div></div>
</div>
</div>







<div class="doc doc-object doc-class" data-djc-id-cF5idCN="">
<h2 id="URLRouteHandler" class="doc doc-heading">
<span id="django_components.URLRouteHandler" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">URLRouteHandler</span>
<a class="headerlink" href="#URLRouteHandler" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>URLRouteHandler()</code></pre></div>
<p class="doc doc-class-bases">Bases: <code>typing.Protocol</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/util/routing.py#L15" target="_blank">See source code</a></p>
<p>Framework-agnostic 'view' function for routes</p>

</div>
</div>


