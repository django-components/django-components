## Local installation

Start by forking the project by clicking the **Fork button** up in the right corner in the [GitHub](https://github.com/django-components/django-components).
This makes a copy of the repository in your own name. Now you can clone this repository locally and start adding features:

```sh
git clone https://github.com/<your GitHub username>/django-components.git
cd django-components
```

To quickly run the tests install the local dependencies by running:

```sh
pip install -r requirements-dev.txt
```

You also have to install this local django-components version. Use `-e` for [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html) so you don't have to re-install after every change:

```sh
pip install -e .
```

## Running tests

Now you can run the tests to make sure everything works as expected:

```sh
pytest
```

The library is also tested across many versions of Python and Django. To run tests that way:

```sh
pyenv install -s 3.8
pyenv install -s 3.9
pyenv install -s 3.10
pyenv install -s 3.11
pyenv install -s 3.12
pyenv install -s 3.13
pyenv install -s 3.14
pyenv local 3.8 3.9 3.10 3.11 3.12 3.13 3.14
tox -p
```

To run tests for a specific Python version, use:

```sh
tox -e py38
```

NOTE: See the available environments in `tox.ini`.

## Linting and formatting

To check linting rules, run:

```sh
ruff check .
# Or to fix errors automatically:
ruff check --fix .
```

To format the code, run:

```sh
ruff format --check .
# Or to fix errors automatically:
ruff format .
```

To validate with Mypy, run:

```sh
mypy .
```

You can run these through `tox` as well:

```sh
tox -e mypy,ruff
```

## Playwright tests

We use [Playwright](https://playwright.dev/python/docs/intro) for end-to-end tests. You will need to install Playwright to run these tests.

Luckily, Playwright makes it very easy:

```sh
pip install -r requirements-dev.txt
playwright install chromium --with-deps
```

After Playwright is ready, run the tests the same way as before:

```sh
pytest
# Or for specific Python version
tox -e py38
```

## Snapshot tests

Some tests rely on snapshot testing with [syrupy](https://github.com/syrupy-project/syrupy) to test the HTML output of the components.

If you need to update the snapshot tests, add `--snapshot-update` to the pytest command:

```sh
pytest --snapshot-update
```

Or with tox:

```sh
tox -e py39 -- --snapshot-update
```

## Dev server

How do you check that your changes to django-components project will work in an actual Django project?

Use the [sampleproject](https://github.com/django-components/django-components/tree/master/sampleproject/) demo project to validate the changes:

1. Navigate to [sampleproject](https://github.com/django-components/django-components/tree/master/sampleproject/) directory:

    ```sh
    cd sampleproject
    ```

2. Install dependencies from the [requirements.txt](https://github.com/django-components/django-components/blob/master/sampleproject/requirements.txt) file:

    ```sh
    pip install -r requirements.txt
    ```

3. Link to your local version of django-components:

    ```sh
    pip install -e ..
    ```

    !!! note

        The path to the local version (in this case `..`) must point to the directory that has the `pyproject.toml` file.

4. Start Django server:

    ```sh
    python manage.py runserver
    ```

Once the server is up, it should be available at <http://127.0.0.1:8000>.

To display individual components, add them to the `urls.py`, like in the case of <http://127.0.0.1:8000/greeting>

## Building JS code

django_components uses a bit of JS code to:

- Manage the loading of JS and CSS files used by the components
- Allow to pass data from Python to JS

When you make changes to this JS code, you also need to compile it:

1. Navigate to `src/django_components_js`:

    ```sh
    cd src/django_components_js
    ```

2. Install the JS dependencies

    ```sh
    npm install
    ```

3. Compile the JS/TS code:

    ```sh
    python build.py
    ```

    The script will combine all JS/TS code into a single `.js` file, minify it,
    and copy it to `django_components/static/django_components/django_components.min.js`.

## Documentation website

The documentation website is built using [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

First install dependencies needed for the documentation:

```sh
pip install -r requirements-docs.txt
```

Then install this local django-components version. Use `-e` for [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html) so you don't have to re-install after every change:

```sh
pip install -e .
```

To run the documentation server locally, run:

```sh
mkdocs serve
```

Then open <http://127.0.0.1:9000/django-components/> in your browser.

To just build the documentation, run:

```sh
mkdocs build
```

The documentation site is deployed automatically with Github actions (see [`.github/workflows/docs.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/docs.yml)).

The CI workflow runs when:

- A new commit is pushed to the `master` branch - This updates the `dev` version
- A new tag is pushed - This updates the `latest` version and the version specified in the tag name

### Examples

The [examples page](../../examples) is populated from entries in `docs/examples/`. 

These examples have special folder layout:
 
```txt
|- docs/
  |- examples/
    |- <example_name>/
      |- component.py - The component definition
      |- page.py      - The page view for the example
      |- test_example_<example_name>.py - Tests
      |- README.md    - Component documentation
      |- images/      - Images used in README
```

This allows us to keep the examples in one place, and define, test, and document them.

**Previews** - There's a script in `sampleproject/examples/utils.py` that picks up the `component.py` and `page.py` files, making them previewable in the dev server (`http://localhost:8000/examples/<example_name>`).

To see all available examples, go to `http://localhost:8000/examples/`.

The examples index page displays a short description for each example. These values are taken from a top-level `DESCRIPTION` string variable in the example's `component.py` file.

**Tests** - Use the file format `test_example_<example_name>.py` to define tests for the example. These tests are picked up when you run pytest.

#### Adding examples

Let's say we want to add an example called `form`:

1. Create a new directory in `docs/examples/form/`
2. Add actual implementation in `component.py`
3. Add a live demo page in `page.py`
4. Add tests in `test_example_form.py`
5. Write up the documentation in `README.md`
6. Link to that new page from `docs/examples/index.md`.
7. Update `docs/examples/.nav.yml` to update the navigation.

### People page

The [people page](https://django-components.github.io/django-components/dev/community/people/) is regularly updated with stats about the contributors and authors. This is triggered automatically once a month or manually via the Actions tab.

See [`.github/workflows/maint-docs-people.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/maint-docs-people.yml) for more details.

## Publishing

We use Github actions to automatically publish new versions of django-components to PyPI when a new tag is pushed. [See the full workflow here](https://github.com/django-components/django-components/blob/master/.github/workflows/publish-to-pypi.yml).

### Commands

We do not manually release new versions of django-components. Commands below are shown for reference only.

To package django-components into a distribution that can be published to PyPI, run `build`:

```sh
# Install pypa/build
python -m pip install build --user
# Build a binary wheel and a source tarball
python -m build --sdist --wheel --outdir dist/ .
```

To then publish the contents of `dist/` to PyPI, use `twine` ([See Python user guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives)):

```sh
twine upload --repository pypi dist/* -u __token__ -p <PyPI_TOKEN>
```

### Release new version

Let's say we want to release a new version `0.141.6`. We need to:

1.  Bump the `version` in `pyproject.toml` to the desired version.

    ```toml
    [project]
    version = "0.141.6"
    ```

2.  Create a summary of the changes in `CHANGELOG.md` at the top of the file.

    When writing release notes for individual changes, it's useful to write them like mini announcements:

    - Explain the context
    - Then the change itself
    - Then include an example

    ```md
    # Release notes

    ## v0.141.6

    _2025-09-24_

    #### Fix

    - Tests - Fix bug when using `@djc_test` decorator and the `COMPONENTS`
      settings are set with `ComponentsSettings`
      See [#1369](https://github.com/django-components/django-components/issues/1369)
    ```

    !!! note

        When you include the release date in the format `_YYYY-MM-DD_`, it will be displayed in the release notes.

        See [`docs/scripts/gen_release_notes.py`](https://github.com/django-components/django-components/blob/master/docs/scripts/gen_release_notes.py) for more details.

        ![Example of a changelog entry](../images/release-notes-dates.png){ width="250" }

3.  Create a new PR to merge the changes above into the `master` branch.

4.  Create new release in [Github UI](https://github.com/django-components/django-components/releases/new).

    ![Github UI release part 1](../images/release-github-ui-1.png)
    ![Github UI release part 2](../images/release-github-ui-2.png)
    ![Github UI release part 3](../images/release-github-ui-3.png)
    ![Github UI release part 4](../images/release-github-ui-4.png)

### Semantic versioning

We use [Semantic Versioning](https://semver.org/) for django-components.

The version number is in the format `MAJOR.MINOR.PATCH` (e.g. `0.141.6`).

- `MAJOR` (e.g. `1.0.0`) is reserved for significant architectural changes and breaking changes.
- `MINOR` (e.g. `0.1.0`) is incremented for new features.
- `PATCH` (e.g. `0.0.1`) is incremented for bug fixes or documentation changes.

## Development guides

Head over to [Dev guides](./devguides/dependency_mgmt.md) for a deep dive into how django_components' features are implemented.

## Maintenance

### Updating supported versions

The `scripts/supported_versions.py` script manages the supported Python and Django versions for the project.

The script runs automatically via GitHub Actions once a week to check for version updates. If changes are detected, it creates a GitHub issue with the necessary updates. See the [`maint-supported-versions.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/maint-supported-versions.yml) workflow.

You can also run the script manually:

```sh
# Check if versions need updating
python scripts/supported_versions.py check

# Generate configuration snippets for manual updates
python scripts/supported_versions.py generate
```

The `generate` command will print to the terminal all the places that need updating and what to set them to.

### Updating link references

The `scripts/validate_links.py` script can be used to update the link references.

```sh
python scripts/validate_links.py
```

When new version of Django is released, you can use the script to update the URLs pointing to the Django documentation.

First, you need to update the `URL_REWRITE_MAP` in the script to point to the new version of Django.

Then, you can run the script to update the URLs in the codebase.

```sh
python scripts/validate_links.py --rewrite
```

## Integrations

### Discord

We integrate with our [Discord server](https://discord.gg/NaQ8QPyHtD) to notify about new releases, issues, PRs, and discussions.

See:
- [`issue-discord.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/issue-discord.yml)
- [`release-discord.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/release-discord.yml)
- [`pr-discord.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/pr-discord.yml)
- [`discussion-discord.yml`](https://github.com/django-components/django-components/blob/master/.github/workflows/discussion-discord.yml)

See [this tutorial](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) on how to set up the Discord webhooks.

The Discord webhook URLs are stored as secrets in the GitHub repository.

- `DISCORD_WEBHOOK_DEVELOPMENT` - For new issues
- `DISCORD_WEBHOOK_ANNOUNCEMENTS` - For new releases

## Project management

### Project board

We use the [GitHub project board](https://github.com/orgs/django-components/projects/1/views/1) to manage the project.

Quick overview of the columns:

- _No status_ - Issues that are not planned yet and need more discussion
- 🔵 **Backlog** - Planned but not ready to be picked up
- 🟢 **Ready** - Ready to be picked up
- 🟡 **In Progress** - Someone is already working on it
- 🟣 **Ready for release** - Completed, but not released yet
- 🟠 **Done** - Completed and released

New issues are automatically added to the _No status_ column.

To pick up an issue, assign it to yourself and move it to the 🟡 **In Progress** column.

![Project board](../images/project-board.png)

Use the sidebar to filter the issues by different labels, milestones, and issue types:

![Project board filter](../images/project-board-label-filter.png){ width="250" }

### Priority

Which issues should be picked up first?

We suggest the following guideline:

1. Bugs - First fix [bugs](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--bug) and documentation errors.
2. V1 release - Then pick up issues that are part of the [v1 release milestone](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=milestone--v1).

After that, pick what you like!

### Labels

Labels help keep our project organized. [See the list of all labels here](https://github.com/django-components/django-components/labels).

#### Milestones

- [`milestone--v1`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=milestone--v1) - Work to be done for the V1 release.

#### Issue types

- [`type--bug`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--bug) - Bugs.
- [`type--documentation`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--documentation) - Documentation changes.
- [`type--enhancement`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--enhancement) - New features and improvements.
- [`type--integration`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--integration) - Integrating with other libraries or systems.
- [`type--operations`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--operations) - Relating to "operations" - Github Actions, processes, etc.
- [`type--optimisation`](https://github.com/orgs/django-components/projects/1/views/1?sliceBy%5Bvalue%5D=type--optimisation) - Optimizing the code for performance.
