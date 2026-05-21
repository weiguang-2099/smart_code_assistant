"""
Tests for the optional Sentry instrumentation.

The SDK is initialised only when SENTRY_DSN is set; with no DSN init_sentry
must return False and never touch the SDK so local / CI runs incur zero cost.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core import sentry as sentry_module


@pytest.fixture(autouse=True)
def _reset_init_flag():
    """Each test sees a fresh module-level flag."""
    sentry_module._initialized = False
    yield
    sentry_module._initialized = False


class TestInitSentry:
    def test_returns_false_when_no_dsn(self, monkeypatch):
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert sentry_module.init_sentry() is False
        assert sentry_module.is_initialized() is False

    def test_returns_true_when_dsn_provided_and_sdk_available(self):
        with patch("sentry_sdk.init") as mock_init:
            ok = sentry_module.init_sentry(dsn="https://example@sentry.io/1")
        assert ok is True
        assert sentry_module.is_initialized() is True
        mock_init.assert_called_once()

    def test_idempotent_subsequent_calls_do_not_reinit(self):
        with patch("sentry_sdk.init") as mock_init:
            assert sentry_module.init_sentry(dsn="https://x@s/1") is True
            assert sentry_module.init_sentry(dsn="https://x@s/1") is True
        # init invoked exactly once even across two init_sentry calls
        assert mock_init.call_count == 1

    def test_uses_env_traces_sample_rate(self, monkeypatch):
        monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.5")
        monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.2")
        with patch("sentry_sdk.init") as mock_init:
            sentry_module.init_sentry(dsn="https://x@s/1")
        kwargs = mock_init.call_args.kwargs
        assert kwargs["traces_sample_rate"] == 0.5
        assert kwargs["profiles_sample_rate"] == 0.2

    def test_explicit_args_override_env(self, monkeypatch):
        monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.5")
        with patch("sentry_sdk.init") as mock_init:
            sentry_module.init_sentry(
                dsn="https://x@s/1",
                traces_sample_rate=0.1,
                environment="staging",
                release="v1.2.3",
            )
        kwargs = mock_init.call_args.kwargs
        assert kwargs["traces_sample_rate"] == 0.1
        assert kwargs["environment"] == "staging"
        assert kwargs["release"] == "v1.2.3"

    def test_send_default_pii_disabled(self):
        with patch("sentry_sdk.init") as mock_init:
            sentry_module.init_sentry(dsn="https://x@s/1")
        assert mock_init.call_args.kwargs["send_default_pii"] is False

    def test_missing_sdk_returns_false(self, monkeypatch):
        # Simulate sentry_sdk not installed
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("sentry_sdk"):
                raise ImportError("sentry_sdk missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        ok = sentry_module.init_sentry(dsn="https://x@s/1")
        assert ok is False
        assert sentry_module.is_initialized() is False
