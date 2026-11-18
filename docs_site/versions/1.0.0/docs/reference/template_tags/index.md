---
title: Template tags
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/template_tags/
description: "API reference - the django-components template tags."
---

# Template tags

django-components provides the following template tags. Load them with `{% load component_tags %}` (or add the library to your template builtins).




<div class="doc doc-object doc-template-tag" data-djc-id-cMQSwKv="">
<h2 id="attrs" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">attrs</span>
<a class="headerlink" href="#attrs" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% attrs *attrs: collections.abc.Mapping[str, typing.Any] | list[&#x27;AttrsSource&#x27;] | tuple[&#x27;AttrsSource&#x27;, ...] %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/attributes.py#L154" target="_blank">See source code</a>


<p>Compose mappings into an attribute dictionary and render it as HTML attributes.</p>
<p>Each argument may be a mapping or an arbitrarily nested list or tuple of
mappings. Sources are applied from left to right. Ordinary attributes use the
last value, while <code>class</code> and <code>style</code> contributions are combined using the same
structured values as <code>normalize_class()</code> and
<code>normalize_style()</code>.</p>
<div class="highlight"><pre><span></span><code><span class="x">&lt;div </span><span class="cp">{%</span> <span class="k">attrs</span> <span class="o">[</span><span class="nv">base_attrs</span><span class="o">,</span> <span class="o">[</span><span class="nv">state_attrs</span><span class="o">]]</span> <span class="nv">local_attrs</span> <span class="cp">%}</span><span class="x">&gt;&lt;/div&gt;</span>
</code></pre></div>
<p>When the tag is the sole node in a nested template expression, it returns an
<a href="../api/#AttrsDict"><code>AttrsDict</code></a> without serializing it. This makes it possible to pass
the result directly to a component:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span>
    <span class="nv">table_attrs</span><span class="o">=</span><span class="s2">"{% attrs [base_attrs, {'class': 'compact'}] %}"</span>
<span class="o">/</span> <span class="cp">%}</span>
</code></pre></div>
<p>Any surrounding text or template nodes cause the result to be serialized to
an escaped, space-delimited attribute string.</p>
<p>This tag supersedes <code>{% html_attrs %}</code> for attribute composition. Prefer
<code>{% attrs %}</code> in new code; <code>{% html_attrs %}</code> remains supported for backward
compatibility.</p>
<p>See <a href="../concepts/fundamentals/html_attributes.md">HTML attributes</a> for details.</p>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-cyyzSG5="">
<h2 id="component" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">component</span>
<a class="headerlink" href="#component" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% component *args: Any, **kwargs: Any [only] %}
{% endcomponent %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/component.py#L3435" target="_blank">See source code</a>


<p>Renders one of the components that was previously registered with
<a href="../api/#register"><code>@register()</code></a>
decorator.</p>
<p>The <a href="#component"><code>{% component %}</code></a> tag takes:</p>
<ul>
<li>Component's registered name as the first positional argument,</li>
<li>Followed by any number of positional and keyword arguments.</li>
</ul>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">load</span> <span class="nv">component_tags</span> <span class="cp">%}</span>
<span class="x">&lt;div&gt;</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"button"</span> <span class="nv">name</span><span class="o">=</span><span class="s2">"John"</span> <span class="nv">job</span><span class="o">=</span><span class="s2">"Developer"</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="x">&lt;/div&gt;</span>
</code></pre></div>
<p>The component name must be a string literal.</p>
<h3>Inserting slot fills</h3>
<p>If the component defined any <a href="../concepts/fundamentals/slots.md">slots</a>, you can
"fill" these slots by placing the <a href="#fill"><code>{% fill %}</code></a> tags
within the <a href="#component"><code>{% component %}</code></a> tag:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_table"</span> <span class="nv">rows</span><span class="o">=</span><span class="nv">rows</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">headers</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">    &lt; 1 | 2 | 3 &gt;</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<p>You can even nest <a href="#fill"><code>{% fill %}</code></a> tags within
<a href="https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#if"><code>{% if %}</code></a>,
<a href="https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#for"><code>{% for %}</code></a>
and other tags:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_table"</span> <span class="nv">rows</span><span class="o">=</span><span class="nv">rows</span> <span class="nv">headers</span><span class="o">=</span><span class="nv">headers</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">if</span> <span class="nv">rows</span> <span class="cp">%}</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">            &lt; 1 | 2 | 3 &gt;</span>
<span class="x">        </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endif</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<h3>Isolating components</h3>
<p>By default, components behave similarly to Django's
<a href="https://docs.djangoproject.com/en/5.2/ref/templates/builtins/#include"><code>{% include %}</code></a>,
and the template inside the component has access to the variables defined in the outer template.</p>
<p>You can selectively isolate a component, using the <code>only</code> flag, so that the inner template
can access only the data that was explicitly passed to it:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"name"</span> <span class="nv">positional_arg</span> <span class="nv">keyword_arg</span><span class="o">=</span><span class="nv">value</span> <span class="p">...</span> <span class="nv">only</span> <span class="cp">%}</span>
</code></pre></div>
<p>Alternatively, you can set all components to be isolated by default, by setting
<a href="../settings/#context_behavior"><code>context_behavior</code></a>
to <code>"isolated"</code> in your settings:</p>
<div class="highlight"><pre><span></span><code><span class="c1"># settings.py</span>
<span class="n">COMPONENTS</span> <span class="o">=</span> <span class="p">{</span>
    <span class="s2">"context_behavior"</span><span class="p">:</span> <span class="s2">"isolated"</span><span class="p">,</span>
<span class="p">}</span>
</code></pre></div>
<h3>Omitting the component keyword</h3>
<p>If you would like to omit the <code>component</code> keyword, and simply refer to your
components by their registered names:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">button</span> <span class="nv">name</span><span class="o">=</span><span class="s2">"John"</span> <span class="nv">job</span><span class="o">=</span><span class="s2">"Developer"</span> <span class="o">/</span> <span class="cp">%}</span>
</code></pre></div>
<p>You can do so by setting the "shorthand" <a href="../concepts/advanced/tag_formatters.md">Tag formatter</a>
in the settings:</p>
<div class="highlight"><pre><span></span><code><span class="c1"># settings.py</span>
<span class="n">COMPONENTS</span> <span class="o">=</span> <span class="p">{</span>
    <span class="s2">"tag_formatter"</span><span class="p">:</span> <span class="s2">"django_components.component_shorthand_formatter"</span><span class="p">,</span>
<span class="p">}</span>
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-cXibLHr="">
<h2 id="component_css_dependencies" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">component_css_dependencies</span>
<a class="headerlink" href="#component_css_dependencies" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% component_css_dependencies %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/dependencies.py#L2365" target="_blank">See source code</a>


<p>Marks location where CSS link tags should be rendered after the whole HTML has been generated.</p>
<p>Generally, this should be inserted into the <code>&lt;head&gt;</code> tag of the HTML.</p>
<p>If the generated HTML does NOT contain any <code>{% component_css_dependencies %}</code> tags, CSS links
are by default inserted into the <code>&lt;head&gt;</code> tag of the HTML. (See
<a href="../concepts/advanced/rendering_js_css.md#default-js-css-locations">Default JS / CSS locations</a>)</p>
<p>Note that there should be only one <code>{% component_css_dependencies %}</code> for the whole HTML document.
If you insert this tag multiple times, ALL CSS links will be duplicately inserted into ALL these places.</p>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-clXIDt8="">
<h2 id="component_js_dependencies" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">component_js_dependencies</span>
<a class="headerlink" href="#component_js_dependencies" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% component_js_dependencies %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/dependencies.py#L2387" target="_blank">See source code</a>


<p>Marks location where JS link tags should be rendered after the whole HTML has been generated.</p>
<p>Generally, this should be inserted at the end of the <code>&lt;body&gt;</code> tag of the HTML.</p>
<p>If the generated HTML does NOT contain any <code>{% component_js_dependencies %}</code> tags, JS scripts
are by default inserted at the end of the <code>&lt;body&gt;</code> tag of the HTML. (See
<a href="../concepts/advanced/rendering_js_css.md#default-js-css-locations">Default JS / CSS locations</a>)</p>
<p>Note that there should be only one <code>{% component_js_dependencies %}</code> for the whole HTML document.
If you insert this tag multiple times, ALL JS scripts will be duplicately inserted into ALL these places.</p>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-caJHTKT="">
<h2 id="fill" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">fill</span>
<a class="headerlink" href="#fill" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% fill name: str, *, data: str | None = None, fallback: str | None = None, body: Union[str, django.utils.safestring.SafeString, django_components.slots.SlotFunc[~TSlotData], django_components.slots.Slot[~TSlotData], NoneType] = None, default: str | None = None %}
{% endfill %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/slots.py#L988" target="_blank">See source code</a>


<p>Use <a href="#fill"><code>{% fill %}</code></a> tag to insert content into component's
<a href="../concepts/fundamentals/slots.md">slots</a>.</p>
<p><a href="#fill"><code>{% fill %}</code></a> tag may be used only within a <code>{% component %}..{% endcomponent %}</code> block,
and raises a <code>TemplateSyntaxError</code> if used outside of a component.</p>
<p>Args:
name (str, required): Name of the slot to insert this content into. Use <code>"default"</code> for
the <a href="../concepts/fundamentals/slots.md#default-slot">default slot</a>.
data (str, optional): This argument allows you to access the data passed to the slot
under the specified variable name. See <a href="../concepts/fundamentals/slots.md#slot-data">Slot data</a>.
fallback (str, optional): This argument allows you to access the original content of the slot
under the specified variable name. See <a href="../concepts/fundamentals/slots.md#slot-fallback">Slot fallback</a>.</p>
<p>Examples:
    <div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_table"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">    &lt; 1 | 2 | 3 &gt;</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div></p>
<h3>Access slot fallback</h3>
<p>Use the <code>fallback</code> kwarg to access the original content of the slot.</p>
<p>The <code>fallback</code> kwarg defines the name of the variable that will contain the slot's fallback content.</p>
<p>Read more about <a href="../concepts/fundamentals/slots.md#slot-fallback">Slot fallback</a>.</p>
<p>Component template:</p>
<div class="highlight"><pre><span></span><code><span class="c">{# my_table.html #}</span>
<span class="x">&lt;table&gt;</span>
<span class="x">  ...</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"pagination"</span> <span class="cp">%}</span>
<span class="x">    &lt; 1 | 2 | 3 &gt;</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endslot</span> <span class="cp">%}</span>
<span class="x">&lt;/table&gt;</span>
</code></pre></div>
<p>Fill:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_table"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="nv">fallback</span><span class="o">=</span><span class="s2">"fallback"</span> <span class="cp">%}</span>
<span class="x">    &lt;div class="my-class"&gt;</span>
<span class="x">      </span><span class="cp">{{</span> <span class="nv">fallback</span> <span class="cp">}}</span>
<span class="x">    &lt;/div&gt;</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<h3>Access slot data</h3>
<p>Use the <code>data</code> kwarg to access the data passed to the slot.</p>
<p>The <code>data</code> kwarg defines the name of the variable that will contain the slot's data.</p>
<p>Read more about <a href="../concepts/fundamentals/slots.md#slot-data">Slot data</a>.</p>
<p>Component template:</p>
<div class="highlight"><pre><span></span><code><span class="c">{# my_table.html #}</span>
<span class="x">&lt;table&gt;</span>
<span class="x">  ...</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"pagination"</span> <span class="nv">pages</span><span class="o">=</span><span class="nv">pages</span> <span class="cp">%}</span>
<span class="x">    &lt; 1 | 2 | 3 &gt;</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endslot</span> <span class="cp">%}</span>
<span class="x">&lt;/table&gt;</span>
</code></pre></div>
<p>Fill:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"my_table"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="nv">data</span><span class="o">=</span><span class="s2">"slot_data"</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">for</span> <span class="nv">page</span> <span class="k">in</span> <span class="nv">slot_data.pages</span> <span class="cp">%}</span>
<span class="x">        &lt;a href="</span><span class="cp">{{</span> <span class="nv">page.link</span> <span class="cp">}}</span><span class="x">"&gt;</span>
<span class="x">          </span><span class="cp">{{</span> <span class="nv">page.index</span> <span class="cp">}}</span>
<span class="x">        &lt;/a&gt;</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfor</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<h3>Using default slot</h3>
<p>To access slot data and the fallback slot content on the default slot,
use <a href="#fill"><code>{% fill %}</code></a> with <code>name</code> set to <code>"default"</code>:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"button"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="nv">name</span><span class="o">=</span><span class="s2">"default"</span> <span class="nv">data</span><span class="o">=</span><span class="s2">"slot_data"</span> <span class="nv">fallback</span><span class="o">=</span><span class="s2">"slot_fallback"</span> <span class="cp">%}</span>
<span class="x">    You clicked me </span><span class="cp">{{</span> <span class="nv">slot_data.count</span> <span class="cp">}}</span><span class="x"> times!</span>
<span class="x">    </span><span class="cp">{{</span> <span class="nv">slot_fallback</span> <span class="cp">}}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<h3>Slot fills from Python</h3>
<p>You can pass a slot fill from Python to a component by setting the <code>body</code> kwarg
on the <a href="#fill"><code>{% fill %}</code></a> tag.</p>
<p>First pass a <a href="../api/#Slot"><code>Slot</code></a> instance to the template
with the <a href="../api/#Component.get_template_data"><code>get_template_data()</code></a>
method:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">component</span><span class="p">,</span> <span class="n">Slot</span>

<span class="k">class</span><span class="w"> </span><span class="nc">Table</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
  <span class="k">def</span><span class="w"> </span><span class="nf">get_template_data</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">args</span><span class="p">,</span> <span class="n">kwargs</span><span class="p">,</span> <span class="n">slots</span><span class="p">,</span> <span class="n">context</span><span class="p">):</span>
    <span class="k">return</span> <span class="p">{</span>
        <span class="s2">"my_slot"</span><span class="p">:</span> <span class="n">Slot</span><span class="p">(</span><span class="k">lambda</span> <span class="n">ctx</span><span class="p">:</span> <span class="s2">"Hello, world!"</span><span class="p">),</span>
    <span class="p">}</span>
</code></pre></div>
<p>Then pass the slot to the <a href="#fill"><code>{% fill %}</code></a> tag:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="nv">body</span><span class="o">=</span><span class="nv">my_slot</span> <span class="o">/</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>If you define both the <code>body</code> kwarg and the <a href="#fill"><code>{% fill %}</code></a> tag's body,
an error will be raised.</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"table"</span> <span class="cp">%}</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"pagination"</span> <span class="nv">body</span><span class="o">=</span><span class="nv">my_slot</span> <span class="cp">%}</span>
<span class="x">    ...</span>
<span class="x">  </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div>
</div>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-cZw3vts="">
<h2 id="html_attrs" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">html_attrs</span>
<a class="headerlink" href="#html_attrs" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% html_attrs attrs: dict | None = None, defaults: dict | None = None, **kwargs: Any %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/attributes.py#L34" target="_blank">See source code</a>


<p>Generate HTML attributes (<code>key="value"</code>), combining data from multiple sources,
whether its template variables or static text.</p>
<p>It is designed to easily merge HTML attributes passed from outside as well as inside the component.</p>
<p>Args:
attrs (dict, optional): Optional dictionary that holds HTML attributes. On conflict, overrides
values in the <code>default</code> dictionary.
default (str, optional): Optional dictionary that holds HTML attributes. On conflict, is overriden
with values in the <code>attrs</code> dictionary.
**kwargs: Any extra kwargs will be appended to the corresponding keys.</p>
<p>The attributes in <code>attrs</code> and <code>defaults</code> are merged and resulting dict is rendered as HTML attributes
(<code>key="value"</code>).</p>
<p>Extra kwargs (<code>key=value</code>) are concatenated to existing keys. So if we have</p>
<div class="highlight"><pre><span></span><code><span class="n">attrs</span> <span class="o">=</span> <span class="p">{</span><span class="s2">"class"</span><span class="p">:</span> <span class="s2">"my-class"</span><span class="p">}</span>
</code></pre></div>
<p>Then</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">html_attrs</span> <span class="nv">attrs</span> <span class="nv">class</span><span class="o">=</span><span class="s2">"extra-class"</span> <span class="cp">%}</span>
</code></pre></div>
<p>will result in <code>class="my-class extra-class"</code>.</p>
<p>Examples:
    <div class="highlight"><pre><span></span><code><span class="x">&lt;div </span><span class="cp">{%</span> <span class="k">html_attrs</span>
    <span class="nv">attrs</span>
    <span class="nv">defaults</span><span class="o">:</span><span class="nv">class</span><span class="o">=</span><span class="s2">"default-class"</span>
    <span class="nv">class</span><span class="o">=</span><span class="s2">"extra-class"</span>
    <span class="nv">data-id</span><span class="o">=</span><span class="s2">"123"</span>
<span class="cp">%}</span><span class="x">&gt;</span>
</code></pre></div></p>
<div class="highlight"><pre><span></span><code>renders

```html
&lt;div class="my-class extra-class" data-id="123"&gt;
```

See more usage examples in
[HTML attributes](../concepts/fundamentals/html_attributes.md).
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-cLRmfXU="">
<h2 id="provide" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">provide</span>
<a class="headerlink" href="#provide" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% provide name: str, **kwargs: Any %}
{% endprovide %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/provide.py#L12" target="_blank">See source code</a>


<p>The <a href="#provide"><code>{% provide %}</code></a> tag is part of the "provider" part of
the <a href="../concepts/advanced/provide_inject.md">provide / inject feature</a>.</p>
<p>Pass kwargs to this tag to define the provider's data.</p>
<p>Any components defined within the <code>{% provide %}..{% endprovide %}</code> tags will be able to access this data
with <a href="../api/#Component.inject"><code>Component.inject()</code></a>.</p>
<p>This is similar to React's <a href="https://react.dev/learn/passing-data-deeply-with-context"><code>ContextProvider</code></a>,
or Vue's <a href="https://vuejs.org/guide/components/provide-inject"><code>provide()</code></a>.</p>
<p>Args:
name (str, required): Provider name. This is the name you will then use in
<a href="../api/#Component.inject"><code>Component.inject()</code></a>.
**kwargs: Any extra kwargs will be passed as the provided data.</p>
<p>Examples:
Provide the "user_data" in parent component:</p>
<div class="highlight"><pre><span></span><code>```djc_py
@register("parent")
class Parent(Component):
    template = """
      &lt;div&gt;
        {% provide "user_data" user=user %}
          {% component "child" / %}
        {% endprovide %}
      &lt;/div&gt;
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "user": kwargs["user"],
        }
```

Since the "child" component is used within the `{% provide %} / {% endprovide %}` tags,
we can request the "user_data" using `Component.inject("user_data")`:

```djc_py
@register("child")
class Child(Component):
    template = """
      &lt;div&gt;
        User is: {{ user }}
      &lt;/div&gt;
    """

    def get_template_data(self, args, kwargs, slots, context):
        user = self.inject("user_data").user
        return {
            "user": user,
        }
```

Notice that the keys defined on the [`{% provide %}`](#provide) tag are then accessed as attributes
when accessing them with [`Component.inject()`](../api/#Component.inject).

✅ Do this
```python
user = self.inject("user_data").user
```

❌ Don't do this
```python
user = self.inject("user_data")["user"]
```
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-template-tag" data-djc-id-cruO9lA="">
<h2 id="slot" class="doc doc-heading">
<span class="doc doc-object-name doc-tag-name">slot</span>
<a class="headerlink" href="#slot" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>{% slot name: str, **kwargs: Any [default] [required] %}
{% endslot %}</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/slots.py#L501" target="_blank">See source code</a>


<p><a href="#slot"><code>{% slot %}</code></a> tag marks a place inside a component where content can be inserted
from outside.</p>
<p><a href="../concepts/fundamentals/slots.md">Learn more about using slots</a>.</p>
<p>This is similar to slots as seen in
<a href="https://developer.mozilla.org/en-US/docs/Web/HTML/Element/slot">Web components</a>,
<a href="https://vuejs.org/guide/components/slots.html">Vue</a>
or <a href="https://react.dev/learn/passing-props-to-a-component#passing-jsx-as-children">React's <code>children</code></a>.</p>
<p>Args:
name (str, required): Registered name of the component to render
default: Optional flag. If there is a default slot, you can pass the component slot content
without using the <a href="#fill"><code>{% fill %}</code></a> tag. See
<a href="../concepts/fundamentals/slots.md#default-slot">Default slot</a>
required: Optional flag. Will raise an error if a slot is required but not given.
**kwargs: Any extra kwargs will be passed as the slot data.</p>
<p>Examples:
    <div class="highlight"><pre><span></span><code><span class="nd">@register</span><span class="p">(</span><span class="s2">"child"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Child</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">"""</span>
      <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
        <span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"content"</span> <span class="nv">default</span> <span class="cp">%}</span>
          This is shown if not overriden!
        <span class="cp">{%</span> <span class="k">endslot</span> <span class="cp">%}</span>
      <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
      <span class="p">&lt;</span><span class="nt">aside</span><span class="p">&gt;</span>
        <span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"sidebar"</span> <span class="nv">required</span> <span class="o">/</span> <span class="cp">%}</span>
      <span class="p">&lt;/</span><span class="nt">aside</span><span class="p">&gt;</span>
    <span class="sd">"""</span>
</code></pre></div></p>
<div class="highlight"><pre><span></span><code>```djc_py
@register("parent")
class Parent(Component):
    template = """
      &lt;div&gt;
        {% component "child" %}
          {% fill "content" %}
            🗞️📰
          {% endfill %}

          {% fill "sidebar" %}
            🍷🧉🍾
          {% endfill %}
        {% endcomponent %}
      &lt;/div&gt;
    """
```
</code></pre></div>
<h3>Slot data</h3>
<p>Any extra kwargs will be considered as slot data, and will be accessible
in the <a href="#fill"><code>{% fill %}</code></a> tag via fill's <code>data</code> kwarg:</p>
<p>Read more about <a href="../concepts/fundamentals/slots.md#slot-data">Slot data</a>.</p>
<div class="highlight"><pre><span></span><code><span class="nd">@register</span><span class="p">(</span><span class="s2">"child"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Child</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">"""</span>
      <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
        <span class="c">{# Passing data to the slot #}</span>
        <span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"content"</span> <span class="nv">user</span><span class="o">=</span><span class="nv">user</span> <span class="cp">%}</span>
          This is shown if not overriden!
        <span class="cp">{%</span> <span class="k">endslot</span> <span class="cp">%}</span>
      <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">"""</span>
</code></pre></div>
<div class="highlight"><pre><span></span><code><span class="nd">@register</span><span class="p">(</span><span class="s2">"parent"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Parent</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">"""</span>
      <span class="c">{# Parent can access the slot data #}</span>
      <span class="cp">{%</span> <span class="k">component</span> <span class="s2">"child"</span> <span class="cp">%}</span>
        <span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"content"</span> <span class="nv">data</span><span class="o">=</span><span class="s2">"data"</span> <span class="cp">%}</span>
          <span class="p">&lt;</span><span class="nt">div</span> <span class="na">class</span><span class="o">=</span><span class="s">"wrapper-class"</span><span class="p">&gt;</span>
            <span class="cp">{{</span> <span class="nv">data.user</span> <span class="cp">}}</span>
          <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
        <span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
      <span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
    <span class="sd">"""</span>
</code></pre></div>
<h3>Slot fallback</h3>
<p>The content between the <code>{% slot %}..{% endslot %}</code> tags is the fallback content that
will be rendered if no fill is given for the slot.</p>
<p>This fallback content can then be accessed from within the <a href="#fill"><code>{% fill %}</code></a> tag
using the fill's <code>fallback</code> kwarg.
This is useful if you need to wrap / prepend / append the original slot's content.</p>
<div class="highlight"><pre><span></span><code><span class="nd">@register</span><span class="p">(</span><span class="s2">"child"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Child</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">"""</span>
      <span class="p">&lt;</span><span class="nt">div</span><span class="p">&gt;</span>
        <span class="cp">{%</span> <span class="k">slot</span> <span class="s2">"content"</span> <span class="cp">%}</span>
          This is fallback content!
        <span class="cp">{%</span> <span class="k">endslot</span> <span class="cp">%}</span>
      <span class="p">&lt;/</span><span class="nt">div</span><span class="p">&gt;</span>
    <span class="sd">"""</span>
</code></pre></div>
<div class="highlight"><pre><span></span><code><span class="nd">@register</span><span class="p">(</span><span class="s2">"parent"</span><span class="p">)</span>
<span class="k">class</span><span class="w"> </span><span class="nc">Parent</span><span class="p">(</span><span class="n">Component</span><span class="p">):</span>
    <span class="nv">template</span> <span class="o">=</span> <span class="sd">"""</span>
      <span class="c">{# Parent can access the slot's fallback content #}</span>
      <span class="cp">{%</span> <span class="k">component</span> <span class="s2">"child"</span> <span class="cp">%}</span>
        <span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"content"</span> <span class="nv">fallback</span><span class="o">=</span><span class="s2">"fallback"</span> <span class="cp">%}</span>
          <span class="cp">{{</span> <span class="nv">fallback</span> <span class="cp">}}</span>
        <span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
      <span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
    <span class="sd">"""</span>
</code></pre></div>
</div>
</div>


