"""
Optional Sentry instrumentation.

Sentry is initialised at app startup only when the ``SENTRY_DSN`` env var is
set. When unset (the default), this module is effectively a no-op so local /
CI runs incur no overhead and the dependency stays optional.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_initialized = False


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    traces_sample_rate: Optional[float] = None,
    profiles_sample_rate: Optional[float] = None,
    release: Optional[str] = None,
) -> bool:
    """
    Initialise the Sentry SDK if configuration is present.

    Returns True if Sentry was actually initialised, False otherwise. Safe to
    call multiple times - subsequent calls are no-ops.
    """
    global _initialized
    if _initialized:
        return True

    dsn = dsn or os.environ.get("SENTRY_DSN")
    if not dsn:
        logger.debug("SENTRY_DSN not set; skipping Sentry initialisation.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed - "
            "install with `pip install 'sentry-sdk[fastapi]'`."
        )
        return False

    environment = environment or os.environ.get("FASTAPI_ENV", "development")
    if traces_sample_rate is None:
        traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    if profiles_sample_rate is None:
        profiles_sample_rate = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))
    release = release or os.environ.get("SENTRY_RELEASE")

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    _initialized = True
    logger.info(
        "Sentry initialised (env=%s, traces=%.2f, profiles=%.2f)",
        environment, traces_sample_rate, profiles_sample_rate,
    )
    return True


def is_initialized() -> bool:
    """Whether init_sentry() has successfully initialised the SDK."""
    return _initialized
