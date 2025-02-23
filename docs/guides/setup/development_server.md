### Reload dev server on component file changes

This is relevant if you are using the project structure as shown in our examples, where
HTML, JS, CSS and Python are in separate files and nested in a directory.

In this case you may notice that when you are running a development server,
the server sometimes does not reload when you change component files.

From relevant [StackOverflow thread](https://stackoverflow.com/a/76722393/9788634):

> TL;DR is that the server won't reload if it thinks the changed file is in a templates directory,
> or in a nested sub directory of a templates directory. This is by design.

To make the dev server reload on all component files, set
[`reload_on_file_change`](#reload_on_file_change---reload-dev-server-on-component-file-changes)
to `True`.
This configures Django to watch for component files too.

!!! note

    This setting should be enabled only for the dev environment!
