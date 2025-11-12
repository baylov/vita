"""Examples demonstrating i18n usage in the VITA system."""

from core.i18n import get_text, detect_language
from models import UserSession, BookingDTO
from datetime import datetime, timezone


def example_language_detection():
    """Example: Language detection from various sources."""
    print("=" * 50)
    print("Language Detection Examples")
    print("=" * 50)
    
    # Example 1: User preference takes priority
    lang = detect_language(telegram_locale="en", user_preference="kz")
    print(f"User preference 'kz' with Telegram 'en': {lang}")
    
    # Example 2: Telegram Kazakh code mapping
    lang = detect_language(telegram_locale="kk")
    print(f"Telegram locale 'kk' (Kazakh): {lang}")
    
    # Example 3: Locale with region
    lang = detect_language(telegram_locale="ru_RU")
    print(f"Telegram locale 'ru_RU': {lang}")
    
    # Example 4: Default fallback
    lang = detect_language(telegram_locale="en")
    print(f"Unsupported locale 'en': {lang}")
    print()


def example_basic_text_retrieval():
    """Example: Basic text retrieval in different languages."""
    print("=" * 50)
    print("Basic Text Retrieval")
    print("=" * 50)
    
    # Russian greetings
    print("Russian:")
    print(f"  Welcome: {get_text('greetings.welcome', 'ru')}")
    print(f"  Good morning: {get_text('greetings.good_morning', 'ru')}")
    print()
    
    # Kazakh greetings
    print("Kazakh:")
    print(f"  Welcome: {get_text('greetings.welcome', 'kz')}")
    print(f"  Good morning: {get_text('greetings.good_morning', 'kz')}")
    print()


def example_placeholder_substitution():
    """Example: Text with placeholder substitution."""
    print("=" * 50)
    print("Placeholder Substitution")
    print("=" * 50)
    
    # Russian with placeholders
    greeting = get_text("greetings.hello", "ru", name="Иван")
    print(f"Russian: {greeting}")
    
    # Kazakh with placeholders
    greeting = get_text("greetings.hello", "kz", name="Алматы")
    print(f"Kazakh: {greeting}")
    
    # Multiple placeholders
    specialist_info = get_text(
        "booking.specialist",
        "ru",
        name="Доктор Иванов"
    )
    print(f"Specialist: {specialist_info}")
    print()


def example_booking_confirmation():
    """Example: Booking confirmation with full details."""
    print("=" * 50)
    print("Booking Confirmation")
    print("=" * 50)
    
    # Russian confirmation
    confirmation_ru = get_text(
        "confirmations.booking_created",
        "ru",
        specialist="Доктор Иванов",
        date="2025-01-15",
        time="10:00",
        duration=60
    )
    print("Russian:")
    print(confirmation_ru)
    print()
    
    # Kazakh confirmation
    confirmation_kz = get_text(
        "confirmations.booking_created",
        "kz",
        specialist="Доктор Иванов",
        date="2025-01-15",
        time="10:00",
        duration=60
    )
    print("Kazakh:")
    print(confirmation_kz)
    print()


def example_error_messages():
    """Example: Error messages in different languages."""
    print("=" * 50)
    print("Error Messages")
    print("=" * 50)
    
    errors = [
        ("errors.general", {}),
        ("errors.booking_not_found", {}),
        ("errors.time_slot_unavailable", {}),
        ("errors.booking_too_soon", {"hours": 24}),
        ("errors.validation_error", {"message": "Invalid phone number"})
    ]
    
    for key, kwargs in errors:
        print(f"\nKey: {key}")
        print(f"  RU: {get_text(key, 'ru', **kwargs)}")
        print(f"  KZ: {get_text(key, 'kz', **kwargs)}")
    print()


def example_admin_notifications():
    """Example: Admin panel notifications."""
    print("=" * 50)
    print("Admin Notifications")
    print("=" * 50)
    
    # Sync completion
    sync_msg = get_text(
        "admin.sync_completed",
        "ru",
        pulled=10,
        pushed=5,
        conflicts=0
    )
    print("Sync completed (RU):")
    print(sync_msg)
    print()
    
    # New booking notification
    new_booking = get_text(
        "notifications.new_booking_admin",
        "kz",
        client="Алматы Серікбаев",
        specialist="Доктор Иванов",
        date="2025-01-15",
        time="10:00"
    )
    print("New booking (KZ):")
    print(new_booking)
    print()


def example_menu_generation():
    """Example: Generate menu in user's language."""
    print("=" * 50)
    print("Menu Generation")
    print("=" * 50)
    
    # Russian menu
    print("Russian Menu:")
    menu_items_ru = [
        get_text("menu.book_appointment", "ru"),
        get_text("menu.my_bookings", "ru"),
        get_text("menu.view_schedule", "ru"),
        get_text("menu.settings", "ru"),
        get_text("menu.help", "ru")
    ]
    for item in menu_items_ru:
        print(f"  {item}")
    print()
    
    # Kazakh menu
    print("Kazakh Menu:")
    menu_items_kz = [
        get_text("menu.book_appointment", "kz"),
        get_text("menu.my_bookings", "kz"),
        get_text("menu.view_schedule", "kz"),
        get_text("menu.settings", "kz"),
        get_text("menu.help", "kz")
    ]
    for item in menu_items_kz:
        print(f"  {item}")
    print()


def example_user_workflow():
    """Example: Complete user workflow with localization."""
    print("=" * 50)
    print("Complete User Workflow")
    print("=" * 50)
    
    # Simulated user session
    user = UserSession(
        user_id=12345,
        telegram_username="test_user",
        language_preference="kz"
    )
    
    # Detect language
    language = detect_language(
        telegram_locale="kk",
        user_preference=user.language_preference
    )
    print(f"Detected language: {language}")
    print()
    
    # Show greeting
    greeting = get_text("greetings.hello", language, name=user.telegram_username)
    print(greeting)
    print()
    
    # Show main menu
    menu_title = get_text("menu.main", language)
    print(menu_title)
    print(get_text("menu.book_appointment", language))
    print(get_text("menu.my_bookings", language))
    print()
    
    # User books appointment
    booking_date = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    booking = BookingDTO(
        specialist_id=1,
        client_name="Test User",
        booking_datetime=booking_date,
        duration_minutes=60,
        status="confirmed"
    )
    
    # Show confirmation
    confirmation = get_text(
        "confirmations.booking_created",
        language,
        specialist="Доктор Иванов",
        date=booking.booking_datetime.strftime("%Y-%m-%d"),
        time=booking.booking_datetime.strftime("%H:%M"),
        duration=booking.duration_minutes
    )
    print(confirmation)
    print()


def example_fallback_behavior():
    """Example: Fallback behavior for missing keys."""
    print("=" * 50)
    print("Fallback Behavior")
    print("=" * 50)
    
    # Missing key returns the key itself
    missing_key = "this.key.does.not.exist"
    result = get_text(missing_key, "ru")
    print(f"Missing key '{missing_key}': {result}")
    print()
    
    # Unsupported language falls back to Russian
    text = get_text("greetings.welcome", "fr")
    print(f"Unsupported language 'fr' fallback: {text}")
    print()


if __name__ == "__main__":
    """Run all examples."""
    examples = [
        example_language_detection,
        example_basic_text_retrieval,
        example_placeholder_substitution,
        example_booking_confirmation,
        example_error_messages,
        example_admin_notifications,
        example_menu_generation,
        example_user_workflow,
        example_fallback_behavior
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Error running {example.__name__}: {e}")
            print()
    
    print("=" * 50)
    print("All examples completed!")
    print("=" * 50)
