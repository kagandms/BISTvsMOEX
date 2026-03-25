"""
Unit tests for config.yaml loading safety.
Validates RuntimeError on malformed or non-dict YAML.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.config import load_config


class TestConfigSafety:
    """Tests for config.yaml load-time validation."""

    @patch("src.config.Path.exists", return_value=True)
    def test_malformed_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """Broken YAML syntax must produce a clear RuntimeError."""
        bad_yaml = "key: [unterminated"
        with patch("builtins.open", mock_open(read_data=bad_yaml)):
            with pytest.raises(RuntimeError, match="Failed to parse configuration"):
                load_config()

    @patch("src.config.Path.exists", return_value=True)
    def test_scalar_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """A YAML file containing a plain string (not a dict) must be rejected."""
        scalar_yaml = "just a string"
        with patch("builtins.open", mock_open(read_data=scalar_yaml)):
            with pytest.raises(RuntimeError, match="must contain a YAML mapping"):
                load_config()

    @patch("src.config.Path.exists", return_value=True)
    def test_list_yaml_raises_runtime_error(self, _mock_exists: object) -> None:
        """A YAML file containing a list (not a dict) must be rejected."""
        list_yaml = "- item1\\n- item2"
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
        valid_yaml = (
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
        with patch("builtins.open", mock_open(read_data=valid_yaml)):
            config = load_config()
            assert isinstance(config, dict)
            assert "api" in config
