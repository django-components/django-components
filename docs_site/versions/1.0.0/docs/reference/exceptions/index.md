---
title: Exceptions
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/exceptions/
description: "API reference - Exceptions."
---

# Exceptions




<div class="doc doc-object doc-class" data-djc-id-cdTGexp="">
<h2 id="AlreadyRegistered" class="doc doc-heading">
<span id="django_components.AlreadyRegistered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">AlreadyRegistered</span>
<a class="headerlink" href="#AlreadyRegistered" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>AlreadyRegistered()</code></pre></div>
<p class="doc doc-class-bases">Bases: <code>Exception</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/component_registry.py#L32" target="_blank">See source code</a></p>
<p>Raised when you try to register a <a href="../api/#Component">Component</a>
under a name that is already registered with the given
<a href="../api/#ComponentRegistry">ComponentRegistry</a>.</p>
<p>Re-registering the exact same class object under the same name is a no-op
and does NOT raise - so calling <code>autodiscover()</code> or <code>import_libraries()</code>
more than once is safe. Any <em>other</em> class under that name raises and you
must call <a href="../api/#ComponentRegistry.unregister"><code>unregister()</code></a>
first to replace the existing registration.</p>

</div>
</div>







<div class="doc doc-object doc-class" data-djc-id-czKfASd="">
<h2 id="NotRegistered" class="doc doc-heading">
<span id="django_components.NotRegistered" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">NotRegistered</span>
<a class="headerlink" href="#NotRegistered" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>NotRegistered()</code></pre></div>
<p class="doc doc-class-bases">Bases: <code>Exception</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/component_registry.py#L46" target="_blank">See source code</a></p>
<p>Raised when you try to access a <a href="../api/#Component">Component</a>,
but it's NOT registered with given
<a href="../api/#ComponentRegistry">ComponentRegistry</a>.</p>

</div>
</div>







<div class="doc doc-object doc-class" data-djc-id-cog64qY="">
<h2 id="TagProtectedError" class="doc doc-heading">
<span id="django_components.TagProtectedError" class="doc doc-legacy-anchor"></span>
<span class="doc doc-symbol doc-symbol-heading doc-symbol-class" title="class"></span><span class="doc doc-object-name doc-class-name">TagProtectedError</span>
<a class="headerlink" href="#TagProtectedError" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>TagProtectedError()</code></pre></div>
<p class="doc doc-class-bases">Bases: <code>Exception</code></p>

<p><a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/library.py#L9" target="_blank">See source code</a></p>
<p>The way the <a href="./../concepts/advanced/tag_formatters.md"><code>TagFormatter</code></a> works is that,
based on which start and end tags are used for rendering components,
the <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a> behind the scenes
<a href="https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#registering-the-tag">un-/registers the template tags</a>
with the associated instance of Django's
<a href="https://docs.djangoproject.com/en/5.2/howto/custom-template-tags/#code-layout"><code>Library</code></a>.</p>
<p>In other words, if I have registered a component <code>"table"</code>, and I use the shorthand
syntax:</p>
<div class="highlight"><pre><span></span><code><span class="cp">{%</span> <span class="k">table</span> <span class="p">...</span> <span class="cp">%}</span>
<span class="cp">{%</span> <span class="k">endtable</span> <span class="cp">%}</span>
</code></pre></div>
<p>Then <a href="../api/#ComponentRegistry"><code>ComponentRegistry</code></a>
registers the tag <code>table</code> onto the Django's Library instance.</p>
<p>However, that means that if we registered a component <code>"slot"</code>, then we would overwrite
the <a href="./template_tags.md#slot"><code>{% slot %}</code></a> tag from django_components.</p>
<p>Thus, this exception is raised when a component is attempted to be registered under
a forbidden name, such that it would overwrite one of django_component's own template tags.</p>

</div>
</div>


