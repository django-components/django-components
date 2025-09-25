# Adding examples

Rule of thumb:

If the example is a 3rd party package or it lives under a different URL, only link to it in `overview.md`.

If the example is file(s) that we wrote:

1. Define the component in `sampleproject/examples/components/<component_name>/<component_name>.py`.
2. Define a view / page component in `sampleproject/examples/pages/<component_name>/<component_name>.py`.
3. Add a new page here in the documentation named `<component_name>.md`, similarly to [Tabs](./alpine/tabs.md).
4. Link to that new page from `index.md`.
5. Update `.nav.yml` if needed.
6. Add a corresponding test file in `tests/test_example_<component_name>.py`.
