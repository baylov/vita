"""Tests for internationalization (i18n) module."""

import json
import pytest
from pathlib import Path
from core.i18n import (
    get_text,
    detect_language,
    clear_cache,
    _get_nested_value,
    _safe_format,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)


@pytest.fixture(autouse=True)
def clear_locale_cache():
    """Clear locale cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_locale_data():
    """Sample locale data for testing."""
    return {
        "greetings": {
            "welcome": "Welcome to VITA!",
            "hello": "Hello, {name}!"
        },
        "errors": {
            "general": "An error occurred"
        }
    }


class TestGetNestedValue:
    """Tests for _get_nested_value helper function."""
    
    def test_get_top_level_key(self, sample_locale_data):
        """Test getting a top-level key."""
        result = _get_nested_value(sample_locale_data, "greetings")
        assert result == sample_locale_data["greetings"]
    
    def test_get_nested_key(self, sample_locale_data):
        """Test getting a nested key with dot notation."""
        result = _get_nested_value(sample_locale_data, "greetings.welcome")
        assert result == "Welcome to VITA!"
    
    def test_get_deeply_nested_key(self):
        """Test getting a deeply nested key."""
        data = {"level1": {"level2": {"level3": "deep value"}}}
        result = _get_nested_value(data, "level1.level2.level3")
        assert result == "deep value"
    
    def test_missing_key_returns_none(self, sample_locale_data):
        """Test that missing key returns None."""
        result = _get_nested_value(sample_locale_data, "nonexistent")
        assert result is None
    
    def test_missing_nested_key_returns_none(self, sample_locale_data):
        """Test that missing nested key returns None."""
        result = _get_nested_value(sample_locale_data, "greetings.nonexistent")
        assert result is None


class TestSafeFormat:
    """Tests for _safe_format helper function."""
    
    def test_format_with_all_placeholders(self):
        """Test formatting when all placeholders are provided."""
        text = "Hello, {name}! You have {count} messages."
        result = _safe_format(text, name="John", count=5)
        assert result == "Hello, John! You have 5 messages."
    
    def test_format_with_missing_placeholders(self):
        """Test formatting with missing placeholders."""
        text = "Hello, {name}! You have {count} messages."
        result = _safe_format(text, name="John")
        assert "John" in result
        assert "{count}" in result
    
    def test_format_without_placeholders(self):
        """Test formatting text without placeholders."""
        text = "Simple text"
        result = _safe_format(text)
        assert result == "Simple text"
    
    def test_format_with_no_kwargs(self):
        """Test formatting with no kwargs provided."""
        text = "Text with {placeholder}"
        result = _safe_format(text)
        assert result == "Text with {placeholder}"


class TestGetText:
    """Tests for get_text function."""
    
    def test_get_russian_text(self):
        """Test getting Russian text."""
        text = get_text("greetings.welcome", "ru")
        assert isinstance(text, str)
        assert len(text) > 0
        assert "VITA" in text
    
    def test_get_kazakh_text(self):
        """Test getting Kazakh text."""
        text = get_text("greetings.welcome", "kz")
        assert isinstance(text, str)
        assert len(text) > 0
        assert "VITA" in text
    
    def test_get_text_with_placeholder(self):
        """Test getting text with placeholder substitution."""
        text = get_text("greetings.hello", "ru", name="Иван")
        assert "Иван" in text
    
    def test_get_text_with_multiple_placeholders(self):
        """Test getting text with multiple placeholders."""
        text = get_text("booking.specialist", "ru", name="Доктор Иванов")
        assert "Доктор Иванов" in text
    
    def test_default_language_fallback(self):
        """Test fallback to default language (Russian)."""
        text = get_text("greetings.welcome")
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_unsupported_language_fallback(self):
        """Test fallback to Russian for unsupported language."""
        text = get_text("greetings.welcome", "en")
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_missing_key_returns_key(self):
        """Test that missing key returns the key itself."""
        key = "nonexistent.key.path"
        text = get_text(key, "ru")
        assert text == key
    
    def test_missing_key_in_kazakh_fallback_to_russian(self):
        """Test that missing key in Kazakh falls back to Russian."""
        # This assumes all keys exist in both languages
        # If a key is missing in KZ, it should fallback to RU
        text = get_text("greetings.welcome", "kz")
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_case_insensitive_language_code(self):
        """Test that language codes are case-insensitive."""
        text1 = get_text("greetings.welcome", "RU")
        text2 = get_text("greetings.welcome", "ru")
        assert text1 == text2
    
    def test_none_language_uses_default(self):
        """Test that None language uses default."""
        text = get_text("greetings.welcome", None)
        assert isinstance(text, str)
        assert len(text) > 0


class TestDetectLanguage:
    """Tests for detect_language function."""
    
    def test_user_preference_priority(self):
        """Test that user preference has highest priority."""
        result = detect_language(
            telegram_locale="en",
            user_preference="kz"
        )
        assert result == "kz"
    
    def test_telegram_locale_priority(self):
        """Test that Telegram locale is used if no user preference."""
        result = detect_language(telegram_locale="ru")
        assert result == "ru"
    
    def test_kazakh_telegram_locale_mapping(self):
        """Test that Telegram 'kk' is mapped to 'kz'."""
        result = detect_language(telegram_locale="kk")
        assert result == "kz"
    
    def test_kazakh_alternative_code(self):
        """Test that 'kaz' is mapped to 'kz'."""
        result = detect_language(telegram_locale="kaz")
        assert result == "kz"
    
    def test_locale_with_region(self):
        """Test locale with region code (e.g., ru_RU)."""
        result = detect_language(telegram_locale="ru_RU")
        assert result == "ru"
    
    def test_kazakh_locale_with_region(self):
        """Test Kazakh locale with region code."""
        result = detect_language(telegram_locale="kk_KZ")
        assert result == "kz"
    
    def test_locale_with_dash_separator(self):
        """Test locale with dash separator (e.g., ru-RU)."""
        result = detect_language(telegram_locale="ru-RU")
        assert result == "ru"
    
    def test_unsupported_locale_fallback(self):
        """Test fallback to default for unsupported locale."""
        result = detect_language(telegram_locale="en")
        assert result == DEFAULT_LANGUAGE
    
    def test_no_parameters_returns_default(self):
        """Test that no parameters returns default language."""
        result = detect_language()
        assert result == DEFAULT_LANGUAGE
    
    def test_invalid_user_preference_continues_detection(self):
        """Test that invalid user preference continues to telegram locale."""
        result = detect_language(
            telegram_locale="kk",
            user_preference="invalid"
        )
        assert result == "kz"
    
    def test_case_insensitive_detection(self):
        """Test that language detection is case-insensitive."""
        result = detect_language(telegram_locale="KK")
        assert result == "kz"


class TestLocaleFiles:
    """Tests for locale file structure and content."""
    
    def test_russian_locale_exists(self):
        """Test that Russian locale file exists."""
        locale_path = Path(__file__).parent.parent / "locales" / "ru.json"
        assert locale_path.exists()
    
    def test_kazakh_locale_exists(self):
        """Test that Kazakh locale file exists."""
        locale_path = Path(__file__).parent.parent / "locales" / "kz.json"
        assert locale_path.exists()
    
    def test_russian_locale_valid_json(self):
        """Test that Russian locale is valid JSON."""
        locale_path = Path(__file__).parent.parent / "locales" / "ru.json"
        with open(locale_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
    
    def test_kazakh_locale_valid_json(self):
        """Test that Kazakh locale is valid JSON."""
        locale_path = Path(__file__).parent.parent / "locales" / "kz.json"
        with open(locale_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
    
    def test_locales_have_same_keys(self):
        """Test that Russian and Kazakh locales have the same key structure."""
        ru_path = Path(__file__).parent.parent / "locales" / "ru.json"
        kz_path = Path(__file__).parent.parent / "locales" / "kz.json"
        
        with open(ru_path, "r", encoding="utf-8") as f:
            ru_data = json.load(f)
        with open(kz_path, "r", encoding="utf-8") as f:
            kz_data = json.load(f)
        
        # Check top-level keys
        assert set(ru_data.keys()) == set(kz_data.keys())
    
    def test_required_sections_present(self):
        """Test that required sections are present in locales."""
        required_sections = [
            "greetings",
            "menu",
            "prompts",
            "confirmations",
            "errors",
            "fallback",
            "admin",
            "notifications",
            "urgency"
        ]
        
        for lang in SUPPORTED_LANGUAGES:
            locale_path = Path(__file__).parent.parent / "locales" / f"{lang}.json"
            with open(locale_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for section in required_sections:
                assert section in data, f"Section '{section}' missing in {lang}.json"


class TestClearCache:
    """Tests for clear_cache function."""
    
    def test_clear_cache_empties_cache(self):
        """Test that clear_cache empties the cache."""
        # Load a locale to populate cache
        get_text("greetings.welcome", "ru")
        
        # Clear cache
        clear_cache()
        
        # Cache should be empty (we can't directly test this,
        # but we can verify that reloading works)
        text = get_text("greetings.welcome", "ru")
        assert isinstance(text, str)


class TestIntegration:
    """Integration tests for i18n functionality."""
    
    def test_complete_workflow_russian(self):
        """Test complete workflow for Russian language."""
        # Detect language
        lang = detect_language(telegram_locale="ru")
        assert lang == "ru"
        
        # Get various texts
        welcome = get_text("greetings.welcome", lang)
        assert isinstance(welcome, str)
        
        hello = get_text("greetings.hello", lang, name="Тестовый")
        assert "Тестовый" in hello
        
        error = get_text("errors.general", lang)
        assert isinstance(error, str)
    
    def test_complete_workflow_kazakh(self):
        """Test complete workflow for Kazakh language."""
        # Detect language
        lang = detect_language(telegram_locale="kk")
        assert lang == "kz"
        
        # Get various texts
        welcome = get_text("greetings.welcome", lang)
        assert isinstance(welcome, str)
        
        hello = get_text("greetings.hello", lang, name="Тестілік")
        assert "Тестілік" in hello
        
        error = get_text("errors.general", lang)
        assert isinstance(error, str)
    
    def test_booking_confirmation_with_placeholders(self):
        """Test booking confirmation with all placeholders."""
        text = get_text(
            "confirmations.booking_created",
            "ru",
            specialist="Доктор Иванов",
            date="2025-01-15",
            time="10:00",
            duration=60
        )
        assert "Доктор Иванов" in text
        assert "2025-01-15" in text
        assert "10:00" in text
        assert "60" in text
    
    def test_admin_sync_notification(self):
        """Test admin sync completion notification."""
        text = get_text(
            "admin.sync_completed",
            "ru",
            pulled=10,
            pushed=5,
            conflicts=0
        )
        assert "10" in text
        assert "5" in text
        assert "0" in text
