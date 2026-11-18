---
title: Testing API
url: https://django-components.github.io/django-components/v/0.153.0/docs/reference/testing_api/
description: "API reference - Testing API."
---

# Testing API




<div class="doc doc-object doc-class" data-djc-id-cDcyrDW="">
<h2 id="djc_test" class="doc doc-heading">
<span id="django_components.testing.djc_test" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-function" title="function"></span><span class="doc doc-object-name doc-class-name">djc_test</span>
<a class="headerlink" href="#djc_test" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>djc_test(
    django_settings: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a> | None | <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Callable">Callable</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a> = None,
    components_settings: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a> | None = None,
    parametrize: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>]]] | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>]], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Iterable">Iterable</a>[None | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#float">float</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#int">int</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a>] | <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Callable">Callable</a>[[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>], None | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#object">object</a>] | None] | None = None,
    gc_collect: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a> = True
) -> <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Callable">Callable</a>[[TCallable], TCallable]</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/util/testing.py#L90" target="_blank">See source code</a></p>
<p>Decorator for testing components from django-components.</p>
<p><code>@djc_test</code> manages the global state of django-components, ensuring that each test is properly
isolated and that components registered in one test do not affect other tests.</p>
<p>This decorator can be applied to a function, method, or a class. If applied to a class,
it will search for all methods that start with <code>test_</code>, and apply the decorator to them.
This is applied recursively to nested classes as well.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>Applying to a function:
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="nd">@djc_test</span>
<span class="k">def</span><span class="w"> </span><span class="nf">test_my_component</span><span class="p">():</span>
    <span class="nd">@register</span><span class="p">(</span><span class="s2">"my_component"</span><span class="p">)</span>
    <span class="k">class</span><span class="w"> </span><span class="nc">MyComponent</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
        <span class="n">template</span> <span class="o">=</span> <span class="s2">"..."</span>
    <span class="o">...</span>
</code></pre></div></p>
<p>Applying to a class:
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="nd">@djc_test</span>
<span class="k">class</span><span class="w"> </span><span class="nc">TestMyComponent</span><span class="p">:</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">test_something</span><span class="p">(</span><span class="bp">self</span><span class="p">):</span>
        <span class="o">...</span>

    <span class="k">class</span><span class="w"> </span><span class="nc">Nested</span><span class="p">:</span>
        <span class="k">def</span><span class="w"> </span><span class="nf">test_something_else</span><span class="p">(</span><span class="bp">self</span><span class="p">):</span>
            <span class="o">...</span>
</code></pre></div></p>
<p>Applying to a class is the same as applying the decorator to each <code>test_</code> method individually:
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="k">class</span><span class="w"> </span><span class="nc">TestMyComponent</span><span class="p">:</span>
    <span class="nd">@djc_test</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">test_something</span><span class="p">(</span><span class="bp">self</span><span class="p">):</span>
        <span class="o">...</span>

    <span class="k">class</span><span class="w"> </span><span class="nc">Nested</span><span class="p">:</span>
        <span class="nd">@djc_test</span>
        <span class="k">def</span><span class="w"> </span><span class="nf">test_something_else</span><span class="p">(</span><span class="bp">self</span><span class="p">):</span>
            <span class="o">...</span>
</code></pre></div></p>
<p>To use <code>@djc_test</code>, Django must be set up first:</p>
<div class="highlight"><pre><span></span><code><span class="kn">import</span><span class="w"> </span><span class="nn">django</span>
<span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="n">django</span><span class="o">.</span><span class="n">setup</span><span class="p">()</span>

<span class="nd">@djc_test</span>
<span class="k">def</span><span class="w"> </span><span class="nf">test_my_component</span><span class="p">():</span>
    <span class="o">...</span>
</code></pre></div></div>
<table class="doc-params"><thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>django_settings</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a> | None | <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Callable">Callable</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a></td><td>Django settings, a dictionary passed to Django's
<a href="https://docs.djangoproject.com/en/5.2/topics/testing/tools/#django.test.override_settings"><code>@override_settings</code></a>.
The test runs within the context of these overridden settings.</p>
<p>If <code>django_settings</code> contains django-components settings (<code>COMPONENTS</code> field), these are merged.
Other Django settings are simply overridden. <span class="doc-param-default">(default: <code>None</code>)</span></td></tr><tr><td><code>components_settings</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a> | None</td><td>Instead of defining django-components settings under <code>django_settings["COMPONENTS"]</code>,
you can simply set the Components settings here.</p>
<p>These settings are merged with the django-components settings from <code>django_settings["COMPONENTS"]</code>.</p>
<p>Fields in <code>components_settings</code> override fields in <code>django_settings["COMPONENTS"]</code>. <span class="doc-param-default">(default: <code>None</code>)</span></td></tr><tr><td><code>parametrize</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>]]] | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Sequence">Sequence</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>]], <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Iterable">Iterable</a>[None | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#float">float</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#int">int</a> | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a>] | <a class="doc-type-link" href="https://docs.python.org/3.13/library/collections.abc.html#collections.abc.Callable">Callable</a>[[<a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a>], None | <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#object">object</a>] | None] | None</td><td><p>Parametrize the test function with
<a href="https://docs.pytest.org/en/stable/how-to/parametrize.html#pytest-mark-parametrize"><code>pytest.mark.parametrize</code></a>.
This requires <a href="https://docs.pytest.org/">pytest</a> to be installed.</p>
<p>The input is a tuple of:</p>
<ul>
<li><code>(param_names, param_values)</code> or</li>
<li><code>(param_names, param_values, ids)</code></li>
</ul> <span class="doc-param-default">(default: <code>None</code>)</span></td></tr><tr><td><code>gc_collect</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a></td><td>By default <code>djc_test</code> runs garbage collection after each test to force the
state cleanup. Set this to <code>False</code> to skip this. <span class="doc-param-default">(default: <code>True</code>)</span></td></tr></tbody></table>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="nd">@djc_test</span><span class="p">(</span>
    <span class="n">parametrize</span><span class="o">=</span><span class="p">(</span>
         <span class="p">[</span><span class="s2">"input"</span><span class="p">,</span> <span class="s2">"expected"</span><span class="p">],</span>
         <span class="p">[[</span><span class="mi">1</span><span class="p">,</span> <span class="s2">"&lt;div&gt;1&lt;/div&gt;"</span><span class="p">],</span> <span class="p">[</span><span class="mi">2</span><span class="p">,</span> <span class="s2">"&lt;div&gt;2&lt;/div&gt;"</span><span class="p">]],</span>
         <span class="n">ids</span><span class="o">=</span><span class="p">[</span><span class="s2">"1"</span><span class="p">,</span> <span class="s2">"2"</span><span class="p">]</span>
     <span class="p">)</span>
<span class="p">)</span>
<span class="k">def</span><span class="w"> </span><span class="nf">test_component</span><span class="p">(</span><span class="nb">input</span><span class="p">,</span> <span class="n">expected</span><span class="p">):</span>
    <span class="n">rendered</span> <span class="o">=</span> <span class="n">MyComponent</span><span class="p">(</span><span class="nb">input</span><span class="o">=</span><span class="nb">input</span><span class="p">)</span><span class="o">.</span><span class="n">render</span><span class="p">()</span>
    <span class="k">assert</span> <span class="n">rendered</span> <span class="o">==</span> <span class="n">expected</span>
</code></pre></div>
<p>You can parametrize the Django or Components settings by setting up parameters called
<code>django_settings</code> and <code>components_settings</code>. These will be merged with the respetive settings
from the decorator.</p>
<p>Example of parametrizing context_behavior:
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components.testing</span><span class="w"> </span><span class="kn">import</span> <span class="n">djc_test</span>

<span class="nd">@djc_test</span><span class="p">(</span>
    <span class="n">components_settings</span><span class="o">=</span><span class="p">{</span>
        <span class="c1"># Settings shared by all tests</span>
        <span class="s2">"app_dirs"</span><span class="p">:</span> <span class="p">[</span><span class="s2">"custom_dir"</span><span class="p">],</span>
    <span class="p">},</span>
    <span class="n">parametrize</span><span class="o">=</span><span class="p">(</span>
        <span class="c1"># Parametrized settings</span>
        <span class="p">[</span><span class="s2">"components_settings"</span><span class="p">],</span>
        <span class="p">[</span>
            <span class="p">[{</span><span class="s2">"context_behavior"</span><span class="p">:</span> <span class="s2">"django"</span><span class="p">}],</span>
            <span class="p">[{</span><span class="s2">"context_behavior"</span><span class="p">:</span> <span class="s2">"isolated"</span><span class="p">}],</span>
        <span class="p">],</span>
        <span class="p">[</span><span class="s2">"django"</span><span class="p">,</span> <span class="s2">"isolated"</span><span class="p">],</span>
    <span class="p">)</span>
<span class="p">)</span>
<span class="k">def</span><span class="w"> </span><span class="nf">test_context_behavior</span><span class="p">(</span><span class="n">components_settings</span><span class="p">):</span>
    <span class="n">rendered</span> <span class="o">=</span> <span class="n">MyComponent</span><span class="o">.</span><span class="n">render</span><span class="p">()</span>
    <span class="o">...</span>
</code></pre></div></p></div>
<p><strong>Settings resolution:</strong></p>
<p><code>@djc_test</code> accepts settings from different sources. The settings are resolved in the following order:</p>
<ul>
<li>
<p>Django settings:</p>
<ol>
<li>The defaults are the Django settings that Django was set up with.</li>
<li>Those are then overriden with fields in the <code>django_settings</code> kwarg.</li>
<li>The parametrized <code>django_settings</code> override the fields on the <code>django_settings</code> kwarg.</li>
</ol>
<p>Priority: <code>django_settings</code> (parametrized) &gt; <code>django_settings</code> &gt; <code>django.conf.settings</code></p>
</li>
<li>
<p>Components settings:</p>
<ol>
<li>Same as above, except that the <code>django_settings["COMPONENTS"]</code> field is merged instead of overridden.</li>
<li>The <code>components_settings</code> kwarg is then merged with the <code>django_settings["COMPONENTS"]</code> field.</li>
<li>The parametrized <code>components_settings</code> override the fields on the <code>components_settings</code> kwarg.</li>
</ol>
<p>Priority: <code>components_settings</code> (parametrized) &gt; <code>components_settings</code> &gt; <code>django_settings["COMPONENTS"]</code> &gt; <code>django.conf.settings.COMPONENTS</code></p>
</li>
</ul>

</div>
</div>


