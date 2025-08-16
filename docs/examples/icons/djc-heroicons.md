```sh
pip install djc-heroicons
```

[djc-heroicons](https://pypi.org/project/djc-heroicons/) adds an `Icon` component that renders an `<svg>` element with the icons from [HeroIcons.com](https://heroicons.com). This icon is accessible in Django templates as `{% component "icon" %}`.

Use the `name` kwarg to specify the icon name:

```django
<div>
  Items:
  <ul>
    <li>
      {% component "icon" name="academic-cap" / %}
    </li>
  </ul>
</div>
```

By default the component renders the `"outline"` variant. To render the `"solid"` variant of the icon, set kwarg `variant` to `"solid"`:

```django
{% component "icon" name="academic-cap" variant="solid" / %}
```

Common changes like color, size, or stroke width can all be set directly on the component:

```django
{% component "icon"
   name="academic-cap"
   size=48
   color="red"
   stroke_width=1.2
/ %}
```

If you need to pass attributes to the `<svg>` element, you can use the `attrs` kwarg, which accepts a dictionary:

```django
{% component "icon"
   name="academic-cap"
   attrs:id="my-svg"
   attrs:class="p-4 mb-3"
   attrs:data-id="test-123"
/ %}
```

## Usage in Python

All of the above is possible also from within Python, by importing `Icon`:

```py
from djc_heroicons import Icon

content = Icon.render(
    kwargs={
        "name": "academic-cap",
        "variant": "solid",
        "size": 48,
        "attrs": {
            "id": "my-svg",
            "class": "p-4 mb-3",
        },
    },
)
```
