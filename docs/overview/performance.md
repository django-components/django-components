We track the performance of `django-components` using [ASV](https://asv.readthedocs.io/en/stable/).

See the [benchmarks dashboard](../../benchmarks).

Our aim is to be at least as fast as Django templates.

As of `0.130`, `django-components` is ~4x slower than Django templates.

| | Render time|
|----------|----------------------|
| django | 68.9±0.6ms |
| django-components | 259±4ms |

See the [full performance breakdown](https://django-components.github.io/django-components/latest/benchmarks/) for more information.
