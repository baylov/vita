"""Internationalization (i18n) module for multi-language support."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "kz"]
DEFAULT_LANGUAGE = "ru"

# Cache for loaded locale data
_locale_cache: dict[str, dict] = {}


def _load_locale(language: str) -> dict:
    """Load locale data from JSON file.
    
    Args:
        language: Language code (e.g., 'ru', 'kz')
        
    Returns:
        Dictionary containing locale strings
        
    Raises:
        FileNotFoundError: If locale file does not exist
        json.JSONDecodeError: If locale file is invalid JSON
    """
    if language in _locale_cache:
        return _locale_cache[language]
    
    locale_path = Path(__file__).parent.parent / "locales" / f"{language}.json"
    
    if not locale_path.exists():
        logger.error(f"Locale file not found: {locale_path}")
        raise FileNotFoundError(f"Locale file not found for language: {language}")
    
    try:
        with open(locale_path, "r", encoding="utf-8") as f:
            locale_data = json.load(f)
            _locale_cache[language] = locale_data
            logger.info(f"Loaded locale data for language: {language}")
            return locale_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse locale file {locale_path}: {e}")
        raise


def _get_nested_value(data: dict, key: str) -> Optional[Any]:
    """Get value from nested dictionary using dot notation.
    
    Args:
        data: Dictionary to search in
        key: Dot-separated key path (e.g., 'greetings.welcome')
        
    Returns:
        Value if found, None otherwise
    """
    keys = key.split(".")
    current = data
    
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    
    return current


def get_text(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Get localized text for the given key and language.
    
    This function retrieves text from locale files and supports:
    - Nested key access using dot notation (e.g., 'greetings.welcome')
    - Placeholder substitution using kwargs
    - Fallback to Russian if key not found in requested language
    - Fallback to key itself if not found in any language
    
    Args:
        key: Dot-separated key path to the text (e.g., 'greetings.welcome')
        language: Language code ('ru' or 'kz'). Defaults to 'ru'
        **kwargs: Values to substitute in the text placeholders
        
    Returns:
        Localized text with substituted placeholders
        
    Example:
        >>> get_text('greetings.hello', 'ru', name='Иван')
        'Здравствуйте, Иван!'
        >>> get_text('booking.specialist', 'kz', name='Алматы')
        'Маман: Алматы'
    """
    # Normalize language code
    language = language.lower() if language else DEFAULT_LANGUAGE
    
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language '{language}', falling back to {DEFAULT_LANGUAGE}")
        language = DEFAULT_LANGUAGE
    
    # Try to get text in requested language
    try:
        locale_data = _load_locale(language)
        text = _get_nested_value(locale_data, key)
        
        if text is not None:
            return _safe_format(text, **kwargs)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load locale for language '{language}': {e}")
    
    # Fallback to Russian if key not found or error occurred
    if language != DEFAULT_LANGUAGE:
        logger.warning(f"Key '{key}' not found in language '{language}', falling back to {DEFAULT_LANGUAGE}")
        try:
            fallback_locale = _load_locale(DEFAULT_LANGUAGE)
            text = _get_nested_value(fallback_locale, key)
            
            if text is not None:
                return _safe_format(text, **kwargs)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load fallback locale: {e}")
    
    # If key not found in any language, log and return the key itself
    logger.warning(f"Translation key '{key}' not found in any locale")
    return key


def _safe_format(text: str, **kwargs) -> str:
    """Safely format text with placeholders.
    
    Attempts to substitute placeholders in the text. If any placeholder
    is missing from kwargs, it will be left as-is in the output.
    
    Args:
        text: Text with placeholders (e.g., 'Hello, {name}!')
        **kwargs: Values to substitute
        
    Returns:
        Formatted text with substituted placeholders
    """
    if not kwargs:
        return text
    
    try:
        return text.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing placeholder in text formatting: {e}")
        # Return text with partial substitution
        try:
            return text.format_map(_SafeDict(**kwargs))
        except Exception as e:
            logger.error(f"Failed to format text: {e}")
            return text
    except Exception as e:
        logger.error(f"Unexpected error during text formatting: {e}")
        return text


class _SafeDict(dict):
    """Dictionary that returns the key itself if not found."""
    
    def __missing__(self, key):
        return "{" + key + "}"


def detect_language(
    telegram_locale: Optional[str] = None,
    user_preference: Optional[str] = None
) -> str:
    """Detect user language based on available information.
    
    Detection priority:
    1. User preference (stored in UserSession)
    2. Telegram locale
    3. Default language (Russian)
    
    Args:
        telegram_locale: Telegram user language code (e.g., 'ru', 'kk')
        user_preference: User's stored language preference
        
    Returns:
        Detected language code ('ru' or 'kz')
        
    Example:
        >>> detect_language(user_preference='kz')
        'kz'
        >>> detect_language(telegram_locale='kk')
        'kz'
        >>> detect_language(telegram_locale='en')
        'ru'
    """
    # Priority 1: User preference
    if user_preference:
        normalized = user_preference.lower()
        if normalized in SUPPORTED_LANGUAGES:
            return normalized
        logger.debug(f"User preference '{user_preference}' not supported, continuing detection")
    
    # Priority 2: Telegram locale
    if telegram_locale:
        normalized = telegram_locale.lower()
        
        # Map Telegram's 'kk' (Kazakh) to our 'kz'
        if normalized in ["kk", "kaz"]:
            return "kz"
        
        if normalized in SUPPORTED_LANGUAGES:
            return normalized
        
        # Check if it's a locale with region (e.g., 'ru_RU', 'kk_KZ')
        if "_" in normalized or "-" in normalized:
            lang_code = normalized.split("_")[0].split("-")[0]
            if lang_code == "kk" or lang_code == "kaz":
                return "kz"
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
        
        logger.debug(f"Telegram locale '{telegram_locale}' not supported")
    
    # Priority 3: Default language
    logger.debug(f"No language detected, using default: {DEFAULT_LANGUAGE}")
    return DEFAULT_LANGUAGE


def clear_cache() -> None:
    """Clear the locale cache.
    
    This is useful for testing or when locale files are updated at runtime.
    """
    global _locale_cache
    _locale_cache.clear()
    logger.debug("Locale cache cleared")
