---
title: Template variables
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/template_variables/
description: "API reference - the variables available inside component templates."
---

# Template variables

These variables are available inside a component's template via the `component_vars` object (e.g. `{{ component_vars.args }}`). They are the fields of [`ComponentVars`][ComponentVars].




<div class="doc doc-object doc-setting" data-djc-id-cjmLIgy="">
<h2 id="args" class="doc doc-heading">
<span id="django_components.component.ComponentVars.args" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">args</span>
<a class="headerlink" href="#args" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>args: <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a></code></pre></div>
<p>The <code>args</code> argument as passed to
<a href="../api/#Component.get_template_data"><code>Component.get_template_data()</code></a>.</p>
<p>This is the same <a href="../api/#Component.args"><code>Component.args</code></a>
that's available on the component instance.</p>
<p>If you defined the <a href="../api/#Component.Args"><code>Component.Args</code></a> class,
then the <code>args</code> property will return an instance of that class.</p>
<p>Otherwise, <code>args</code> will be a plain list.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>With <code>Args</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="k">class</span><span class="w"> </span><span class="nc">Args</span><span class="p">:</span>
        <span class="n">page</span><span class="p">:</span> <span class="nb">int</span>
        <span class="n">per_page</span><span class="p">:</span> <span class="nb">int</span>

    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">h1</span><span class="p">&gt;</span>Table<span class="p">&lt;/</span><span class="nt">h1</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Page: <span class="cp">{{</span> <span class="nv">component_vars.args.page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Per page: <span class="cp">{{</span> <span class="nv">component_vars.args.per_page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div>
<p>Without <code>Args</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">h1</span><span class="p">&gt;</span>Table<span class="p">&lt;/</span><span class="nt">h1</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Page: <span class="cp">{{</span> <span class="nv">component_vars.args.0</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Per page: <span class="cp">{{</span> <span class="nv">component_vars.args.1</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cEcQjsD="">
<h2 id="kwargs" class="doc doc-heading">
<span id="django_components.component.ComponentVars.kwargs" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">kwargs</span>
<a class="headerlink" href="#kwargs" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>kwargs: <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a></code></pre></div>
<p>The <code>kwargs</code> argument as passed to
<a href="../api/#Component.get_template_data"><code>Component.get_template_data()</code></a>.</p>
<p>This is the same <a href="../api/#Component.kwargs"><code>Component.kwargs</code></a>
that's available on the component instance.</p>
<p>If you defined the <a href="../api/#Component.Kwargs"><code>Component.Kwargs</code></a> class,
then the <code>kwargs</code> property will return an instance of that class.</p>
<p>Otherwise, <code>kwargs</code> will be a plain dict.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>With <code>Kwargs</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="k">class</span><span class="w"> </span><span class="nc">Kwargs</span><span class="p">:</span>
        <span class="n">page</span><span class="p">:</span> <span class="nb">int</span>
        <span class="n">per_page</span><span class="p">:</span> <span class="nb">int</span>

    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">h1</span><span class="p">&gt;</span>Table<span class="p">&lt;/</span><span class="nt">h1</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Page: <span class="cp">{{</span> <span class="nv">component_vars.kwargs.page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Per page: <span class="cp">{{</span> <span class="nv">component_vars.kwargs.per_page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div>
<p>Without <code>Kwargs</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">h1</span><span class="p">&gt;</span>Table<span class="p">&lt;/</span><span class="nt">h1</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Page: <span class="cp">{{</span> <span class="nv">component_vars.kwargs.page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
            <span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>Per page: <span class="cp">{{</span> <span class="nv">component_vars.kwargs.per_page</span> <span class="cp">}}</span><span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cDapKH7="">
<h2 id="slots" class="doc doc-heading">
<span id="django_components.component.ComponentVars.slots" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">slots</span>
<a class="headerlink" href="#slots" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>slots: <a class="doc-type-link" href="https://docs.python.org/3.13/library/typing.html#typing.Any">Any</a></code></pre></div>
<p>The <code>slots</code> argument as passed to
<a href="../api/#Component.get_template_data"><code>Component.get_template_data()</code></a>.</p>
<p>This is the same <a href="../api/#Component.slots"><code>Component.slots</code></a>
that's available on the component instance.</p>
<p>If you defined the <a href="../api/#Component.Slots"><code>Component.Slots</code></a> class,
then the <code>slots</code> property will return an instance of that class.</p>
<p>Otherwise, <code>slots</code> will be a plain dict.</p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>With <code>Slots</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">SlotInput</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="k">class</span><span class="w"> </span><span class="nc">Slots</span><span class="p">:</span>
        <span class="n">footer</span><span class="p">:</span> <span class="n">SlotInput</span>

    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
                <span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"footer"</span> <span class="nv">body</span><span class="o">=</span><span class="nv">component_vars.slots.footer</span> <span class="o">/</span> <span class="cp">%}</span>
            <span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div>
<p>Without <code>Slots</code> class:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">Component</span><span class="p">,</span> <span class="n">SlotInput</span><span class="p">,</span> <span class="n">register</span>

<span class="nd">@register</span><span class="p">(</span><span class="s2">"table"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">'''</span>
        <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
            <span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
                <span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"footer"</span> <span class="nv">body</span><span class="o">=</span><span class="nv">component_vars.slots.footer</span> <span class="o">/</span> <span class="cp">%}</span>
            <span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
        <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">'''</span>
</code></pre></div></div>
</div>
</div>







<div class="doc doc-object doc-setting" data-djc-id-cXtFtxA="">
<h2 id="is_filled" class="doc doc-heading">
<span id="django_components.component.ComponentVars.is_filled" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name">is_filled</span>
<a class="headerlink" href="#is_filled" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>is_filled: <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#dict">dict</a>[<a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a>, <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/functions.html#bool">bool</a>]</code></pre></div>
<p>Deprecated. Will be removed in 2.0. Use <a href="#slots"><code>component_vars.slots</code></a> instead.
Note that <code>component_vars.slots</code> no longer escapes the slot names.</p>
<p>Dictonary describing which component slots are filled (<code>True</code>) or are not (<code>False</code>).</p>
<p><i>New in version 0.70</i></p>
<p>Use as <code>{{ component_vars.is_filled }}</code></p>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><div class="highlight"><pre><span></span><code><span class="c">{# Render wrapping HTML only if the slot is defined #}</span>
<span class="cp">{%</span> <span class="k">if</span> <span class="nv">component_vars.is_filled.my_slot</span> <span class="cp">%}</span>
<span class="x">    &lt;div class="slot-wrapper"&gt;</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"my_slot"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    &lt;/div&gt;</span>
<span class="cp">{%</span> <span class="k">endif</span> <span class="cp">%}</span>
</code></pre></div>
<p>This is equivalent to checking if a given key is among the slot fills:</p>
<div class="highlight"><pre><span></span><code><span class="k">class</span><span class="w"> </span><span class="nc">MyTable</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">get_template_data</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">args</span><span class="p">,</span> <span class="n">kwargs</span><span class="p">,</span> <span class="n">slots</span><span class="p">,</span> <span class="n">context</span><span class="p">):</span>
        <span class="k">return</span> <span class="p">{</span>
            <span class="s2">"my_slot_filled"</span><span class="p">:</span> <span class="s2">"my_slot"</span> <span class="ow">in</span> <span class="n">slots</span>
        <span class="p">}</span>
</code></pre></div></div>
</div>
</div>


