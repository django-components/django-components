# Sample Django project with django_components

## Installation

1. Prepare virtual environment:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

## Development server

```sh
python manage.py runserver
```

The app will be available at http://localhost:8000/.

To see more examples, visit http://localhost:8000/examples/.

### Serving static files

Assuming that you're running the dev server with `DEBUG=True` setting, ALL
static files (JS/CSS/HTML/PY) will be accessible under the `/static/` URL path.

## Production server

1. Prepare static files

   ```sh
   python manage.py collectstatic
   ```

2. Set `DEBUG = False` in [settings.py](./sampleproject/settings.py).

3. Start server with gunicorn

   ```sh
   gunicorn sampleproject.wsgi:application
   ```

The app will be available at http://localhost:8000/.

### Serving static files

This project uses [WhiteNoise](https://whitenoise.readthedocs.io/en/stable/) to configure Django to serve static files
even for production environment.

Assuming that you're running the prod server with:

1. `DEBUG = False` setting
2. `"django.contrib.staticfiles"` in the `INSTALLED_APPS`

Then Django will server only JS and CSS files under the `/static/` URL path.

You can verify that this is true by starting the prod server and then navigating to:

- http://127.0.0.1:8000/static/calendar/calendar.js
- http://127.0.0.1:8000/static/calendar/calendar.css
- http://127.0.0.1:8000/static/calendar/calendar.html
- http://127.0.0.1:8000/static/calendar/calendar.py
