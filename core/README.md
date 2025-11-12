# Core Modules

## Internationalization (i18n)

The `core/i18n.py` module provides comprehensive localization support for Russian (RU) and Kazakh (KZ) languages.

### Features

- **Multi-language Support**: Russian and Kazakh translations
- **Nested Key Access**: Use dot notation to access nested translations (e.g., `greetings.welcome`)
- **Placeholder Substitution**: Safe formatting with named placeholders
- **Fallback Logic**: Automatic fallback to Russian if key not found in requested language
- **Language Detection**: Smart detection based on Telegram locale and user preferences
- **Logging**: Warnings logged for missing keys and unsupported languages
- **Caching**: Locale data cached for performance

### Quick Start

```python
from core.i18n import get_text, detect_language

# Detect user's language
user_language = detect_language(
    telegram_locale="kk",  # Telegram language code
    user_preference="kz"   # Stored user preference
)

# Get localized text
welcome = get_text("greetings.welcome", user_language)
# Returns: "VITA жазылу жүйесіне қош келдіңіз!" (for KZ)

# Get text with placeholders
greeting = get_text("greetings.hello", user_language, name="Алматы")
# Returns: "Сәлеметсіз бе, Алматы!" (for KZ)
```

### API Reference

#### `get_text(key, language='ru', **kwargs) -> str`

Retrieve localized text for the given key and language.

**Parameters:**
- `key` (str): Dot-separated path to the translation (e.g., "greetings.welcome")
- `language` (str): Language code ("ru" or "kz"). Defaults to "ru"
- `**kwargs`: Values to substitute in placeholders

**Returns:**
- Localized text with substituted placeholders

**Examples:**
```python
# Simple text
text = get_text("errors.general", "ru")
# "❌ Произошла ошибка. Пожалуйста, попробуйте позже."

# Text with placeholders
booking = get_text(
    "confirmations.booking_created",
    "ru",
    specialist="Доктор Иванов",
    date="2025-01-15",
    time="10:00",
    duration=60
)

# Fallback behavior
text = get_text("nonexistent.key", "ru")
# Returns: "nonexistent.key"
```

#### `detect_language(telegram_locale=None, user_preference=None) -> str`

Detect user's preferred language based on available information.

**Detection Priority:**
1. User preference (stored in UserSession)
2. Telegram locale
3. Default language (Russian)

**Parameters:**
- `telegram_locale` (str, optional): Telegram language code (e.g., "ru", "kk", "en")
- `user_preference` (str, optional): User's stored language preference

**Returns:**
- Detected language code ("ru" or "kz")

**Examples:**
```python
# User preference takes priority
lang = detect_language(telegram_locale="en", user_preference="kz")
# Returns: "kz"

# Telegram locale mapping (kk -> kz)
lang = detect_language(telegram_locale="kk")
# Returns: "kz"

# Locale with region
lang = detect_language(telegram_locale="ru_RU")
# Returns: "ru"

# Unsupported locale fallback
lang = detect_language(telegram_locale="en")
# Returns: "ru" (default)
```

#### `clear_cache() -> None`

Clear the locale data cache. Useful for testing or when locale files are updated at runtime.

```python
from core.i18n import clear_cache

clear_cache()
```

### Locale Files

Translations are stored in JSON files:
- `locales/ru.json` - Russian translations
- `locales/kz.json` - Kazakh translations

**Structure:**
```json
{
  "greetings": {
    "welcome": "Welcome message",
    "hello": "Hello, {name}!"
  },
  "errors": {
    "general": "General error message"
  }
}
```

**Available Sections:**
- `greetings` - Welcome messages and greetings
- `menu` - Menu items and navigation
- `prompts` - User input prompts
- `booking` - Booking-related text
- `confirmations` - Success confirmations
- `errors` - Error messages
- `fallback` - Fallback messages
- `admin` - Admin panel text
- `notifications` - Notification templates
- `urgency` - Urgency tags
- `status` - Status labels
- `days` - Day names
- `common` - Common UI text
- `help` - Help and documentation

### Integration Example

```python
from core.i18n import get_text, detect_language
from models import UserSession

def handle_user_message(user: UserSession, telegram_user):
    # Detect language
    language = detect_language(
        telegram_locale=telegram_user.language_code,
        user_preference=user.language_preference
    )
    
    # Get localized greeting
    greeting = get_text("greetings.hello", language, name=user.telegram_username)
    
    # Get menu options
    menu_items = [
        get_text("menu.book_appointment", language),
        get_text("menu.my_bookings", language),
        get_text("menu.view_schedule", language),
    ]
    
    # Send response to user
    return greeting + "\n\n" + "\n".join(menu_items)
```

### Booking Workflow Example

```python
from core.i18n import get_text
from models import BookingDTO

def confirm_booking(booking: BookingDTO, language: str):
    # Format booking confirmation
    confirmation = get_text(
        "confirmations.booking_created",
        language,
        specialist=booking.specialist_name,
        date=booking.booking_datetime.strftime("%Y-%m-%d"),
        time=booking.booking_datetime.strftime("%H:%M"),
        duration=booking.duration_minutes
    )
    
    return confirmation

def notify_admin(booking: BookingDTO, language: str):
    # Format admin notification
    notification = get_text(
        "notifications.new_booking_admin",
        language,
        client=booking.client_name,
        specialist=booking.specialist_name,
        date=booking.booking_datetime.strftime("%Y-%m-%d"),
        time=booking.booking_datetime.strftime("%H:%M")
    )
    
    return notification
```

### Error Handling Example

```python
from core.i18n import get_text

def handle_booking_error(error_type: str, language: str, **kwargs):
    # Get appropriate error message
    if error_type == "time_slot_unavailable":
        message = get_text("errors.time_slot_unavailable", language)
    elif error_type == "past_date":
        message = get_text("errors.past_date", language)
    elif error_type == "booking_too_soon":
        message = get_text("errors.booking_too_soon", language, hours=24)
    else:
        message = get_text("errors.general", language)
    
    return message
```

### Best Practices

1. **Always specify language**: Pass the detected language to `get_text()`
2. **Use consistent keys**: Follow the dot notation pattern across the codebase
3. **Provide all placeholders**: Ensure all required placeholders are provided in kwargs
4. **Log missing keys**: The module automatically logs warnings for missing keys
5. **Test both languages**: Verify translations work for both Russian and Kazakh
6. **Keep keys synchronized**: Ensure both locale files have the same key structure

### Testing

The module includes comprehensive tests covering:
- Key retrieval for both languages
- Fallback behavior for missing keys and unsupported languages
- Placeholder substitution with missing values
- Language detection from various sources
- Locale file structure validation

Run tests:
```bash
pytest tests/test_i18n.py -v
```

### Supported Languages

- **ru** (Russian) - Default language
- **kz** (Kazakh) - Mapped from Telegram's "kk" code

### Language Codes Mapping

The module automatically maps various language codes:
- `kk` → `kz` (Telegram Kazakh code)
- `kaz` → `kz` (ISO 639-2 code)
- `ru_RU` → `ru` (Locale with region)
- `kk_KZ` → `kz` (Locale with region)

### Extending to New Languages

To add a new language:

1. Create a new locale file: `locales/XX.json`
2. Add the language code to `SUPPORTED_LANGUAGES` in `core/i18n.py`
3. Translate all keys from `ru.json` to the new language
4. Update tests to include the new language
5. Add language code mappings in `detect_language()` if needed
