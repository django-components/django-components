# Django componnets JS

## Usage

```js
// Register a function that is run at component initialization
DjangoComponents.manager.registerComponent(
  "table",  // Component name
  async (data, { id, name, els }) => {
    ...
  },
);

// Register data factory function that may be used by multiple
// components.
DjangoComponents.registerComponentData(
  "table",  // Component name
  "3d09cf", // Input ID
  () => {
    return JSON.parse('{ "abc": 123 }');
  },
);

// Once the component and data factories are registered,
// we can run component's init function
DjangoComponents.callComponent(
  "table",  // Component name
  "c123456",    // Component ID - An HTML element with corresponding
            //                attribute (`data-djc-id-c123456`) MUST
            //                be present in the DOM.
  "3d09cf", // Input ID
);

// Load JS or CSS script if not laoded already
DjangoComponents.loadJs('<script src="/abc/def">');

// Or mark one as already-loaded, so it is ignored when
// we call `loadJs`
DjangoComponents.markScriptLoaded("js", '/abc/def');
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
