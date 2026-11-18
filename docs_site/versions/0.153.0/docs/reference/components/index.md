---
title: Components
url: https://django-components.github.io/django-components/v/0.153.0/docs/reference/components/
description: "API reference - the predefined django-components components."
---

# Components

django-components ships these ready-to-use components. Register them like any other component, then use them in your templates.




<div class="doc doc-object doc-class doc-component" data-djc-id-ckY0b1z="">
<h2 id="DynamicComponent" class="doc doc-heading">
<span id="django_components.components.dynamic.DynamicComponent" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">DynamicComponent</span>
<a class="headerlink" href="#DynamicComponent" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
<p class="doc doc-class-bases">Bases: <code>django_components.component.Component</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/components/dynamic.py#L10" target="_blank">See source code</a></p>
<p>This component is given a registered name or a reference to another component,
and behaves as if the other component was in its place.</p>
<p>The args, kwargs, and slot fills are all passed down to the underlying component.</p>
<table class="doc-params"><thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead><tbody><tr><td><code>is</code></td><td>str | type[Component]</td><td>Component that should be rendered. Either a registered name of a component,
or a <a href="../api/#Component">Component</a> class directly. Required.</td></tr><tr><td><code>registry</code></td><td><a class="doc-type-link" href="../api/#ComponentRegistry">ComponentRegistry</a> | None</td><td>Specify the <a href="../api/#ComponentRegistry">registry</a>
to search for the registered name. If omitted, all registries are searched until the first match. <span class="doc-param-default">(default: <code>None</code>)</span></td></tr><tr><td><code>*args</code></td><td>Any | None</td><td>Additional data passed to the component. <span class="doc-param-default">(default: <code>None</code>)</span></td></tr><tr><td><code>**kwargs</code></td><td>Any | None</td><td>Additional data passed to the component. <span class="doc-param-default">(default: <code>None</code>)</span></td></tr></tbody></table>
<p><strong>Slots:</strong></p>
<ul>
<li>Any slots, depending on the actual component.</li>
</ul>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>Django
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"dynamic"</span> <span class="k">is</span><span class="o">=</span><span class="nv">table_comp</span> <span class="nv">data</span><span class="o">=</span><span class="nv">table_data</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">table_headers</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div></p>
<p>Or in case you use the <code>django_components.component_shorthand_formatter</code> tag formatter:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">dynamic</span> <span class="k">is</span><span class="o">=</span><span class="nv">table_comp</span> <span class="nv">data</span><span class="o">=</span><span class="nv">table_data</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">table_headers</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">enddynamic</span> <span class="cp">%}</span>
</code></pre></div>
<p>Python
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">DynamicComponent</span>

<span class="n">DynamicComponent</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
    <span class="n">kwargs</span><span class="o">=</span><span class="p">{</span>
        <span class="s2">"is"</span><span class="p">:</span> <span class="n">table_comp</span><span class="p">,</span>
        <span class="s2">"data"</span><span class="p">:</span> <span class="n">table_data</span><span class="p">,</span>
        <span class="s2">"headers"</span><span class="p">:</span> <span class="n">table_headers</span><span class="p">,</span>
    <span class="p">},</span>
    <span class="n">slots</span><span class="o">=</span><span class="p">{</span>
        <span class="s2">"pagination"</span><span class="p">:</span> <span class="n">PaginationComponent</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
            <span class="n">deps_strategy</span><span class="o">=</span><span class="s2">"ignore"</span><span class="p">,</span>
        <span class="p">),</span>
    <span class="p">},</span>
<span class="p">)</span>
</code></pre></div></p></div>
<h3>Use cases</h3>
<p>Dynamic components are suitable if you are writing something like a form component. You may design
it such that users give you a list of input types, and you render components depending on the input types.</p>
<p>While you could handle this with a series of if / else statements, that's not an extensible approach.
Instead, you can use the dynamic component in place of normal components.</p>
<h3>Component name</h3>
<p>By default, the dynamic component is registered under the name <code>"dynamic"</code>. In case of a conflict,
you can set the
<a href="../settings/#dynamic_component_name"><code>COMPONENTS.dynamic_component_name</code></a>
setting to change the name used for the dynamic components.</p>
<div class="highlight"><pre><span></span><code><span class="c1"># settings.py</span>
<span class="n">COMPONENTS</span> <span class="o">=</span> <span class="n">ComponentsSettings</span><span class="p">(</span>
    <span class="n">dynamic_component_name</span><span class="o">=</span><span class="s2">"my_dynamic"</span><span class="p">,</span>
<span class="p">)</span>
</code></pre></div>
<p>After which you will be able to use the dynamic component with the new name:
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_dynamic"</span> <span class="k">is</span><span class="o">=</span><span class="nv">table_comp</span> <span class="nv">data</span><span class="o">=</span><span class="nv">table_data</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">table_headers</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"pagination"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div></p>
                <div class="doc-members"><h3 class="doc-group-label">Methods</h3><div class="doc doc-member"><h4 id="DynamicComponent.on_render" class="doc-member-heading"><span id="django_components.components.dynamic.DynamicComponent.on_render"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc-object-name">on_render</span><a class="headerlink" href="#DynamicComponent.on_render" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>on_render(context: <a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context">Context</a>, template: <a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template">Template</a> | None) -> <a class="doc-type-link" href="https://docs.python.org/3.13/builtins/stdtypes.html#str">str</a></code></pre></div></div></div></div>
</div>
</div>







<div class="doc doc-object doc-class doc-component" data-djc-id-crwVPUa="">
<h2 id="ErrorFallback" class="doc doc-heading">
<span id="django_components.components.error_fallback.ErrorFallback" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">ErrorFallback</span>
<a class="headerlink" href="#ErrorFallback" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
<p class="doc doc-class-bases">Bases: <code>django_components.component.Component</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/components/error_fallback.py#L10" target="_blank">See source code</a></p>
<p>A component that catches errors and displays fallback content, similar to React's ErrorBoundary.</p>
<p>See React's <a href="https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary"><code>ErrorBoundary</code></a>
component.</p>
<p><strong>Parameters</strong>:</p>
<ul>
<li><strong>fallback</strong> (str, optional): A string to display when an error occurs.
The string is escaped, so it is shown as text. To render HTML, use the <code>fallback</code> slot,
or pass a string marked safe, such as <code>fallback="&lt;b&gt;Oops&lt;/b&gt;"|safe</code> or <code>mark_safe("&lt;b&gt;Oops&lt;/b&gt;")</code>.
Cannot be used together with the <code>fallback</code> slot.</li>
</ul>
<p><strong>Slots</strong>:</p>
<ul>
<li><strong>content</strong> or <strong>default</strong>: The main content that might raise an error.</li>
<li><strong>fallback</strong>: Custom fallback content to display when an error occurs. When using the <code>fallback</code> slot,
you can access the <code>error</code> object through slot data (<code>{% fill "fallback" data="data" %}</code>).
Cannot be used together with the <code>fallback</code> kwarg.</li>
</ul>
<div class="doc-section doc-examples"><p class="doc-section-title">Example</p><p>Given this template:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"error_fallback"</span> <span class="nv">fallback</span><span class="o">=</span><span class="s2">"Oops, something went wrong"</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<p>Then:</p>
<ul>
<li>If the <code>table</code> component does NOT raise an error, then the table is rendered as normal.</li>
<li>If the <code>table</code> component DOES raise an error, then <code>error_fallback</code> renders <code>Oops, something went wrong</code>.</li>
</ul>
<p>To have more control over the fallback content, you can use the <code>fallback</code> slot
instead of the <code>fallback</code> kwarg.</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"error_fallback"</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"content"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"fallback"</span> <span class="cp">%}</span>
<span class="x">        &lt;p&gt;Oops, something went wrong&lt;/p&gt;</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">button</span> <span class="nv">href</span><span class="o">=</span><span class="s2">"/report-error"</span> <span class="cp">%}</span>
<span class="x">            Report error</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">endbutton</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<p>If you want to print the error, you can access the <code>error</code> variable
as <a href="../concepts/fundamentals/slots.md#slot-data">slot data</a>.</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"error_fallback"</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"content"</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"fallback"</span> <span class="nv">data</span><span class="o">=</span><span class="s2">"data"</span> <span class="cp">%}</span>
<span class="x">        Oops, something went wrong:</span>
<span class="x">        &lt;pre&gt;</span><span class="cp">{{</span> <span class="nv">data.error</span> <span class="cp">}}</span><span class="x">&lt;/pre&gt;</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<p><strong>Python:</strong></p>
<p>With fallback kwarg:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ErrorFallback</span>

<span class="n">ErrorFallback</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
    <span class="n">slots</span><span class="o">=</span><span class="p">{</span>
        <span class="c1"># Main content</span>
        <span class="s2">"content"</span><span class="p">:</span> <span class="k">lambda</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">TableComponent</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
            <span class="n">deps_strategy</span><span class="o">=</span><span class="s2">"ignore"</span><span class="p">,</span>
        <span class="p">),</span>
    <span class="p">},</span>
    <span class="n">kwargs</span><span class="o">=</span><span class="p">{</span>
        <span class="c1"># Fallback content</span>
        <span class="s2">"fallback"</span><span class="p">:</span> <span class="s2">"Oops, something went wrong"</span><span class="p">,</span>
    <span class="p">},</span>
<span class="p">)</span>
</code></pre></div>
<p>With fallback slot:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ErrorFallback</span>

<span class="n">ErrorFallback</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
    <span class="n">slots</span><span class="o">=</span><span class="p">{</span>
        <span class="c1"># Main content</span>
        <span class="s2">"content"</span><span class="p">:</span> <span class="k">lambda</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">TableComponent</span><span class="o">.</span><span class="n">render</span><span class="p">(</span>
            <span class="n">deps_strategy</span><span class="o">=</span><span class="s2">"ignore"</span><span class="p">,</span>
        <span class="p">),</span>
        <span class="c1"># Fallback content</span>
        <span class="s2">"fallback"</span><span class="p">:</span> <span class="k">lambda</span> <span class="n">ctx</span><span class="p">:</span> <span class="n">format_html</span><span class="p">(</span><span class="s2">"Oops, something went wrong: </span><span class="si">{}</span><span class="s2">"</span><span class="p">,</span> <span class="n">ctx</span><span class="o">.</span><span class="n">data</span><span class="p">[</span><span class="s2">"error"</span><span class="p">]),</span>
    <span class="p">},</span>
<span class="p">)</span>
</code></pre></div></div>
<div class="admonition info">
<p class="admonition-title">Info</p>
<p>Remember to define the <code>content</code> slot as function, so it's evaluated from inside of <code>ErrorFallback</code>.</p>
</div>
                <div class="doc-members"><h3 class="doc-group-label">Attributes</h3><div class="doc doc-member"><h4 id="ErrorFallback.template" class="doc-member-heading"><span id="django_components.components.error_fallback.ErrorFallback.template"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-attribute" title="attribute"></span><span class="doc-object-name">template</span><a class="headerlink" href="#ErrorFallback.template" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>template: django_html</code></pre></div></div></div><h3 class="doc-group-label">Methods</h3><div class="doc doc-member"><h4 id="ErrorFallback.on_render" class="doc-member-heading"><span id="django_components.components.error_fallback.ErrorFallback.on_render"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-method" title="method"></span><span class="doc-object-name">on_render</span><a class="headerlink" href="#ErrorFallback.on_render" title="Permanent link">¤</a></h4><div class="doc-contents"><div class="doc-signature highlight"><pre><code>on_render(context: <a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context">Context</a>, template: <a class="doc-type-link" href="https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Template">Template</a> | None) -> <a class="doc-type-link" href="../api/#OnRenderGenerator">OnRenderGenerator</a></code></pre></div></div></div><h3 class="doc-group-label">Classes</h3><div class="doc doc-member"><h4 id="ErrorFallback.Kwargs" class="doc-member-heading"><span id="django_components.components.error_fallback.ErrorFallback.Kwargs"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc-object-name">Kwargs</span><a class="headerlink" href="#ErrorFallback.Kwargs" title="Permanent link">¤</a></h4><div class="doc-contents"></div></div><div class="doc doc-member"><h4 id="ErrorFallback.Slots" class="doc-member-heading"><span id="django_components.components.error_fallback.ErrorFallback.Slots"></span><span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc-object-name">Slots</span><a class="headerlink" href="#ErrorFallback.Slots" title="Permanent link">¤</a></h4><div class="doc-contents"></div></div></div>
</div>
</div>


