---
title: CLI commands
url: https://django-components.github.io/django-components/v/1.0.0/docs/reference/commands/
description: "API reference - the django-components CLI commands."
---

# CLI commands

These are the [Django management commands](https://docs.djangoproject.com/en/5.2/ref/django-admin) that installing `django_components` adds. All of them live under the `components` command.




<div class="doc doc-object doc-command" data-djc-id-cUonxPr="">
<h2 id="components" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components</span>
<a class="headerlink" href="#components" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components [-h] {create,upgrade,ext,list} ...</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/components.py#L11" target="_blank">See source code</a>


<p>The entrypoint for the 'components' commands.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li></ul></div><div class="doc-section doc-command-args"><p class="doc-section-title">Subcommands</p><ul><li><a href="#components-create"><code>create</code></a> &ndash; Create a new django component.</li><li><a href="#components-upgrade"><code>upgrade</code></a> &ndash; Upgrade django components syntax from &#x27;{% component_block ... %}&#x27; to &#x27;{% component ... %}&#x27;.</li><li><a href="#components-ext"><code>ext</code></a> &ndash; Run extension commands.</li><li><a href="#components-list"><code>list</code></a> &ndash; List all components created in this project.</li></ul></div>
<p>The entrypoint for the "components" commands.</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>list
python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>&lt;name&gt;
python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>upgrade
python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list
python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>run<span class="w"> </span>&lt;extension&gt;<span class="w"> </span>&lt;command&gt;
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-cPFFVcf="">
<h2 id="components-create" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components create</span>
<a class="headerlink" href="#components-create" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components create [-h] [--path PATH] [--js JS] [--css CSS] [--template TEMPLATE]
              [--force] [--verbose] [--dry-run]
              name</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/create.py#L12" target="_blank">See source code</a>


<p>Create a new django component.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Positional Arguments</p><ul><li><code>name</code> &ndash; The name of the component to create. This is a required argument.</li></ul></div><div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li><li><code>--path PATH</code> &ndash; The path to the component&#x27;s directory. This is an optional argument. If not provided, the command will use the `COMPONENTS.dirs` setting from your Django settings.</li><li><code>--js JS</code> &ndash; The name of the JavaScript file. This is an optional argument. The default value is `script.js`.</li><li><code>--css CSS</code> &ndash; The name of the CSS file. This is an optional argument. The default value is `style.css`.</li><li><code>--template TEMPLATE</code> &ndash; The name of the template file. This is an optional argument. The default value is `template.html`.</li><li><code>--force</code> &ndash; This option allows you to overwrite existing files if they exist. This is an optional argument.</li><li><code>--verbose</code> &ndash; This option allows the command to print additional information during component creation. This is an optional argument.</li><li><code>--dry-run</code> &ndash; This option allows you to simulate component creation without actually creating any files. This is an optional argument. The default value is `False`.</li></ul></div>
<h3>Usage</h3>
<p>To use the command, run the following command in your terminal:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>&lt;name&gt;<span class="w"> </span>--path<span class="w"> </span>&lt;path&gt;<span class="w"> </span>--js<span class="w"> </span>&lt;js_filename&gt;<span class="w"> </span>--css<span class="w"> </span>&lt;css_filename&gt;<span class="w"> </span>--template<span class="w"> </span>&lt;template_filename&gt;<span class="w"> </span>--force<span class="w"> </span>--verbose<span class="w"> </span>--dry-run
</code></pre></div>
<p>Replace <code>&lt;name&gt;</code>, <code>&lt;path&gt;</code>, <code>&lt;js_filename&gt;</code>, <code>&lt;css_filename&gt;</code>, and <code>&lt;template_filename&gt;</code> with your desired values.</p>
<h3>Examples</h3>
<p>Here are some examples of how you can use the command:</p>
<p><strong>Creating a Component with Default Settings</strong></p>
<p>To create a component with the default settings, you only need to provide the name of the component:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>my_component
</code></pre></div>
<p>This will create a new component named <code>my_component</code> in the <code>components</code> directory of your Django project. The JavaScript, CSS, and template files will be named <code>script.js</code>, <code>style.css</code>, and <code>template.html</code>, respectively.</p>
<p><strong>Creating a Component with Custom Settings</strong></p>
<p>You can also create a component with custom settings by providing additional arguments:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>new_component<span class="w"> </span>--path<span class="w"> </span>my_components<span class="w"> </span>--js<span class="w"> </span>my_script.js<span class="w"> </span>--css<span class="w"> </span>my_style.css<span class="w"> </span>--template<span class="w"> </span>my_template.html
</code></pre></div>
<p>This will create a new component named <code>new_component</code> in the <code>my_components</code> directory. The JavaScript, CSS, and template files will be named <code>my_script.js</code>, <code>my_style.css</code>, and <code>my_template.html</code>, respectively.</p>
<p><strong>Overwriting an Existing Component</strong></p>
<p>If you want to overwrite an existing component, you can use the <code>--force</code> option:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>my_component<span class="w"> </span>--force
</code></pre></div>
<p>This will overwrite the existing <code>my_component</code> if it exists.</p>
<p><strong>Simulating Component Creation</strong></p>
<p>If you want to simulate the creation of a component without actually creating any files, you can use the <code>--dry-run</code> option:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>create<span class="w"> </span>my_component<span class="w"> </span>--dry-run
</code></pre></div>
<p>This will simulate the creation of <code>my_component</code> without creating any files.</p>
</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-ciDqOAM="">
<h2 id="components-upgrade" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components upgrade</span>
<a class="headerlink" href="#components-upgrade" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components upgrade [-h] [--path PATH]</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/upgrade.py#L15" target="_blank">See source code</a>


<p>Upgrade django components syntax from '{% component_block ... %}' to '{% component ... %}'.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li><li><code>--path PATH</code> &ndash; Path to search for components</li></ul></div>

</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-c7ACFD3="">
<h2 id="components-ext" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components ext</span>
<a class="headerlink" href="#components-ext" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components ext [-h] {list,run} ...</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/ext.py#L6" target="_blank">See source code</a>


<p>Run extension commands.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li></ul></div><div class="doc-section doc-command-args"><p class="doc-section-title">Subcommands</p><ul><li><a href="#components-ext-list"><code>list</code></a> &ndash; List all extensions.</li><li><a href="#components-ext-run"><code>run</code></a> &ndash; Run a command added by an extension.</li></ul></div>
<p>Run extension commands.</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list
python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>run<span class="w"> </span>&lt;extension&gt;<span class="w"> </span>&lt;command&gt;
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-cw98YA0="">
<h2 id="components-ext-list" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components ext list</span>
<a class="headerlink" href="#components-ext-list" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components ext list [-h] [--all] [--columns COLUMNS] [-s]</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/ext_list.py#L7" target="_blank">See source code</a>


<p>List all extensions.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li><li><code>--all</code> &ndash; Show all columns. Same as `--columns name`.</li><li><code>--columns COLUMNS</code> &ndash; Comma-separated list of columns to show. Available columns: name. Defaults to `--columns name`.</li><li><code>-s</code>, <code>--simple</code> &ndash; Only show table data, without headers. Use this option for generating machine-readable output.</li></ul></div>
<p>List all extensions.</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list
</code></pre></div>
<p>Prints the list of installed extensions:</p>
<div class="highlight"><pre><span></span><code>name
==============
view
my_extension
</code></pre></div>
<p>To specify which columns to show, use the <code>--columns</code> flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list<span class="w"> </span>--columns<span class="w"> </span>name
</code></pre></div>
<p>Which prints:</p>
<div class="highlight"><pre><span></span><code>name
==============
view
my_extension
</code></pre></div>
<p>To print out all columns, use the <code>--all</code> flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list<span class="w"> </span>--all
</code></pre></div>
<p>If you need to omit the title in order to programmatically post-process the output,
you can use the <code>--simple</code> (or <code>-s</code>) flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>list<span class="w"> </span>--simple
</code></pre></div>
<p>Which prints just:</p>
<div class="highlight"><pre><span></span><code>view
my_extension
</code></pre></div>
</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-cv2mj5f="">
<h2 id="components-ext-run" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components ext run</span>
<a class="headerlink" href="#components-ext-run" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components ext run [-h]</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/ext_run.py#L52" target="_blank">See source code</a>


<p>Run a command added by an extension.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li></ul></div>
<p>Run a command added by an <a href="../concepts/advanced/extensions.md">extension</a>.</p>
<p>Each extension can add its own commands, which will be available to run with this command.</p>
<p>For example, if you define and install the following extension:</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">ComponentCommand</span><span class="p">,</span> <span class="n">ComponentExtension</span>

<span class="k">class</span><span class="w"> </span><span class="nc">HelloCommand</span><span class="p">(</span><span class="n">ComponentCommand</span><span class="p">):</span>
    <span class="n">name</span> <span class="o">=</span> <span class="s2">"hello"</span>
    <span class="n">help</span> <span class="o">=</span> <span class="s2">"Say hello"</span>
    <span class="k">def</span><span class="w"> </span><span class="nf">handle</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="o">*</span><span class="n">args</span><span class="p">,</span> <span class="o">**</span><span class="n">kwargs</span><span class="p">):</span>
        <span class="nb">print</span><span class="p">(</span><span class="s2">"Hello, world!"</span><span class="p">)</span>

<span class="k">class</span><span class="w"> </span><span class="nc">MyExt</span><span class="p">(</span><span class="n">ComponentExtension</span><span class="p">):</span>
    <span class="n">name</span> <span class="o">=</span> <span class="s2">"my_ext"</span>
    <span class="n">commands</span> <span class="o">=</span> <span class="p">[</span><span class="n">HelloCommand</span><span class="p">]</span>
</code></pre></div>
<p>You can run the <code>hello</code> command with:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>run<span class="w"> </span>my_ext<span class="w"> </span>hello
</code></pre></div>
<p>You can also define arguments for the command, which will be passed to the command's <code>handle</code> method.</p>
<div class="highlight"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">django_components</span><span class="w"> </span><span class="kn">import</span> <span class="n">CommandArg</span><span class="p">,</span> <span class="n">ComponentCommand</span><span class="p">,</span> <span class="n">ComponentExtension</span>

<span class="k">class</span><span class="w"> </span><span class="nc">HelloCommand</span><span class="p">(</span><span class="n">ComponentCommand</span><span class="p">):</span>
    <span class="n">name</span> <span class="o">=</span> <span class="s2">"hello"</span>
    <span class="n">help</span> <span class="o">=</span> <span class="s2">"Say hello"</span>
    <span class="n">arguments</span> <span class="o">=</span> <span class="p">[</span>
        <span class="n">CommandArg</span><span class="p">(</span><span class="n">name</span><span class="o">=</span><span class="s2">"name"</span><span class="p">,</span> <span class="n">help</span><span class="o">=</span><span class="s2">"The name to say hello to"</span><span class="p">),</span>
        <span class="n">CommandArg</span><span class="p">(</span><span class="n">name</span><span class="o">=</span><span class="p">[</span><span class="s2">"--shout"</span><span class="p">,</span> <span class="s2">"-s"</span><span class="p">],</span> <span class="n">action</span><span class="o">=</span><span class="s2">"store_true"</span><span class="p">),</span>
    <span class="p">]</span>

    <span class="k">def</span><span class="w"> </span><span class="nf">handle</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">name</span><span class="p">:</span> <span class="nb">str</span><span class="p">,</span> <span class="o">*</span><span class="n">args</span><span class="p">,</span> <span class="o">**</span><span class="n">kwargs</span><span class="p">):</span>
        <span class="n">shout</span> <span class="o">=</span> <span class="n">kwargs</span><span class="o">.</span><span class="n">get</span><span class="p">(</span><span class="s2">"shout"</span><span class="p">,</span> <span class="kc">False</span><span class="p">)</span>
        <span class="n">msg</span> <span class="o">=</span> <span class="sa">f</span><span class="s2">"Hello, </span><span class="si">{</span><span class="n">name</span><span class="si">}</span><span class="s2">!"</span>
        <span class="k">if</span> <span class="n">shout</span><span class="p">:</span>
            <span class="n">msg</span> <span class="o">=</span> <span class="n">msg</span><span class="o">.</span><span class="n">upper</span><span class="p">()</span>
        <span class="nb">print</span><span class="p">(</span><span class="n">msg</span><span class="p">)</span>
</code></pre></div>
<p>You can run the command with:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>ext<span class="w"> </span>run<span class="w"> </span>my_ext<span class="w"> </span>hello<span class="w"> </span>--name<span class="w"> </span>John<span class="w"> </span>--shout
</code></pre></div>
<div class="admonition note">
<p class="admonition-title">Note</p>
<p>Command arguments and options are based on Python's <code>argparse</code> module.</p>
<p>For more information, see the <a href="https://docs.python.org/3/library/argparse.html">argparse documentation</a>.</p>
</div>
</div>
</div>







<div class="doc doc-object doc-command" data-djc-id-cvvBJOu="">
<h2 id="components-list" class="doc doc-heading">
<span class="doc doc-object-name doc-command-name">components list</span>
<a class="headerlink" href="#components-list" title="Permanent link">¤</a>
</h2>
<div class="doc doc-contents">
                <div class="doc-signature highlight"><pre><code>usage: python manage.py components list [-h] [--all] [--columns COLUMNS] [-s]</code></pre></div>


<a class="doc-source-link" href="https://github.com/django-components/django-components/blob/master/src/django_components/commands/list.py#L91" target="_blank">See source code</a>


<p>List all components created in this project.</p>
<div class="doc-section doc-command-args"><p class="doc-section-title">Options</p><ul><li><code>-h</code>, <code>--help</code> &ndash; show this help message and exit</li><li><code>--all</code> &ndash; Show all columns. Same as `--columns name,full_name,path`.</li><li><code>--columns COLUMNS</code> &ndash; Comma-separated list of columns to show. Available columns: name, full_name, path. Defaults to `--columns full_name,path`.</li><li><code>-s</code>, <code>--simple</code> &ndash; Only show table data, without headers. Use this option for generating machine-readable output.</li></ul></div>
<p>List all components.</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>list
</code></pre></div>
<p>Prints the list of available components:</p>
<div class="highlight"><pre><span></span><code>full_name                                                     path
==================================================================================================
project.pages.project.ProjectPage                             ./project/pages/project
project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
</code></pre></div>
<p>To specify which columns to show, use the <code>--columns</code> flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>list<span class="w"> </span>--columns<span class="w"> </span>name,full_name,path
</code></pre></div>
<p>Which prints:</p>
<div class="highlight"><pre><span></span><code>name                      full_name                                                     path
==================================================================================================
ProjectPage               project.pages.project.ProjectPage                             ./project/pages/project
ProjectDashboard          project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
ProjectDashboardAction    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
</code></pre></div>
<p>To print out all columns, use the <code>--all</code> flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>list<span class="w"> </span>--all
</code></pre></div>
<p>If you need to omit the title in order to programmatically post-process the output,
you can use the <code>--simple</code> (or <code>-s</code>) flag:</p>
<div class="highlight"><pre><span></span><code>python<span class="w"> </span>manage.py<span class="w"> </span>components<span class="w"> </span>list<span class="w"> </span>--simple
</code></pre></div>
<p>Which prints just:</p>
<div class="highlight"><pre><span></span><code>ProjectPage               project.pages.project.ProjectPage                             ./project/pages/project
ProjectDashboard          project.components.dashboard.ProjectDashboard                 ./project/components/dashboard
ProjectDashboardAction    project.components.dashboard_action.ProjectDashboardAction    ./project/components/dashboard_action
</code></pre></div>
</div>
</div>


