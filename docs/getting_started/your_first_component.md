### Overview

A component in django-components consists of HTML, JavaScript, and CSS.

These are tied together by a Python component class:

```python title="components/product_card/product_card.py"
from django_components import Component, register

@register("product_card")
class ProductCard(Component):
    template_file = "product_card.html"
    js_file = "product_card.js"
    css_file = "product_card.css"

    class Kwargs:
        product_id: int
        show_price: bool = True
        theme: str = "light"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        product = Product.objects.get(id=kwargs.product_id)
        return {
            "product": product,
            "show_price": kwargs.show_price,
            "is_in_stock": product.stock_count > 0,
        }

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        product = Product.objects.get(id=kwargs.product_id)
        return {
            "product_id": kwargs.product_id,
            "price": float(product.price),
            "api_endpoint": f"/api/products/{kwargs.product_id}/",
        }

    def get_css_data(self, args, kwargs: Kwargs, slots, context):
        themes = {
            "light": {
                "card_bg": "#ffffff",
                "text_color": "#333333",
                "price_color": "#e63946",
            },
            "dark": {
                "card_bg": "#242424",
                "text_color": "#f1f1f1",
                "price_color": "#ff6b6b",
            },
        }
        theme_vars = themes.get(kwargs.theme, themes["light"])
        return theme_vars
```

In your template:

```htmldjango title="templates/product_card/product_card.html"
<div class="product-card" data-product-id="{{ product.id }}">
    <img src="{{ product.image_url }}" alt="{{ product.name }}">
    <h3>{{ product.name }}</h3>

    {% if show_price %}
        <p class="price">${{ product.price }}</p>
    {% endif %}

    {% if is_in_stock %}
        <button class="add-to-cart">Add to Cart</button>
    {% else %}
        <p class="out-of-stock">Out of Stock</p>
    {% endif %}
</div>
```

JavaScript:

```javascript title="components/product_card/product_card.js"
// Access component JS variables in $onComponent callback
$onComponent(({ product_id, price, api_endpoint }, ctx) => {
  const containerEl = ctx.els[0];
  containerEl.querySelector(".add-to-cart")
    .addEventListener("click", () => {
      fetch(api_endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "add_to_cart", price: price }),
      });
    });
});
```

CSS:

```css title="components/product_card/product_card.css"
/* Access component CSS variables */
.product-card {
  background-color: var(--card_bg);
  color: var(--text_color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.price {
  color: var(--price_color);
  font-weight: bold;
}
```

Alternatively, you can inline HTML, JS, and CSS right into the component class:

```djc_py
from django_components import Component

class Calendar(Component):
    template = """
      <div class="calendar">
        Today's date is <span>{{ date }}</span>
      </div>
    """

    css = """
      .calendar {
        width: 200px;
        background: pink;
      }
    """

    js = """
      document.querySelector(".calendar").onclick = function () {
        alert("Clicked calendar!");
      };
    """
```

!!! note

    If you inline the HTML, JS and CSS code into the Python class, you can set up
    [syntax highlighting](../concepts/fundamentals/single_file_components.md#syntax-highlighting) for better experience.

    **NOTE:** Autocompletion / intellisense does not currently work with syntax highlighting.

We'll start by creating a component that defines only a Django template:

### 1. Create project structure

Start by creating empty `calendar.py` and `calendar.html` files:

```
sampleproject/
├── calendarapp/
├── components/             🆕
│   └── calendar/           🆕
│       ├── calendar.py     🆕
│       └── calendar.html   🆕
├── sampleproject/
├── manage.py
└── requirements.txt
```

### 2. Write Django template

Inside `calendar.html`, write:

```htmldjango title="[project root]/components/calendar/calendar.html"
<div class="calendar">
  Today's date is <span>{{ date }}</span>
</div>
```

In this example we've defined one template variable `date`. You can use any and as many variables as you like. These variables will be
defined in the Python file in [`get_template_data()`](../reference/api.md#django_components.Component.get_template_data)
when creating an instance of this component.

!!! note

    The template will be rendered with whatever template backend you've specified in your Django settings file.

    Currently django-components supports only the default `"django.template.backends.django.DjangoTemplates"` template backend!

### 3. Create new Component in Python

In `calendar.py`, create a subclass of [Component](../reference/api.md#django_components.Component)
to create a new component.

To link the HTML template with our component, set [`template_file`](../reference/api.md#django_components.Component.template_file)
to the name of the HTML file.

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"
```

!!! note

    The path to the template file can be either:

    1. Relative to the component's python file (as seen above),
    2. Relative to any of the component directories as defined by
    [`COMPONENTS.dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.dirs)
    and/or [`COMPONENTS.app_dirs`](../reference/settings.md#django_components.app_settings.ComponentsSettings.app_dirs)
    (e.g. `[your apps]/components` dir and `[project root]/components`)

### 4. Define the template variables

In `calendar.html`, we've used the variable `date`. So we need to define it for the template to work.

First, we define what inputs the component accepts using [`Component.Kwargs`](../reference/api.md#django_components.Component.Kwargs).
This class defines the keyword arguments that can be passed to the component, with optional default values.

Then, we use [`Component.get_template_data()`](../reference/api.md#django_components.Component.get_template_data)
to provide variables to the template. It's a function that returns a dictionary. The entries in this dictionary
will become available within the template as variables, e.g. as `{{ date }}`.

```python title="[project root]/components/calendar/calendar.py"
from django_components import Component

class Calendar(Component):
    template_file = "calendar.html"

    class Kwargs:
        date: str = "1970-01-01"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "date": kwargs.date,
        }
```

Now, when we render the component with [`Component.render()`](../reference/api.md#django_components.Component.render)
method:

```py
Calendar.render(kwargs={"date": "2024-11-06"})
```

It will output

```html
<div class="calendar">
  Today's date is <span>2024-11-06</span>
</div>
```

Or, if we don't pass a date, it will use the default value:

```py
Calendar.render()
```

```html
<div class="calendar">
  Today's date is <span>1970-01-01</span>
</div>
```

And voilá!! We've created our first component.

---

Next, [let's add JS and CSS to this component ➡️](adding_js_and_css.md).
