---
title: Tag formatters
url: https://django-components.github.io/django-components/v/0.152.1/docs/reference/tag_formatters/
description: "API reference - the predefined django-components tag formatters."
---

# Tag formatters

A [`TagFormatter`][TagFormatterABC] controls the start/end tag names a component is rendered with. django-components ships these predefined formatters.

## Available tag formatters

- `django_components.component_formatter` &rarr; [`ComponentFormatter`](#ComponentFormatter)
- `django_components.component_shorthand_formatter` &rarr; [`ShorthandComponentFormatter`](#ShorthandComponentFormatter)




<div class="doc doc-object doc-class doc-tag-formatter" data-djc-id-cao7wKO="">
<h2 id="ComponentFormatter" class="doc doc-heading">
<span id="django_components.tag_formatter.ComponentFormatter" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name doc-class-name">ComponentFormatter</span>
<a class="headerlink" href="#ComponentFormatter" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
<p class="doc doc-class-bases">Bases: <code>django_components.tag_formatter.TagFormatterABC</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/tag_formatter.py#L205" target="_blank">See source code</a></p>
<p>The original django_component's component tag formatter, it uses the <code>{% component %}</code>
and <code>{% endcomponent %}</code> tags, and the component name is given as the first positional arg.</p>
<p>Example as block:
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"mycomp"</span> <span class="nv">abc</span><span class="o">=</span><span class="m">123</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"myfill"</span> <span class="cp">%}</span>
<span class="x">        ...</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endcomponent</span> <span class="cp">%}</span>
</code></pre></div></p>
<p>Example as inlined tag:
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">component</span> <span class="s2">"mycomp"</span> <span class="nv">abc</span><span class="o">=</span><span class="m">123</span> <span class="o">/</span> <span class="cp">%}</span>
</code></pre></div></p>
</div>
</div>







<div class="doc doc-object doc-class doc-tag-formatter" data-djc-id-cdEMlHx="">
<h2 id="ShorthandComponentFormatter" class="doc doc-heading">
<span id="django_components.tag_formatter.ShorthandComponentFormatter" class="doc doc-legacy-anchor"></span>
<span class="doc doc-object-name doc-class-name">ShorthandComponentFormatter</span>
<a class="headerlink" href="#ShorthandComponentFormatter" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
<p class="doc doc-class-bases">Bases: <code>django_components.tag_formatter.TagFormatterABC</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/tag_formatter.py#L255" target="_blank">See source code</a></p>
<p>The component tag formatter that uses <code>{% &lt;name&gt; %}</code> / <code>{% end&lt;name&gt; %}</code> tags.</p>
<p>This is similar to <a href="https://github.com/Xzya/django-web-components">django-web-components</a>
and <a href="https://github.com/mixxorz/slippers">django-slippers</a>
syntax.</p>
<p>Example as block:
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">mycomp</span> <span class="nv">abc</span><span class="o">=</span><span class="m">123</span> <span class="cp">%}</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">fill</span> <span class="s2">"myfill"</span> <span class="cp">%}</span>
<span class="x">        ...</span>
<span class="x">    </span><span class="cp">{%</span> <span class="k">endfill</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endmycomp</span> <span class="cp">%}</span>
</code></pre></div></p>
<p>Example as inlined tag:
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">mycomp</span> <span class="nv">abc</span><span class="o">=</span><span class="m">123</span> <span class="o">/</span> <span class="cp">%}</span>
</code></pre></div></p>
</div>
</div>


