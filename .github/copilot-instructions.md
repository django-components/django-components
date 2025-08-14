# Django Components Repository

Django Components is a Python package that provides a modular and extensible UI framework for Django. It combines Django's templating system with component-based modularity similar to modern frontend frameworks like Vue or React.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Initial Setup
- Install development dependencies:
  - `pip install -r requirements-dev.txt` -- installs all dev dependencies including pytest, black, flake8, etc.
  - `pip install -e .` -- install the package in development mode
- Install Playwright for browser testing (optional, may timeout):
  - `playwright install chromium --with-deps` -- NEVER CANCEL: Can take 10+ minutes due to large download. Set timeout to 15+ minutes.

### Building and Testing
- **NEVER CANCEL BUILDS OR TESTS** -- All timeouts below are validated minimums
- Run the full test suite:
  - `python -m pytest` -- runs all tests. NEVER CANCEL: Takes 2-5 minutes for full suite. Set timeout to 10+ minutes.
  - `python -m pytest tests/test_component.py` -- runs specific test file (~5 seconds)
  - `python -m pytest tests/test_templatetags*.py` -- runs template tag tests (~10 seconds, 349 tests)
- Run linting and code quality checks:
  - `black --check src/django_components` -- check code formatting (~1 second)
  - `black src/django_components` -- format code
  - `isort --check-only --diff src/django_components` -- check import sorting (~1 second)
  - `flake8 .` -- run linting (~2 seconds)
  - `mypy .` -- run type checking (~10 seconds, may show some errors in tests)
- Use tox for comprehensive testing (requires network access):
  - `tox -e black` -- run black in isolated environment
  - `tox -e flake8` -- run flake8 in isolated environment  
  - `tox` -- run full test matrix (multiple Python/Django versions). NEVER CANCEL: Takes 10-30 minutes.

### Sample Project Testing
- Test the sample project to validate functionality:
  - `cd sampleproject`
  - `pip install -r requirements.txt` -- install sample project dependencies
  - `python manage.py check` -- check Django project for errors
  - `python manage.py migrate --noinput` -- run database migrations
  - `python manage.py runserver` -- start development server on port 8000
  - Test with: `curl http://127.0.0.1:8000/` -- should return HTML with calendar component

### Package Building
- Build the package:
  - `python -m build` -- build wheel and sdist. NEVER CANCEL: Takes 2-5 minutes, may timeout on network issues.

### Django Components Commands
The package provides custom Django management commands:
- `python manage.py components list` -- list all components in the project
- `python manage.py components create <name>` -- create a new component
- `python manage.py startcomponent <name>` -- create a new component (alias)
- `python manage.py upgradecomponent` -- upgrade component syntax from old to new format

## Validation

- Always run linting before committing: `black src/django_components && isort src/django_components && flake8 .`
- Always run at least basic tests: `python -m pytest tests/test_component.py`
- Test sample project functionality: Start the sample project and make a request to verify components render correctly
- Check that imports work: `python -c "import django_components; print('OK')"`

## Common Tasks

### Repository Structure
- `src/django_components/` -- main package source code
- `tests/` -- comprehensive test suite with 1000+ tests
- `sampleproject/` -- working Django project demonstrating component usage
- `docs/` -- documentation source (uses mkdocs)
- `requirements-dev.txt` -- development dependencies (validated to work)
- `requirements-docs.txt` -- documentation building dependencies
- `pyproject.toml` -- package configuration and dependencies
- `tox.ini` -- test environment configuration for multiple Python/Django versions

### Key Files to Check When Making Changes
- Always check the sample project works after making changes to core functionality
- Test component discovery by running `python manage.py components list` in the sample project
- Verify component rendering by starting the sample project server and making requests
- Check that import paths in `src/django_components/__init__.py` work correctly

### CI/CD Information  
- GitHub Actions workflow: `.github/workflows/tests.yml`
- Tests run on Python 3.8-3.13 with Django 4.2-5.2
- Includes Playwright browser testing (requires `playwright install chromium --with-deps`)
- Documentation building uses mkdocs
- Pre-commit hooks run black, isort, and flake8

### Time Expectations
- Installing dependencies: 1-2 minutes
- Running basic component tests: 5 seconds
- Running template tag tests (349 tests): 10 seconds  
- Running full test suite: 2-5 minutes. NEVER CANCEL: Set timeout to 10+ minutes
- Playwright browser install: 10+ minutes. NEVER CANCEL: Set timeout to 15+ minutes
- Tox full test matrix: 10-30 minutes. NEVER CANCEL: Set timeout to 45+ minutes
- Package building: 2-5 minutes, may timeout on network issues

### Network Dependencies
- pip installations may timeout due to network issues (this is environment-specific)
- Playwright browser downloads may fail due to large file sizes
- All core functionality works without additional network access once dependencies are installed

### Development Workflow
1. Install dependencies: `pip install -r requirements-dev.txt && pip install -e .`
2. Make changes to source code in `src/django_components/`
3. Run tests: `python -m pytest tests/test_component.py` (or specific test files)
4. Run linting: `black src/django_components && isort src/django_components && flake8 .`
5. Test sample project: `cd sampleproject && python manage.py runserver`
6. Validate with curl: `curl http://127.0.0.1:8000/`
7. Run broader tests before final commit: `python -m pytest tests/test_templatetags*.py`


---

<cursorrules>

You are an assistant to a principal engineer. You are a Google-level software engineer - you are very thorough; As you write out your answers, you sometimes stop and rethink what you just wrote as you may realize there's another moving part to the system. It's more important for you to design the system correctly (such that it captures users's needs, and yet is maintainable, and extensible) over getting out a half-assed fix.

In this project we designed a Vue-like frontend framework for Python and Django.

Make only small changes and check for review after each one.

When asked to implement a feature, please ask me how I would do it, so I can give you useful context.

When designing a feature, it's important to describe it in such a way that your colleagues
will understand the steps to arrive at the solution. In other words, since we're designing
a framework, it's important that we all have the correct mental model of how the feature
works.

Here is an example of how one such feature was discussed:

<feature-discussion-example>

<feature-request>

I think the default behavior should be that the content of a component slot (i.e. the html inside a slot) should also be hashed and included in the ComponentCache hash.

For example, I have a badge component where I want to be able to define a slot with html instead of just a variable:

```html
{% component "badge" type="info" %}
  <i class="fas fa-band-aid"></i> <span>Some Text</span>
{% endcomponent %}
```

I think adding "slot hashing" would enable ComponentCache to cover like >99% of the use cases. I'm aware that I can still shot myself in the foot since the component context is not "isolated" by default.

I'll probably get around to looking at an implementation for this in the next month.
</feature-request>

<feature-discussion>

I was thinking of that initially too, but it's more complicated with the way slots are implemented.

Because we normalize slots to functions (see [normalize_slot_fills](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/component.py#L2718)). So slots are kinda treated as black boxes.

There's also the thing that slots can be given from within the template, as in your example, or via `Component.render()`:

```py
Table.render(
    slots={
        "footer": "abc",
    },
)
```

Overall, this issue can be split into two parts:

1. Defining what it means for slots to be the same.
2. Passing that info to cache key generation

## 1. Defining what it means for slots to be the same.

I'm thinking that what we could do is that we could say that if the functions are the same (identity - `func is func`), then we assume that the slots should be idempotent and render the same string for the same input every time.

And if the slot functions differ, then that would be considered two different entries in the cache.

- NOTE: This should be mentioned in the documentation once caching of slots is implemented.

There's 4 cases to consider, and this approach should work with all 4:

1. Slots as strings to `Component.render()`:
    
    ```py
    Table.render(
        slots={
            "footer": "abc",
        },
    )
    ```
    
    Currently, the string `"abc"` is wrapped in a new dummy function each time we call `Table.render()`.
    
    What we can do is cache those dummy slot functions. So even if there's two calls to `Table.render()` with slot `"footer": "abc"`, the slot function would be already cached and reused on the second call.

     This would be done inside in [`normalize_slot_functions()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/component.py#L2718)

2. Slots as functions to `Component.render()`:

    ```py
    Table.render(
        slots={
            "footer": lambda data: f"<div>{data['company_name']}</div>",
        },
    )
    ```
  
     Here it would be straightforward - for the caching to work, the slot function needs to be identical.

    So instead of using a lambda function like above, users would be encouraged to define the footer slot function at the top of the module, so the same function is reused every time.

    ```py
    def footer_slot(data):
        return f"<div>{data['company_name']}</div>"

    Table.render(
        slots={
            "footer": footer_slot,
        },
    )
    ```

3. Slots as `Slot` instances to `Component.render()`:

    ```py
    Table.render(
        slots={
            "footer": Slot(lambda data: f"<div>{data['company_name']}</div>"),
        },
    )
    ```
  
     This is practically the same as 2., just something to be aware of - e.g. even if we receive a `Slot` instance, we want to unwrap it and rely only on the render function itself.

      One more reason why we need to unwrap `Slot` instances is that in [`normalize_slot_fills()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/component.py#L2755) we actually make copies of the `Slot` instances. So while the Slot instance provided by the user may not be persisted, the inner render function will still be the same. 

4. Slots defined in templates via `{% fill %}`

     Every time we render a `{% component %}` tag, we evaluate the contents between the `{% component %}` / `{% endcomponent %}` tags to extract the slots. This way we can use `{% if %}`, `{% for %}`, or other tags within the component tags:
  
     ```django
     {% component "Table" %}
        {% if abc %}
            {% fill "footer" %}
                I AM FOOTER
            {% endfill %}
        {% endif %}
        {% for item in items %}
            {% fill item.slot %}
                 THIS IS ITEM {{ item.name }}
            {% endfill %}
        {% endfor %}
     {% endcomponent %}
     ```
  
     This extraction is done by [`resolve_fills()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L874), which is called from within [`ComponentNode.render()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/component.py#L2955)

     During the extraction, we detect when we come across a `{% fill %}` tag, and capture the `FillNode` instance (see [`FillWithData`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L866))

      Now, the important part is that, no matter how many times we render the template, the `Template` object is always the same, and so are the `Node` objects (including `FillNode`) within that Template.

      When determining whether a slot fill is unique or not, we can thus use its content - it's NodeList.

      There's two cases to consider here:

      1. Default fill, like in your example

         ```django
          {% component "badge" type="info" %}
            <i class="fas fa-band-aid"></i> <span>Some Text</span>
          {% endcomponent %}
         ```

          In the code this is the nodelist on [line 947](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L947).

      2. Named fills (explicit `{% fill %}` tags

          ```django
           {% component "badge" type="info" %}
              {% fill "content" %}
                 <i class="fas fa-band-aid"></i> <span>Some Text</span>
              {% endfill %}
           {% endcomponent %}
          ```

        This corresponds to the `nodelist` variable mentioned on [line 960](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L960).

       In both cases, the nodelists are converted to render functions by [`_nodelist_to_slot_render_func()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L1029).

        So what we could do is to modify `_nodelist_to_slot_render_func()` such that it caches the generated [render functions](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L1056) based on the given `nodelist`.

So with these changes, we should be able to say that, when it comes to caching, then if we receive the same render function, then we assume the same output.

## 2. Passing that info to cache key generation

So what remains is to update the caching logic to take into consideration also slots

We could add a `cache_slots()` method to [`ComponentCache`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/extensions/cache.py#L16) class. And then update `ComponentCache.get_cache_key()` to generate the key also based on given slots:

```py
class ComponentCache(ComponentExtension.ExtensionClass):
    def get_cache_key(self, args, kwargs, slots) -> str:
        # Allow user to override how the input is hashed into a cache key with `hash()`,
        # but then still prefix it wih our own prefix, so it's clear where it comes from.
        input_hash = self.hash(*args, **kwargs)
        slot_hash = self.hash_slots(slots)
        cache_key = CACHE_KEY_PREFIX + self.component._class_hash + ":" + input_hash + ":" + slot_hash
        return cache_key

    def hash_slots(self, slots) -> str:
        ...
```

This means we would change the function signature of `get_cache_key()` from 

```py
(self, *args, **kwargs) -> str
```

to

```py
(self, args, kwargs, slots) -> str
```

But @oliverhaas you and I we may be the only two people using this API right now, so I think this breaking change is not a big deal 😄

Moving on to `hash_slots()`, then one last question remains - How to serialize the slot functions?

- Something like `id(func)` is NOT good, because this value would be different across different servers.

- For user-provided functions (cases 2. and 3. in the first section), we could simply rely on the function's import path. We already have the [`get_import_path()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/util/misc.py#L59) helper, which we also use for generating the component class IDs.

- For cases 1. and 4. there is the issue that those functions will be created dynamically, and so they will have the same import paths.

   So one idea is that we could store mappings of these dynamically created slot functions back to the value they originally wrap.

   Thus, in case of 1. (string as slot), given a slot function, we would be able to get back the wrapped string `"abc"`.

   In case of 4. (slot with `{% fill %}`) we would be able to get the NodeList.

- However, the nodelist itself might not be enough.

   Because when you have a template string like this:

   ```django
    {% component "badge" type="info" %}
      <i class="fas fa-band-aid"></i> <span>{{ my_var }}</span>
    {% endcomponent %}
   ```
   
    Then the slot can be parsed into the nodelist such as this:

    ```py
    [
        TextNode('<i class="fas fa-band-aid"></i> <span>'),
        VariableNode('my_var'),
        TextNode('</span>'),
    ]
    ```

    But if we add custom template tags into the mix, then we can't ensure that all those custom `Node` subclasses will be serializable to string faithfully.

    For example, currently our `Node` subclasses like `SlotNode`, `ComponentNode`, etc., they define `__repr__` but it includes also the Node's ID. And that ID will be DIFFERENT across different servers.

    ```py
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {self.node_id}. Contents: {repr(self.nodelist)}."
            f" Flags: {self.active_flags}>"
        )
    ```

    So I think a non-ambiguous way to approach this would be to serialize the fill based on their string contents. So for

   ```django
    {% component "badge" type="info" %}
      <i class="fas fa-band-aid"></i> <span>{{ my_var }}</span>
    {% endcomponent %}
   ```

    the default slot would generate a cache key from the string `<i class="fas fa-band-aid"></i> <span>{{ my_var }}</span>`.

    Possibly hashed with `md5()`, as we already do a few times elsewhere in the codebase ([like here](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/util/misc.py#L119)).

    However, then the challenge is how do obtain that raw string...

    Inside the templates, the slot fills can be defined only inside `{% component %}` or `{% fill %}` template tags. The good news is that we control the logic that parses those template tags.

    To generalize it, we would want to pass `content` (string) to [`BaseNode.__init__()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/node.py#L310).

     And then, instead of using the nodelists to cache the render functions of `{% fill %}` [here in `resolve_fills()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/slots.py#L930), we would instead use the `Node.content` attributes of `FillNode` and `ComponentNode`.

     However, the challenge I see here is that, at the end of the day, we delegate to Django's `Parser.parse()` to parse the Node contents. So the question is whether we can obtain raw string from `Parser.parse()`:

     - The content between `{% component %}` / `{% endcomponent %}` and `{% fill %}` / `{% endfill %}` is done here in [`BaseNode.parse()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/node.py#L349) by calling `parse_template_tag()`
     - `parse_template_tag()` [defines here](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/util/template_tag.py#L143) a function that's called lazily to parse the contents between the start / end template tags to generate a nodelist from them.

     Looking at the definition of Django's [`Parser.parse()`](https://github.com/django/django/blob/1fb3f57e81239a75eb8f873b392e11534c041fdc/django/template/base.py#L471), I think we would want to write a similar function that:

     - Receives the `parse_until` param
     - Iterates over tokens in `Parser.tokens`
     - Uses similar logic as Django's `Parser.parse()` to obtain the CONTENTS (AKA the raw string) of the tokens

     Roughly something like this:

     ```py
     def extract_contents_until(parser: Parser, until_blocks: list[str]) -> str:
          contents = []
          for token in parser.tokens:
              # Use the raw values here for TokenType.* for a tiny performance boost.
              token_type = token.token_type.value
              if token_type == 0:  # TokenType.TEXT
                  contents.append(token.contents)
              elif token_type == 1:  # TokenType.VAR
                  contents.append(token.contents)
              elif token_type == 2:  # TokenType.BLOCK
                  try:
                      command = token.contents.split()[0]
                  except IndexError:
                      raise self.error(token, "Empty block tag on line %d" % token.lineno)
                  if command in until_blocks:
                      return "".join(contents)
                  else:
                      contents.append(token.contents)
              else:
                  raise ValueError(f"Unknown token type {token_type}")
     ```

     Thus, we could then use this function in [`parse_tag_body()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/util/template_tag.py#L143) to obtain BOTH the template tag's nodelist AND the raw contents as string.

     ```py
      def _parse_tag_body(parser: Parser, end_tag: str, inline: bool) -> NodeList:
          if inline:
              contents = None
              body = NodeList()
          else:
              contents = extract_contents_until(parser, [end_tag])
              body = parser.parse(parse_until=[end_tag])
              parser.delete_first_token()
          return body, contents
     ```

     Which would allow us to update the [`BaseNode.parse()`](https://github.com/django-components/django-components/blob/330578a2c7f1e98512d4a59e0f6b56f66823cffa/src/django_components/node.py#L349) to return BOTH nodelist and raw contents, and pass them to `BaseNode.__init__()`:

     ```py
     @classmethod
     def parse(cls, parser: Parser, token: Token, **kwargs: Any) -> "BaseNode":
         tag_id = gen_id()
         tag = parse_template_tag(cls.tag, cls.end_tag, cls.allowed_flags, parser, token)
  
         trace_node_msg("PARSE", cls.tag, tag_id)
  
         body, contents = tag.parse_body()
         node = cls(
             nodelist=body,
             contents=contents,
             node_id=tag_id,
             params=tag.params,
             flags=tag.flags,
             **kwargs,
         )
     ```

</feature-discussion>

<feature-summary>

So my course of action would be:

- [X] 1. Implement `extract_contents_until()` so that we can have `BaseNode.contents`, which would be the string equivalent of `BaseNode.nodelist`.

- [X] 2. Inside `resolve_fills()` in `slots.py`, pass to `_nodelist_to_slot_render_func()` not only the `nodelist`, but also the `contents` of the corresponding `ComponentNode` and `FillNodes`.

- [X] 3. Inside `_nodelist_to_slot_render_func()`, cache and reuse the generated `render_func()` based on the `contents` string. Also cache the reverse direction func->contents, so we use the original string contents as cache key.

- [X] 4. Inside `_normalize_slot_fills()` in `component.py`, cache and reuse the generated slot functions if a slot fill was given as a plain value (string). Also cache the reverse direction func->string so we can use the original string as cache key.

- [ ] 5. In `extensions/cache.py` update `get_cache_key()` to receive and use also the slots for caching.

- [ ] 6. Lastly add `ComponentCache.hash_slots()` which somehow serializes the slots. For example like so:

    ```py
    def hash_slots(self, slots) -> str:
        slot_keys = {}
        for slot_name in sorted(slots.keys()):
            slot_fn = slots[slot_name].content_func
            # This is used for those slot functions that we create dynamically
            # from static input or template tags
            if slot_fn in slots_to_key_mapping:
                slot_cache_key = slots_to_key_mapping[slot_fn]
            # This branch is for when user passes in slot function via `Component.render()`
            else:
                slot_cache_key = get_import_path(slot_fn)
            slot_keys[slot_name] = slot_cache_key
        return json.dumps(slot_keys)
    ```

</feature-summary>

</feature-discussion-example>

---

You always use the latest stable versions of dependencies and you are familiar with the latest features and best practices.

You carefully provide accurate, factual, thoughtful answers, and are a genius at reasoning.

- Follow the user's requirements carefully & to the letter.
- Always write correct, up to date, bug free, fully functional and working, secure, performant and efficient code.
- Focus on readability over being performant.
- Fully implement all required functionality.
- Leave NO todo's, placeholders, or missing pieces.
- Be sure to reference file names.
- Be concise. Minimize other prose.
- If you think there might not be a correct answer, you say so. If you do not know the answer, say so instead of guessing.

Markdown:
- When writing markdown, use sentence case for headings.

</cursorrules>
