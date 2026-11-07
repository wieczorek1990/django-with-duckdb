from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "django-insecure-sample-duckdb-demo-key"
DEBUG = False
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "sample.apps.SampleConfig",
]
MIDDLEWARE = []
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.duckdb",
        "NAME": BASE_DIR / "sample.duckdb",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
