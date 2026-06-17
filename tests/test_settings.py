"""
Tests for the configuration system (Settings, YAML loading, overrides).
"""

from __future__ import annotations

import pytest

from src.config.settings import Settings, _load_yaml_config, load_settings


class TestSettingsDefaults:
    """Test that Settings has correct default values from architecture spec."""

    def test_default_review_window(self) -> None:
        s = Settings()
        assert s.review_window_weeks == 10

    def test_default_cluster_size(self) -> None:
        s = Settings()
        assert s.min_cluster_size == 5

    def test_default_max_themes(self) -> None:
        s = Settings()
        assert s.max_themes == 5

    def test_default_quotes_per_theme(self) -> None:
        s = Settings()
        assert s.quotes_per_theme == 3

    def test_default_actions_per_theme(self) -> None:
        s = Settings()
        assert s.actions_per_theme == 2

    def test_default_llm_model(self) -> None:
        s = Settings()
        assert s.llm_model == "llama-3.3-70b-versatile"

    def test_default_embedding_model(self) -> None:
        s = Settings()
        assert s.embedding_model == "all-MiniLM-L6-v2"

    def test_default_max_tokens(self) -> None:
        s = Settings()
        assert s.max_tokens_per_run == 60000

    def test_default_max_reviews(self) -> None:
        s = Settings()
        assert s.max_reviews_per_product == 500

    def test_default_email_mode(self) -> None:
        s = Settings()
        assert s.email_mode == "draft"

    def test_default_cost_threshold(self) -> None:
        s = Settings()
        assert s.cost_alert_threshold_usd == 2.00

    def test_default_retry(self) -> None:
        s = Settings()
        assert s.retry_max_attempts == 3
        assert s.retry_backoff_base_sec == 2

    def test_default_log_level(self) -> None:
        s = Settings()
        assert s.log_level == "INFO"


class TestSettingsValidation:
    """Test field validation on Settings."""

    def test_invalid_log_level_raises(self) -> None:
        with pytest.raises(ValueError, match="log_level must be one of"):
            Settings(log_level="VERBOSE")

    def test_log_level_normalized_to_upper(self) -> None:
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_review_window_too_low_raises(self) -> None:
        with pytest.raises(ValueError):
            Settings(review_window_weeks=0)

    def test_min_cluster_size_too_low_raises(self) -> None:
        with pytest.raises(ValueError):
            Settings(min_cluster_size=1)

    def test_invalid_email_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            Settings(email_mode="broadcast")  # type: ignore[arg-type]


class TestSettingsOverrides:
    """Test that overrides via load_settings() work correctly."""

    def test_keyword_override(self) -> None:
        s = load_settings(max_themes=10, log_level="DEBUG")
        assert s.max_themes == 10
        assert s.log_level == "DEBUG"

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PULSE_MAX_THEMES", "7")
        s = Settings()
        assert s.max_themes == 7

    def test_env_var_email_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PULSE_EMAIL_MODE", "send")
        s = Settings()
        assert s.email_mode == "send"


class TestYAMLLoading:
    """Test YAML config file loading."""

    def test_load_yaml_returns_dict(self) -> None:
        result = _load_yaml_config()
        assert isinstance(result, dict)

    def test_load_settings_from_yaml(self) -> None:
        # Should load from config/default.yaml in the project
        s = load_settings()
        # Verify it loaded (defaults from YAML should match code defaults)
        assert s.review_window_weeks == 10
        assert s.email_mode == "draft"
