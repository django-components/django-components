# Django components JS

## Overview

The `manager.ts` file provides the core JavaScript dependency manager for django-components. It handles:

- Component registration and initialization
- Loading and tracking of JS/CSS dependencies
- Passing data from Python to JavaScript components

## `$onComponent()` transformation

In django-components, when you write `$onComponent()` in your component's JavaScript code, it is automatically transformed behind the scenes to:

```js
DjangoComponents.manager.registerComponent(
  class_id,
  // Your $onComponent() callback here
  (data, ctx) => {},
);
```

This means that `$onComponent()` is syntactic sugar that simplifies component registration. The transformation happens during the component rendering process on the server side.

## Usage

### Registering component callbacks

You can register one or more callback functions for a component. Multiple callbacks can be registered for the same component, and they will be called in sequence when the component is initialized.

This is useful for extensions that need to add behavior
without interfering with user-defined callbacks.

```js
// Register a function that is run at component initialization
DjangoComponents.manager.registerComponent(
  "table", // Component class ID (e.g., "TableComponent_a91d03")
  async (data, { id, name, els }) => {
    // First callback
    console.log(`Component ${name} initialized with ID ${id}`);
  },
);

// Register another callback for the same component
DjangoComponents.manager.registerComponent(
  "table",
  async (data, { id, name, els }) => {
    // Second callback - will be called after the first
  },
);
```

**Component context (`ctx`):**

- `id` - `string`: The unique instance ID of the component (e.g., `"c1a2b3c"`)
- `name` - `string`: The component class ID (e.g., `"TableComponent_a91d03"`)
- `els` - `HTMLElement[]`: Array of DOM elements with the `data-djc-id-{id}` attribute

**Data parameter (`data`):**

- Contains the data passed from Python's `get_js_data()` method
- Empty object `{}` if no JS variables are provided

### Registering component data

Component data is passed from Python to JavaScript as JSON.

This JSON is then wrapped in a factory function.
This way, if the same data is used for multiple components,
the data is not shared between them.

```js
DjangoComponents.manager.registerComponentData(
  "table", // Component class ID
  "3d09cf", // JS variables hash (used to identify the data set)
  () => {
    return JSON.parse('{ "abc": 123 }');
  },
);
```

### Calling components

Once components and data factories are registered, you can call component instances to trigger the `$onComponent()` callbacks:

```js
DjangoComponents.manager.callComponent(
  "table", // Component class ID
  "c123456", // Component instance ID
  "3d09cf", // JS variables hash (or `null` if no JS variables)
);
```

**Note:** `callComponent` will:

1. Call all registered callbacks for the component in registration order
2. Pass the same `data` and `ctx` to each callback
3. Return the result from the last callback
4. Throw an error if the component is not registered or if JS variables are missing

### Component call queue system

When a Python component defines a `Component.js` or `Component.js_file`, it can define a `$onComponent()` callback within the JS code. This JS callback is to be called when the component is instantiated in the DOM.

However, the `Component.js` script may also need to wait for other JS/CSS scripts or dependencies to be loaded. For example:

- Third-party scripts set in `Component.Media.js`
- JS variables from `Component.get_js_data()` that arrive in separate script tags (especially for fragments)

As a result, the most ergonomic way to call the components' callbacks is to enqueue them and monitor what conditions are met before we can call the component.

**Order preservation:** We ensure that component callbacks are called in the order they were enqueued. This is important because component callbacks may depend on each other. When a next-in-line component call is blocked, we stop and do not proceed until it is resolved.

### Loading scripts

Use the `loadJs()` and `loadCss()` methods to load JS and CSS into the DOM. They will insert `<script>` / `<style>` / `<link>` tags into the DOM.

This means that the JS/CSS files will be executed.

These methods return a promise that resolves when the JS/CSS is loaded.

JS/CSS that has been already loaded or "marked as loaded" will not be loaded again.

The `markScriptLoaded()` method is used to mark a JS/CSS as already loaded,
so it won't be loaded again.

The `waitForScriptsToLoad()` method is used to wait for specific JS/CSS (identified by their URL) to be loaded.

```js
// Load a JS script
const { el, promise } = DjangoComponents.manager.loadJs({
  tag: "script",
  attrs: { src: "/abc/def.js" },
  content: "",
});
// This resolves on `<script>`'s `onload` event
await promise;

// Load a CSS file
const { el, promise } = DjangoComponents.manager.loadCss({
  tag: "link",
  attrs: { href: "/abc/def.css", rel: "stylesheet" },
  content: "",
});
// This resolves immediately
await promise;

// Mark a JS/CSS as already loaded, so it won't be loaded again
DjangoComponents.manager.markScriptLoaded("js", "/abc/def.js");
DjangoComponents.manager.markScriptLoaded("css", "/abc/def.css");

// Check if a JS/CSS is already loaded
const isLoaded = DjangoComponents.manager.isScriptLoaded("js", "/abc/def.js");

// Wait for scripts to be loaded
// (doesn't load them, just waits)
await DjangoComponents.manager.waitForScriptsToLoad("js", [
  "/script1.js",
  "/script2.js",
]);
```

<!-- TODO_v1: Delete this section in v1 -->

!!! note "Backwards compatibility"

    The dependency manager was renamed from `Components` to `DjangoComponents` in v0.146.0. See https://github.com/django-components/django-components/issues/1544.

    For backwards compatibility, `Components` will remain available as an alias to `DjangoComponents` until v1.0.

## Build

1. Make sure you are inside `django_components_js`:

```sh
cd src/django_components_js
```

2. Make sure that JS dependencies are installed

```sh
npm install
```

3. Compile the JS/TS code:

```sh
python build.py
```

This will copy it to `django_components/static/django_components/django_components.min.js`.
