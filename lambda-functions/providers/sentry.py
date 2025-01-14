import os
from sentry_sdk import init as sentry_sdk_init

sentry_sdk_init(
    dsn=os.environ.get("SENTRY_DSN"),
    max_breadcrumbs=50,
    enable_tracing=True,
    attach_stacktrace=True,
    environment=os.environ.get("ENV"),
)
