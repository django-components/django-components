# Benchmarks

## Overview

[`asv`](https://github.com/airspeed-velocity/) (Airspeed Velocity) is used for benchmarking performance.

`asv` covers the entire benchmarking workflow. We can:

1. Define benchmark tests similarly to writing pytest tests (supports both timing and memory benchmarks)
2. Run the benchmarks and generate results for individual git commits, tags, or entire branches
3. View results as an HTML report (dashboard with charts)
4. Compare performance between two commits / tags / branches for CI integration

![asv dashboard](./assets/asv_dashboard.png)

django-components uses `asv` for these use cases:

- Benchmarking across releases:

  1.  When a git tag is created and pushed, this triggers a Github Action workflow (see `docs.yml`).
  2.  The workflow runs the benchmarks with the latest release, and commits the results to the repository.
      Thus, we can see how performance changes across releases.

- Displaying performance results on the website:

  1.  When a git tag is created and pushed, we also update the documentation website (see `docs.yml`).
  2.  Before we publish the docs website, we generate the HTML report for the benchmark results.
  3.  The generated report is placed in the `docs/benchmarks/` directory, and is thus
      published with the rest of the docs website and available under [`/benchmarks/`](https://django-components.github.io/django-components/benchmarks).
      - NOTE: The location where the report is placed is defined in `asv.conf.json`.

- Compare performance between commits on pull requests:
  1. When a pull request is made, this triggers a Github Action workflow (see `benchmark.yml`).
  2. The workflow compares performance between commits.
  3. The report is added to the PR as a comment made by a bot.

## Interpreting benchmarks

The results CANNOT be taken as ABSOLUTE values e.g.:

"This example took 200ms to render, so my page will also take 200ms to render."

Each UI may consist of different number of Django templates, template tags, and components, and all these may influence the rendering time differently.

Instead, the results MUST be understood as RELATIVE values.

- If a commit is 10% slower than the master branch, that's valid.
- If Django components are 10% slower than vanilla Django templates, that's valid.
- If "isolated" mode is 10% slower than "django" mode, that's valid.

## Development

Let's say we want to generate results for the last 5 commits.

1. Install `asv`

   ```bash
   pip install asv
   ```

2. Run benchmarks and generate results

   ```bash
   asv run HEAD --steps 5 -e
   ```

   - `HEAD` means that we want to run benchmarks against the [current branch](https://stackoverflow.com/a/2304106/9788634).
   - `--steps 5` means that we want to run benchmarks for the last 5 commits.
   - `-e` to print out any errors.

   The results will be stored in `.asv/results/`, as configured in `asv.conf.json`.

3. Generate HTML report

   ```bash
   asv publish
   asv preview
   ```

   - `publish` generates the HTML report and stores it in `docs/benchmarks/`, as configured in `asv.conf.json`.
   - `preview` starts a local server and opens the report in the browser.

   NOTE: Since the results are stored in `docs/benchmarks/`, you can also view the results
   with `mkdocs serve` and navigating to `http://localhost:9000/django-components/benchmarks/`.

   NOTE 2: Running `publish` will overwrite the existing contents of `docs/benchmarks/`.

## Writing benchmarks

`asv` supports writing different [types of benchmarks](https://asv.readthedocs.io/en/latest/writing_benchmarks.html#benchmark-types). What's relevant for us is:

- [Raw timing benchmarks](https://asv.readthedocs.io/en/latest/writing_benchmarks.html#raw-timing-benchmarks)
- [Peak memory benchmarks](https://asv.readthedocs.io/en/latest/writing_benchmarks.html#peak-memory)

Notes:

- The difference between "raw timing" and "timing" tests is that "raw timing" is ran in a separate process.
  And instead of running the logic within the test function itself, we return a script (string)
  that will be executed in the separate process.

- The difference between "peak memory" and "memory" tests is that "memory" calculates the memory
  of the object returned from the test function. On the other hand, "peak memory" detects the
  peak memory usage during the execution of the test function (including the setup function).

You can write the test file anywhere in the `benchmarks/` directory, `asv` will automatically find it.

Inside the file, write a test function. Depending on the type of the benchmark,
prefix the test function name with `timeraw_` or `peakmem_`. See [`benchmarks/benchmark_templating.py`](benchmark_templating.py) for examples.

### Ensuring that the benchmarked logic is correct

The approach I (Juro) took with benchmarking the overall template rendering is that
I've defined the actual logic in `tests/test_benchmark_*.py` files. So those files
are part of the normal pytest testing, and even contain a section with pytest tests.

This ensures that the benchmarked logic remains functional and error-free.

However, there's some caveats:

1. I wasn't able to import files from `tests/`.
2. When running benchmarks, we don't want to run the pytest tests.

To work around that, the approach I used for loading the files from the `tests/` directory is to:

1. Get the file's source code as a string.
2. Cut out unwanted sections (like the pytest tests).
3. Append the benchmark-specific code to the file (e.g. to actually render the templates).
4. In case of "timeraw" benchmarks, we can simply return the remaining code as a string
   to be run in a separate process.
5. In case of "peakmem" benchmarks, we need to access this modified source code as Python objects.
   So the code is made available as a "virtual" module, which makes it possible to import Python objects like so:
   ```py
   from my_virtual_module import run_my_benchmark
   ```

## Using `asv`

### Compare latest commit against master

Note: Before comparing, you must run the benchmarks first to generate the results. The `continuous` command does not generate the results by itself.

```bash
asv continuous master^! HEAD^! --factor 1.1
```

- Factor of `1.1` means that the new commit is allowed to be 10% slower/faster than the master commit.

- `^` means that we mean the COMMIT of the branch, not the BRANCH itself.

  Without it, we would run benchmarks for the whole branch history.

  With it, we run benchmarks FROM the latest commit (incl) TO ...

- `!` means that we want to select range spanning a single commit.

  Without it, we would run benchmarks for all commits FROM the latest commit
  TO the start of the branch history.

  With it, we run benchmarks ONLY FOR the latest commit.

### More Examples

Notes:

- Use `~1` to select the second-latest commit, `~2` for the third-latest, etc..

Generate benchmarks for the latest commit in `master` branch.

```bash
asv run master^!
```

Generate benchmarks for second-latest commit in `master` branch.

```bash
asv run master~1^!
```

Generate benchmarks for all commits in `master` branch.

```bash
asv run master
```

Generate benchmarks for all commits in `master` branch, but exclude the latest commit.

```bash
asv run master~1
```

Generate benchmarks for the LAST 5 commits in `master` branch, but exclude the latest commit.

```bash
asv run master~1 --steps 5
```
