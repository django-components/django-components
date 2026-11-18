---
title: Extension hooks
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/extension_hooks/
description: "API reference - extension lifecycle hooks and their context objects."
---

# Extension hooks

Extensions hook into the component lifecycle by subclassing [`ComponentExtension`][ComponentExtension] and implementing the `on_*` methods below. Each hook receives a single context object whose fields are listed under **Available data**.

## Hooks




<div class="doc doc-object doc-hook" data-djc-id-c9lps4S="">
<h3 id="on_component_class_created" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_class_created" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_class_created</span>
<a class="headerlink" href="#on_component_class_created" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_class_created(ctx: <a class="doc-type-link" href="#OnComponentClassCreatedContext">OnComponentClassCreatedContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L590" target="_blank">See source code</a></p>
<p>Called when a new <a href="../api/#Component"><code>Component</code></a> class is created.</p>
<p>This hook is called after the <a href="../api/#Component"><code>Component</code></a> class
is fully defined but before it's registered.</p>
<p>Use this hook to perform any initialization or validation of the
<a href="../api/#Component"><code>Component</code></a> class.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentClassCreatedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_class_created</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentClassCreatedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Add a new attribute to the Component class</span>
        <span class="n">ctx</span><span class="o">.</span><span class="n">component_cls</span><span class="o">.</span><span class="n">my_attr</span> <span class="o">=</span> <span class="s2">"my_value"</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The created Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cyyq1OH="">
<h3 id="on_component_class_deleted" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_class_deleted" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_class_deleted</span>
<a class="headerlink" href="#on_component_class_deleted" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_class_deleted(ctx: <a class="doc-type-link" href="#OnComponentClassDeletedContext">OnComponentClassDeletedContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L612" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> class is being deleted.</p>
<p>This hook is called before the <a href="../api/#Component"><code>Component</code></a> class
is deleted from memory.</p>
<p>Use this hook to perform any cleanup related to the <a href="../api/#Component"><code>Component</code></a> class.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentClassDeletedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_class_deleted</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentClassDeletedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Remove Component class from the extension's cache on deletion</span>
        <span class="bp">self</span><span class="o">.</span><span class="n">cache</span><span class="o">.</span><span class="n">pop</span><span class="p">(</span><span class="n">ctx</span><span class="o">.</span><span class="n">component_cls</span><span class="p">,</span> <span class="kc">None</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The to-be-deleted Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cPW4SuH="">
<h3 id="on_component_data" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_data" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_data</span>
<a class="headerlink" href="#on_component_data" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_data(ctx: <a class="doc-type-link" href="#OnComponentDataContext">OnComponentDataContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L786" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> was triggered to render,
after a component's context and data methods have been processed.</p>
<p>This hook is called after
<a href="../api/#Component.get_template_data"><code>Component.get_template_data()</code></a>,
<a href="../api/#Component.get_js_data"><code>Component.get_js_data()</code></a>
and <a href="../api/#Component.get_css_data"><code>Component.get_css_data()</code></a>.</p>
<p>This hook runs after <a href="#on_component_input"><code>on_component_input</code></a>.</p>
<p>Use this hook to modify or validate the component's data before rendering.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentDataContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_data</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentDataContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Add extra template variable to all components when they are rendered</span>
        <span class="n">ctx</span><span class="o">.</span><span class="n">template_data</span><span class="p">[</span><span class="s2">"my_template_var"</span><span class="p">]</span> <span class="o">=</span> <span class="s2">"my_value"</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>context_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Deprecated. Use <code>template_data</code> instead. Will be removed in 2.0.</td></tr><tr><td><code>template_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of template data from <code>Component.get_template_data()</code></td></tr><tr><td><code>js_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of JavaScript data from <code>Component.get_js_data()</code></td></tr><tr><td><code>css_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of CSS data from <code>Component.get_css_data()</code></td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cowmvO6="">
<h3 id="on_component_input" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_input" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_input</span>
<a class="headerlink" href="#on_component_input" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_input(ctx: <a class="doc-type-link" href="#OnComponentInputContext">OnComponentInputContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L717" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> was triggered to render,
but before a component's context and data methods are invoked.</p>
<p>Use this hook to modify or validate component inputs before they're processed.</p>
<p>This is the first hook that is called when rendering a component. As such this hook is called before
<a href="../api/#Component.get_template_data"><code>Component.get_template_data()</code></a>,
<a href="../api/#Component.get_js_data"><code>Component.get_js_data()</code></a>,
and <a href="../api/#Component.get_css_data"><code>Component.get_css_data()</code></a> methods,
and the
<a href="#on_component_data"><code>on_component_data</code></a>
hook.</p>
<p>This hook also allows to skip the rendering of a component altogether. If the hook returns
a non-null value, this value will be used instead of rendering the component.</p>
<p>You can use this to implement a caching mechanism for components, or define components
that will be rendered conditionally.</p>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>When any extension short-circuits a component (by returning a non-null value), the
rest of that component's render is skipped, including
<a href="#on_component_data"><code>on_component_data</code></a>
and
<a href="#on_component_rendered"><code>on_component_rendered</code></a>.</p>
<p>Extensions run in order, and the built-in extensions (including the cache) run before
user extensions. So your <code>on_component_input</code> may run even when a later extension
short-circuits the same component.</p>
<p>In practice this means: if you save something at the start of a render (here, in
<code>on_component_input</code>) so you can use or remove it later in <code>on_component_rendered</code>,
that later hook might never run. And if you saved it in a dictionary that lives on
your extension, nothing ever removes that entry, so the dictionary grows by one with
every skipped render. That is a memory leak.</p>
<p>To avoid this, store anything you need for a single render on the component itself,
or on something that lives only as long as the component (such as its config object
for your extension, or <code>Slot.extra</code>). It is then discarded automatically once the
component is done, whether or not <code>on_component_rendered</code> runs.</p>
</div>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentInputContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_input</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentInputContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Add extra kwarg to all components when they are rendered</span>
        <span class="n">ctx</span><span class="o">.</span><span class="n">kwargs</span><span class="p">[</span><span class="s2">"my_input"</span><span class="p">]</span> <span class="o">=</span> <span class="s2">"my_value"</span>
</code></pre></div></div>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>In this hook, the components' inputs are still mutable.</p>
<p>As such, if a component defines <a href="../api/#Component.Args"><code>Args</code></a>,
<a href="../api/#Component.Kwargs"><code>Kwargs</code></a>,
<a href="../api/#Component.Slots"><code>Slots</code></a> types, these types are NOT yet instantiated.</p>
<p>Instead, component fields like <a href="../api/#Component.args"><code>Component.args</code></a>,
<a href="../api/#Component.kwargs"><code>Component.kwargs</code></a>,
<a href="../api/#Component.slots"><code>Component.slots</code></a>
are plain <code>list</code> / <code>dict</code> objects.</p>
</div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that received the input and is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>args</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a></td><td>List of positional arguments passed to the component</td></tr><tr><td><code>kwargs</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of keyword arguments passed to the component</td></tr><tr><td><code>slots</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="../api/#Slot">Slot</a>]</td><td>Dictionary of slot definitions</td></tr><tr><td><code>context</code></td><td><a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context">Context</a></td><td>The Django template Context object</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cMHecBF="">
<h3 id="on_component_registered" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_registered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_registered</span>
<a class="headerlink" href="#on_component_registered" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_registered(ctx: <a class="doc-type-link" href="#OnComponentRegisteredContext">OnComponentRegisteredContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L675" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> class is
registered with a <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a>.</p>
<p>This hook is called after a <a href="../api/#Component"><code>Component</code></a> class
is successfully registered.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentRegisteredContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_registered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentRegisteredContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Component </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">component_cls</span><span class="si">}</span><span class="s2"> registered to </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">registry</span><span class="si">}</span><span class="s2"> as '</span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">name</span><span class="si">}</span><span class="s2">'"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The registry the component was registered to</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name the component was registered under</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The registered Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cXRsBoL="">
<h3 id="on_component_rendered" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_rendered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_rendered</span>
<a class="headerlink" href="#on_component_rendered" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_rendered(ctx: <a class="doc-type-link" href="#OnComponentRenderedContext">OnComponentRenderedContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L812" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> was rendered, including
all its child components.</p>
<p>Use this hook to access or post-process the component's rendered output.</p>
<p>This hook works similarly to
<a href="../api/#Component.on_render_after"><code>Component.on_render_after()</code></a>:</p>
<ol>
<li>
<p>To modify the output, return a new string from this hook. The original output or error will be ignored.</p>
</li>
<li>
<p>To cause this component to return a new error, raise that error. The original output and error
will be ignored.</p>
</li>
<li>
<p>If you neither raise nor return string, the original output or error will be used.</p>
</li>
</ol>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>Change the final output of a component:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentRenderedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_rendered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentRenderedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Append a comment to the component's rendered output</span>
        <span class="k">return</span> <span class="n">ctx</span><span class="o">.</span><span class="n">result</span> <span class="o">+</span> <span class="s2">"&lt;!-- MyExtension comment --&gt;"</span>
</code></pre></div>
<p>Cause the component to raise a new exception:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentRenderedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_rendered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentRenderedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Raise a new exception</span>
        <span class="k">raise</span> <span class="ne">Exception</span><span class="p">(</span><span class="s2">"Error message"</span><span class="p">)</span>
</code></pre></div>
<p>Return nothing (or <code>None</code>) to handle the result as usual:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentRenderedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_rendered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentRenderedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="k">if</span> <span class="n">ctx</span><span class="o">.</span><span class="n">error</span> <span class="ow">is</span> <span class="ow">not</span> <span class="kc">None</span><span class="p">:</span>
            <span class="c1"># The component raised an exception</span>
            <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Error: </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">error</span><span class="si">}</span><span class="s2">"</span><span class="p">)</span>
        <span class="k">else</span><span class="p">:</span>
            <span class="c1"># The component rendered successfully</span>
            <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Result: </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">result</span><span class="si">}</span><span class="s2">"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>result</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</td><td>The rendered component, or <code>None</code> if rendering failed</td></tr><tr><td><code>error</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/exceptions.html#Exception">Exception</a> | None</td><td>The error that occurred during rendering, or <code>None</code> if rendering was successful</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cifSkI2="">
<h3 id="on_component_unregistered" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_component_unregistered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_component_unregistered</span>
<a class="headerlink" href="#on_component_unregistered" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_component_unregistered(ctx: <a class="doc-type-link" href="#OnComponentUnregisteredContext">OnComponentUnregisteredContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L694" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#Component"><code>Component</code></a> class is
unregistered from a <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a>.</p>
<p>This hook is called after a <a href="../api/#Component"><code>Component</code></a> class
is removed from the registry.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnComponentUnregisteredContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_component_unregistered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnComponentUnregisteredContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Component </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">component_cls</span><span class="si">}</span><span class="s2"> unregistered from </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">registry</span><span class="si">}</span><span class="s2"> as '</span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">name</span><span class="si">}</span><span class="s2">'"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The registry the component was unregistered from</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name the component was registered under</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The unregistered Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cSkZDL3="">
<h3 id="on_css_loaded" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_css_loaded" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_css_loaded</span>
<a class="headerlink" href="#on_css_loaded" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_css_loaded(ctx: <a class="doc-type-link" href="#OnCssLoadedContext">OnCssLoadedContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L919" target="_blank">See source code</a></p>
<p>Called when a Component's CSS is loaded as a string.</p>
<p>This hook runs only once per <a href="../api/#Component"><code>Component</code></a> class and works for both
<a href="../api/#Component.css"><code>Component.css</code></a> and
<a href="../api/#Component.css_file"><code>Component.css_file</code></a>.</p>
<p>Use this hook to read or modify the CSS.</p>
<p>To modify the CSS, return a new string from this hook.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnCssLoadedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_css_loaded</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnCssLoadedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Modify the CSS</span>
        <span class="k">return</span> <span class="n">ctx</span><span class="o">.</span><span class="n">content</span><span class="o">.</span><span class="n">replace</span><span class="p">(</span><span class="s2">"Hello"</span><span class="p">,</span> <span class="s2">"Hi"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose CSS was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The CSS content (string)</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cz9HYkr="">
<h3 id="on_dependencies" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_dependencies" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_dependencies</span>
<a class="headerlink" href="#on_dependencies" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_dependencies(ctx: <a class="doc-type-link" href="#OnDependenciesContext">OnDependenciesContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#tuple">tuple</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Script">Script</a>], <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Style">Style</a>]] | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L1015" target="_blank">See source code</a></p>
<p>Called when a rendered HTML is being finalized, after all dependencies (JS and CSS) were collected,
and before they are rendered as <code>&lt;script&gt;</code> and <code>&lt;link&gt;</code> tags.</p>
<p>Use this hook to access or modify the JS/CSS dependencies, for example to:</p>
<ul>
<li>Modify or add dependencies</li>
<li>Render <code>&lt;script&gt;</code> tags JS modules with <code>type="module"</code></li>
<li>Add CSP nonce to the dependencies</li>
</ul>
<p>To modify the dependencies, return a tuple of <code>(scripts, styles)</code>.</p>
<p>Where:</p>
<ul>
<li><code>scripts</code> is a list of <a href="../api/#Script"><code>Script</code></a> objects.</li>
<li><code>styles</code> is a list of <a href="../api/#Style"><code>Style</code></a> objects.</li>
</ul>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="p">(</span>
    <span class="n">ComponentExtension</span><span class="p">,</span>
    <span class="n">OnDependenciesContext</span><span class="p">,</span>
    <span class="n">Script</span><span class="p">,</span>
    <span class="n">Style</span><span class="p">,</span>
<span class="p">)</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_dependencies</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnDependenciesContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">tuple</span><span class="p">[</span><span class="nb">list</span><span class="p">[</span><span class="s2">"Script"</span><span class="p">],</span> <span class="nb">list</span><span class="p">[</span><span class="s2">"Style"</span><span class="p">]]:</span>
        <span class="n">scripts</span> <span class="o">=</span> <span class="n">ctx</span><span class="o">.</span><span class="n">scripts</span>
        <span class="n">styles</span> <span class="o">=</span> <span class="n">ctx</span><span class="o">.</span><span class="n">styles</span>

        <span class="c1"># Modify existing scripts and styles</span>
        <span class="k">for</span> <span class="n">script</span> <span class="ow">in</span> <span class="n">scripts</span><span class="p">:</span>
            <span class="k">if</span> <span class="n">script</span><span class="o">.</span><span class="n">kind</span> <span class="o">==</span> <span class="s2">"extra"</span><span class="p">:</span>
                <span class="n">script</span><span class="o">.</span><span class="n">wrap</span> <span class="o">=</span> <span class="kc">False</span>
        <span class="k">for</span> <span class="n">style</span> <span class="ow">in</span> <span class="n">styles</span><span class="p">:</span>
            <span class="k">if</span> <span class="n">style</span><span class="o">.</span><span class="n">kind</span> <span class="o">==</span> <span class="s2">"extra"</span><span class="p">:</span>
                <span class="n">style</span><span class="o">.</span><span class="n">attrs</span><span class="p">[</span><span class="s2">"media"</span><span class="p">]</span> <span class="o">=</span> <span class="s2">"print"</span>

        <span class="c1"># Add extra JS and CSS dependencies (inline content)</span>
        <span class="n">scripts</span><span class="o">.</span><span class="n">append</span><span class="p">(</span>
            <span class="n">Script</span><span class="p">(</span>
                <span class="n">content</span><span class="o">=</span><span class="s2">"console.log('extension-injected script');"</span><span class="p">,</span>
                <span class="n">wrap</span><span class="o">=</span><span class="kc">False</span><span class="p">,</span>
            <span class="p">)</span>
        <span class="p">)</span>
        <span class="n">styles</span><span class="o">.</span><span class="n">append</span><span class="p">(</span>
            <span class="n">Style</span><span class="p">(</span>
                <span class="n">content</span><span class="o">=</span><span class="s2">"body { background-color: red; }"</span><span class="p">,</span>
            <span class="p">)</span>
        <span class="p">)</span>
        <span class="c1"># Add extra JS and CSS dependencies (external URL)</span>
        <span class="n">scripts</span><span class="o">.</span><span class="n">append</span><span class="p">(</span>
            <span class="n">Script</span><span class="p">(</span>
                <span class="n">url</span><span class="o">=</span><span class="s2">"/static/analytics.js"</span><span class="p">,</span>
                <span class="n">content</span><span class="o">=</span><span class="kc">None</span><span class="p">,</span>
            <span class="p">)</span>
        <span class="p">)</span>
        <span class="n">styles</span><span class="o">.</span><span class="n">append</span><span class="p">(</span>
            <span class="n">Style</span><span class="p">(</span>
                <span class="n">url</span><span class="o">=</span><span class="s2">"/static/print.css"</span><span class="p">,</span>
                <span class="n">content</span><span class="o">=</span><span class="kc">None</span><span class="p">,</span>
                <span class="n">attrs</span><span class="o">=</span><span class="p">{</span><span class="s2">"media"</span><span class="p">:</span> <span class="s2">"print"</span><span class="p">},</span>
            <span class="p">)</span>
        <span class="p">)</span>
        <span class="k">return</span> <span class="p">(</span><span class="n">scripts</span><span class="p">,</span> <span class="n">styles</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>scripts</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Script">Script</a>]</td><td>List of JS scripts to load</td></tr><tr><td><code>styles</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Style">Style</a>]</td><td>List of CSS styles to load</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-c3e04Np="">
<h3 id="on_extension_created" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_extension_created" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_extension_created</span>
<a class="headerlink" href="#on_extension_created" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_extension_created(ctx: <a class="doc-type-link" href="#OnExtensionCreatedContext">OnExtensionCreatedContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L568" target="_blank">See source code</a></p>
<p>Called when a new <a href="../api/#ComponentExtension"><code>ComponentExtension</code></a> instance is created.</p>
<p>Use this hook to perform any initialization or validation of the extension instance.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnExtensionCreatedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_extension_created</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnExtensionCreatedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Add a new attribute to the extension instance</span>
        <span class="n">ctx</span><span class="o">.</span><span class="n">extension</span><span class="o">.</span><span class="n">my_attr</span> <span class="o">=</span> <span class="s2">"my_value"</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>extension</code></td><td><a class="doc-type-link" href="../api/#ComponentExtension">ComponentExtension</a></td><td>The created extension</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cwDsMOv="">
<h3 id="on_js_loaded" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_js_loaded" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_js_loaded</span>
<a class="headerlink" href="#on_js_loaded" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_js_loaded(ctx: <a class="doc-type-link" href="#OnJsLoadedContext">OnJsLoadedContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L943" target="_blank">See source code</a></p>
<p>Called when a Component's JS is loaded as a string.</p>
<p>This hook runs only once per <a href="../api/#Component"><code>Component</code></a> class and works for both
<a href="../api/#Component.js"><code>Component.js</code></a> and
<a href="../api/#Component.js_file"><code>Component.js_file</code></a>.</p>
<p>Use this hook to read or modify the JS.</p>
<p>To modify the JS, return a new string from this hook.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnCssLoadedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_js_loaded</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnJsLoadedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Modify the JS</span>
        <span class="k">return</span> <span class="n">ctx</span><span class="o">.</span><span class="n">content</span><span class="o">.</span><span class="n">replace</span><span class="p">(</span><span class="s2">"Hello"</span><span class="p">,</span> <span class="s2">"Hi"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose JS was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The JS content (string)</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cZnfI9D="">
<h3 id="on_registry_created" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_registry_created" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_registry_created</span>
<a class="headerlink" href="#on_registry_created" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_registry_created(ctx: <a class="doc-type-link" href="#OnRegistryCreatedContext">OnRegistryCreatedContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L633" target="_blank">See source code</a></p>
<p>Called when a new <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a> is created.</p>
<p>This hook is called after a new
<a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a> instance is initialized.</p>
<p>Use this hook to perform any initialization needed for the registry.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnRegistryCreatedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_registry_created</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnRegistryCreatedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Add a new attribute to the registry</span>
        <span class="n">ctx</span><span class="o">.</span><span class="n">registry</span><span class="o">.</span><span class="n">my_attr</span> <span class="o">=</span> <span class="s2">"my_value"</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The created ComponentRegistry instance</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cAhOr6Z="">
<h3 id="on_registry_deleted" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_registry_deleted" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_registry_deleted</span>
<a class="headerlink" href="#on_registry_deleted" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_registry_deleted(ctx: <a class="doc-type-link" href="#OnRegistryDeletedContext">OnRegistryDeletedContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L654" target="_blank">See source code</a></p>
<p>Called when a <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a> is being deleted.</p>
<p>This hook is called before
a <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a> instance is deleted.</p>
<p>Use this hook to perform any cleanup related to the registry.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnRegistryDeletedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_registry_deleted</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnRegistryDeletedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Remove registry from the extension's cache on deletion</span>
        <span class="bp">self</span><span class="o">.</span><span class="n">cache</span><span class="o">.</span><span class="n">pop</span><span class="p">(</span><span class="n">ctx</span><span class="o">.</span><span class="n">registry</span><span class="p">,</span> <span class="kc">None</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The to-be-deleted ComponentRegistry instance</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-c5DDraQ="">
<h3 id="on_slot_rendered" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_slot_rendered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_slot_rendered</span>
<a class="headerlink" href="#on_slot_rendered" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_slot_rendered(ctx: <a class="doc-type-link" href="#OnSlotRenderedContext">OnSlotRenderedContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L971" target="_blank">See source code</a></p>
<p>Called when a <a href="./template_tags.md#slot"><code>{% slot %}</code></a> tag was rendered.</p>
<p>Use this hook to access or post-process the slot's rendered output.</p>
<p>To modify the output, return a new string from this hook.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnSlotRenderedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_slot_rendered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnSlotRenderedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Append a comment to the slot's rendered output</span>
        <span class="k">return</span> <span class="n">ctx</span><span class="o">.</span><span class="n">result</span> <span class="o">+</span> <span class="s2">"&lt;!-- MyExtension comment --&gt;"</span>
</code></pre></div></div>
<p><strong>Access slot metadata:</strong></p>
<p>You can access the <a href="./template_tags.md#slot"><code>{% slot %}</code> tag</a>
node (<a href="../api/#SlotNode"><code>SlotNode</code></a>) and its metadata using <code>ctx.slot_node</code>.</p>
<p>For example, to find the <a href="../api/#Component"><code>Component</code></a> class to which
belongs the template where the <a href="./template_tags.md#slot"><code>{% slot %}</code></a> tag is defined, you can use
<code>ctx.slot_node.template_component</code>:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnSlotRenderedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_slot_rendered</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnSlotRenderedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Access slot metadata</span>
        <span class="n">slot_node</span> <span class="o">=</span> <span class="n">ctx</span><span class="o">.</span><span class="n">slot_node</span>
        <span class="n">slot_owner</span> <span class="o">=</span> <span class="n">slot_node</span><span class="o">.</span><span class="n">template_component</span>
        <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Slot owner: </span><span class="si">{</span><span class="n">slot_owner</span><span class="si">}</span><span class="s2">"</span><span class="p">)</span>
</code></pre></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that contains the <code>{% slot %}</code> tag</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class that contains the <code>{% slot %}</code> tag</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>slot</code></td><td><a class="doc-type-link" href="../api/#Slot">Slot</a></td><td>The Slot instance that was rendered</td></tr><tr><td><code>slot_name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name of the <code>{% slot %}</code> tag</td></tr><tr><td><code>slot_node</code></td><td><a class="doc-type-link" href="../api/#SlotNode">SlotNode</a></td><td>The node instance of the <code>{% slot %}</code> tag</td></tr><tr><td><code>slot_is_required</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a></td><td>Whether the slot is required</td></tr><tr><td><code>slot_is_default</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a></td><td>Whether the slot is default</td></tr><tr><td><code>result</code></td><td><a class="doc-type-link" href="../api/#SlotResult">SlotResult</a></td><td>The rendered result of the slot</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cGAdLWW="">
<h3 id="on_template_compiled" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_template_compiled" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_template_compiled</span>
<a class="headerlink" href="#on_template_compiled" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_template_compiled(ctx: <a class="doc-type-link" href="#OnTemplateCompiledContext">OnTemplateCompiledContext</a>) -> None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L897" target="_blank">See source code</a></p>
<p>Called when a Component's template is compiled
into a <a href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template"><code>Template</code></a> object.</p>
<p>This hook runs only once per <a href="../api/#Component"><code>Component</code></a> class and works for both
<a href="../api/#Component.template"><code>Component.template</code></a> and
<a href="../api/#Component.template_file"><code>Component.template_file</code></a>.</p>
<p>Use this hook to read or modify the template (in-place) after it's compiled.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnTemplateCompiledContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_template_compiled</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnTemplateCompiledContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="kc">None</span><span class="p">:</span>
        <span class="nb">print</span><span class="p">(</span><span class="sa">f</span><span class="s2">"Template origin: </span><span class="si">{</span><span class="n">ctx</span><span class="o">.</span><span class="n">template</span><span class="o">.</span><span class="n">origin</span><span class="o">.</span><span class="n">name</span><span class="si">}</span><span class="s2">"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose template was loaded</td></tr><tr><td><code>template</code></td><td><a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template">Template</a></td><td>The compiled template object</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook" data-djc-id-cUi1PwF="">
<h3 id="on_template_loaded" class="doc doc-heading">
<span id="django_components.extension.ComponentExtension.on_template_loaded" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc doc-object-name">on_template_loaded</span>
<a class="headerlink" href="#on_template_loaded" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>on_template_loaded(ctx: <a class="doc-type-link" href="#OnTemplateLoadedContext">OnTemplateLoadedContext</a>) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</code></pre></div>
<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/extension.py#L873" target="_blank">See source code</a></p>
<p>Called when a Component's template is loaded as a string.</p>
<p>This hook runs only once per <a href="../api/#Component"><code>Component</code></a> class and works for both
<a href="../api/#Component.template"><code>Component.template</code></a> and
<a href="../api/#Component.template_file"><code>Component.template_file</code></a>.</p>
<p>Use this hook to read or modify the template before it's compiled.</p>
<p>To modify the template, return a new string from this hook.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentExtension</span><span class="p">,</span> <span class="n">OnTemplateLoadedContext</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExtension</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">on_template_loaded</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">OnTemplateLoadedContext</span><span class="p">)</span> <span class="o">-&gt;</span> <span class="nb">str</span> <span class="o">|</span> <span class="kc">None</span><span class="p">:</span>
        <span class="c1"># Modify the template</span>
        <span class="k">return</span> <span class="n">ctx</span><span class="o">.</span><span class="n">content</span><span class="o">.</span><span class="n">replace</span><span class="p">(</span><span class="s2">"Hello"</span><span class="p">,</span> <span class="s2">"Hi"</span><span class="p">)</span>
</code></pre></div></div>
<div class="doc-section doc-fields"><p class="doc-section-title">Available data</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose template was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The template string</td></tr><tr><td><code>origin</code></td><td>Origin | None</td><td>The origin of the template</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</td><td>The name of the template</td></tr></tbody></table></div>
</div>
</div>




## Objects




<div class="doc doc-object doc-hook-context" data-djc-id-chXg9Ta="">
<h3 id="OnComponentClassCreatedContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentClassCreatedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentClassCreatedContext</span>
<a class="headerlink" href="#OnComponentClassCreatedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The created Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cGq7FhA="">
<h3 id="OnComponentClassDeletedContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentClassDeletedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentClassDeletedContext</span>
<a class="headerlink" href="#OnComponentClassDeletedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The to-be-deleted Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-c0hjXch="">
<h3 id="OnComponentDataContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentDataContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentDataContext</span>
<a class="headerlink" href="#OnComponentDataContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>context_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Deprecated. Use <code>template_data</code> instead. Will be removed in 2.0.</td></tr><tr><td><code>template_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of template data from <code>Component.get_template_data()</code></td></tr><tr><td><code>js_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of JavaScript data from <code>Component.get_js_data()</code></td></tr><tr><td><code>css_data</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of CSS data from <code>Component.get_css_data()</code></td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-c3t0L37="">
<h3 id="OnComponentInputContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentInputContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentInputContext</span>
<a class="headerlink" href="#OnComponentInputContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that received the input and is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>args</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a></td><td>List of positional arguments passed to the component</td></tr><tr><td><code>kwargs</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a></td><td>Dictionary of keyword arguments passed to the component</td></tr><tr><td><code>slots</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="../api/#Slot">Slot</a>]</td><td>Dictionary of slot definitions</td></tr><tr><td><code>context</code></td><td><a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context">Context</a></td><td>The Django template Context object</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cUTo0IO="">
<h3 id="OnComponentRegisteredContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentRegisteredContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentRegisteredContext</span>
<a class="headerlink" href="#OnComponentRegisteredContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The registry the component was registered to</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name the component was registered under</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The registered Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cj9aC5A="">
<h3 id="OnComponentRenderedContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentRenderedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentRenderedContext</span>
<a class="headerlink" href="#OnComponentRenderedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that is being rendered</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>result</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</td><td>The rendered component, or <code>None</code> if rendering failed</td></tr><tr><td><code>error</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/exceptions.html#Exception">Exception</a> | None</td><td>The error that occurred during rendering, or <code>None</code> if rendering was successful</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-crW01hm="">
<h3 id="OnComponentUnregisteredContext" class="doc doc-heading">
<span id="django_components.extension.OnComponentUnregisteredContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnComponentUnregisteredContext</span>
<a class="headerlink" href="#OnComponentUnregisteredContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The registry the component was unregistered from</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name the component was registered under</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The unregistered Component class</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cYnVwuE="">
<h3 id="OnCssLoadedContext" class="doc doc-heading">
<span id="django_components.extension.OnCssLoadedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnCssLoadedContext</span>
<a class="headerlink" href="#OnCssLoadedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose CSS was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The CSS content (string)</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-caNTCrd="">
<h3 id="OnDependenciesContext" class="doc doc-heading">
<span id="django_components.extension.OnDependenciesContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnDependenciesContext</span>
<a class="headerlink" href="#OnDependenciesContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>scripts</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Script">Script</a>]</td><td>List of JS scripts to load</td></tr><tr><td><code>styles</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#list">list</a>[<a class="doc-type-link" href="../api/#Style">Style</a>]</td><td>List of CSS styles to load</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cMB6vbo="">
<h3 id="OnExtensionCreatedContext" class="doc doc-heading">
<span id="django_components.extension.OnExtensionCreatedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnExtensionCreatedContext</span>
<a class="headerlink" href="#OnExtensionCreatedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>extension</code></td><td><a class="doc-type-link" href="../api/#ComponentExtension">ComponentExtension</a></td><td>The created extension</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-ccrT6km="">
<h3 id="OnJsLoadedContext" class="doc doc-heading">
<span id="django_components.extension.OnJsLoadedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnJsLoadedContext</span>
<a class="headerlink" href="#OnJsLoadedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose JS was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The JS content (string)</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cK8B1dL="">
<h3 id="OnRegistryCreatedContext" class="doc doc-heading">
<span id="django_components.extension.OnRegistryCreatedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnRegistryCreatedContext</span>
<a class="headerlink" href="#OnRegistryCreatedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The created ComponentRegistry instance</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-cMCll2H="">
<h3 id="OnRegistryDeletedContext" class="doc doc-heading">
<span id="django_components.extension.OnRegistryDeletedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnRegistryDeletedContext</span>
<a class="headerlink" href="#OnRegistryDeletedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a></td><td>The to-be-deleted ComponentRegistry instance</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-c6aUQqA="">
<h3 id="OnSlotRenderedContext" class="doc doc-heading">
<span id="django_components.extension.OnSlotRenderedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnSlotRenderedContext</span>
<a class="headerlink" href="#OnSlotRenderedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component</code></td><td><a class="doc-type-link" href="../api/#Component">Component</a></td><td>The Component instance that contains the <code>{% slot %}</code> tag</td></tr><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class that contains the <code>{% slot %}</code> tag</td></tr><tr><td><code>component_id</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The unique identifier for this component instance</td></tr><tr><td><code>slot</code></td><td><a class="doc-type-link" href="../api/#Slot">Slot</a></td><td>The Slot instance that was rendered</td></tr><tr><td><code>slot_name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The name of the <code>{% slot %}</code> tag</td></tr><tr><td><code>slot_node</code></td><td><a class="doc-type-link" href="../api/#SlotNode">SlotNode</a></td><td>The node instance of the <code>{% slot %}</code> tag</td></tr><tr><td><code>slot_is_required</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a></td><td>Whether the slot is required</td></tr><tr><td><code>slot_is_default</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a></td><td>Whether the slot is default</td></tr><tr><td><code>result</code></td><td><a class="doc-type-link" href="../api/#SlotResult">SlotResult</a></td><td>The rendered result of the slot</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-c4DFxft="">
<h3 id="OnTemplateCompiledContext" class="doc doc-heading">
<span id="django_components.extension.OnTemplateCompiledContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnTemplateCompiledContext</span>
<a class="headerlink" href="#OnTemplateCompiledContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose template was loaded</td></tr><tr><td><code>template</code></td><td><a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template">Template</a></td><td>The compiled template object</td></tr></tbody></table></div>
</div>
</div>







<div class="doc doc-object doc-hook-context" data-djc-id-czIAl9H="">
<h3 id="OnTemplateLoadedContext" class="doc doc-heading">
<span id="django_components.extension.OnTemplateLoadedContext" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name">OnTemplateLoadedContext</span>
<a class="headerlink" href="#OnTemplateLoadedContext" title="Permanent link">¤</a>
</h3>
<div class="doc doc-contents">

<div class="doc-section doc-fields"><p class="doc-section-title">Fields</p><table class="doc-params"><thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>component_cls</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#type">type</a>[<a class="doc-type-link" href="../api/#Component">Component</a>]</td><td>The Component class whose template was loaded</td></tr><tr><td><code>content</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></td><td>The template string</td></tr><tr><td><code>origin</code></td><td>Origin | None</td><td>The origin of the template</td></tr><tr><td><code>name</code></td><td><a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a> | None</td><td>The name of the template</td></tr></tbody></table></div>
</div>
</div>


