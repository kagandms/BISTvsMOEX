"""
Unit tests for config loading and environment override safety.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import mock_open, patch

import pytest

from src.config import get_sentry_traces_sample_rate, load_config

_VALID_YAML = (
    "api:\n"
    "  moex_iss:\n"
    "    base_url: https://example.com\n"
    "    timeout_seconds: 15\n"
    "    max_retries: 3\n"
    "    retry_delay_seconds: 1\n"
    "data:\n"
    "  moex_delay_days: 2\n"
    "  default_lookback_days: 365\n"
    "  min_data_points: 5\n"
)


def _load_config_with_env(env: dict[str, str], yaml_text: str = _VALID_YAML) -> dict[str, Any]:
    """Load config.yaml content under a controlled environment."""

    with patch.dict("src.config.os.environ", env, clear=True):
        with patch("builtins.open", mock_open(read_data=yaml_text)):
            return load_config()


class TestConfigSafety:
    """Tests for config.yaml load-time validation and env overrides."""

    @patch("src.config.Path.exists", return_value=True)
    def test_malformed_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """Broken YAML syntax must produce a clear RuntimeError."""

        bad_yaml = "key: [unterminated"
        with patch.dict("src.config.os.environ", {}, clear=True):
            with patch("builtins.open", mock_open(read_data=bad_yaml)):
                with pytest.raises(RuntimeError, match="Failed to parse configuration"):
                    load_config()

    @patch("src.config.Path.exists", return_value=True)
    def test_scalar_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """A YAML file containing a plain string (not a dict) must be rejected."""

        scalar_yaml = "just a string"
        with patch.dict("src.config.os.environ", {}, clear=True):
            with patch("builtins.open", mock_open(read_data=scalar_yaml)):
                with pytest.raises(RuntimeError, match="must contain a YAML mapping"):
                    load_config()

    @patch("src.config.Path.exists", return_value=True)
    def test_list_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """A YAML file containing a list (not a dict) must be rejected."""

        list_yaml = "- item1\\n- item2"
        with patch.dict("src.config.os.environ", {}, clear=True):
            with patch("builtins.open", mock_open(read_data=list_yaml)):
                with pytest.raises(RuntimeError, match="must contain a YAML mapping"):
                    load_config()

    def test_missing_config_file_raises_file_not_found(self) -> None:
        """Missing config.yaml must raise FileNotFoundError."""

        with patch("src.config.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Configuration file not found"):
                load_config()

    @patch("src.config.Path.exists", return_value=True)
    def test_valid_yaml_dict_loads_successfully(self, _mock_exists: object) -> None:
        """A valid YAML dict should load without exceptions."""

        config = _load_config_with_env({})
        assert isinstance(config, dict)
        assert "api" in config

    @patch("src.config.Path.exists", return_value=True)
    def test_timeout_override_applies_when_positive(self, _mock_exists: object) -> None:
        """A valid timeout override must replace the YAML default."""

        config = _load_config_with_env({"BM_TIMEOUT": "30"})
        assert config["api"]["moex_iss"]["timeout_seconds"] == 30

    @patch("src.config.Path.exists", return_value=True)
    def test_timeout_override_ignores_zero_value(self, _mock_exists: object) -> None:
        """A zero timeout override must be ignored for safety."""

        config = _load_config_with_env({"BM_TIMEOUT": "0"})
        assert config["api"]["moex_iss"]["timeout_seconds"] == 15

    @patch("src.config.Path.exists", return_value=True)
    def test_moex_delay_override_applies_when_positive(self, _mock_exists: object) -> None:
        """A valid MOEX delay override must replace the YAML default."""

        config = _load_config_with_env({"BM_MOEX_DELAY": "4"})
        assert config["data"]["moex_delay_days"] == 4

    @patch("src.config.Path.exists", return_value=True)
    def test_moex_delay_override_ignores_zero_value(self, _mock_exists: object) -> None:
        """A zero MOEX delay override must be ignored for safety."""

        config = _load_config_with_env({"BM_MOEX_DELAY": "0"})
        assert config["data"]["moex_delay_days"] == 2

    def test_sentry_trace_sample_rate_returns_default_when_unset(self) -> None:
        """Missing Sentry sampling env var must use the production-safe default."""

        with patch.dict("src.config.os.environ", {}, clear=True):
            assert get_sentry_traces_sample_rate() == pytest.approx(0.1)

    def test_sentry_trace_sample_rate_uses_valid_env_value(self) -> None:
        """A valid Sentry sampling env var must be applied."""

        with patch.dict(
            "src.config.os.environ",
            {"BM_SENTRY_TRACE_SAMPLE_RATE": "0.25"},
            clear=True,
        ):
            assert get_sentry_traces_sample_rate() == pytest.approx(0.25)

    def test_sentry_trace_sample_rate_ignores_out_of_range_value(self) -> None:
        """Out-of-range Sentry sampling values must fall back to the default."""

        with patch.dict(
            "src.config.os.environ",
            {"BM_SENTRY_TRACE_SAMPLE_RATE": "1.5"},
            clear=True,
        ):
            assert get_sentry_traces_sample_rate() == pytest.approx(0.1)
