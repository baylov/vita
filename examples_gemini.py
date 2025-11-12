"""Examples of using the Gemini AI service for request analysis and response generation."""

from services.gemini import GeminiClient, GeminiAnalyzer, RequestType, UrgencyLevel


def example_classifier():
    """Example: Classify user requests."""
    print("=" * 60)
    print("Example: Request Classification")
    print("=" * 60)

    # Initialize analyzer (requires GEMINI_API_KEY environment variable)
    try:
        analyzer = GeminiAnalyzer()
    except Exception as e:
        print(f"Note: Requires valid GEMINI_API_KEY: {e}")
        print("Showing example structure instead:\n")

        # Show what the result looks like
        print("Classification Result Structure:")
        print("- request_type: 'appointment_booking' | 'complaint' | etc.")
        print("- urgency: 'low' | 'medium' | 'high'")
        print("- specialist_suggestion: 'Cardiologist' (optional)")
        print("- confidence: 0.0 - 1.0")
        print("- reasoning: 'User wants to schedule an appointment'")
        return

    # Classify various user messages
    messages = [
        "I want to book an appointment with a cardiologist",
        "I have a complaint about the long wait times",
        "What are your clinic hours?",
        "I need to cancel my appointment",
    ]

    for message in messages:
        print(f"\nUser: {message}")
        result = analyzer.classify_request(message, language="ru")
        print(f"Type: {result.request_type.value}")
        print(f"Urgency: {result.urgency.value}")
        print(f"Confidence: {result.confidence:.2f}")
        if result.specialist_suggestion:
            print(f"Suggestion: {result.specialist_suggestion}")


def example_response_generation():
    """Example: Generate AI responses to user messages."""
    print("\n" + "=" * 60)
    print("Example: Response Generation")
    print("=" * 60)

    try:
        analyzer = GeminiAnalyzer()
    except Exception as e:
        print(f"Note: Requires valid GEMINI_API_KEY: {e}")
        print("\nExample generated responses:")
        print("1. 'You can book an appointment through our website or by calling.'")
        print("2. 'We apologize for the wait times. Your feedback helps us improve.'")
        print("3. 'Our clinic hours are 9 AM to 6 PM, Monday to Friday.'")
        return

    user_message = "How do I book an appointment?"
    context = {"clinic_name": "VITA", "available_languages": ["Russian", "Kazakh"]}

    print(f"\nUser: {user_message}")
    result = analyzer.generate_response(user_message, context=context, language="ru")

    if result.is_fallback:
        print(f"⚠️ Fallback response (API error: {result.error}):")
    else:
        print("Response:")

    print(result.text)


def example_complaint_summarization():
    """Example: Summarize long complaints."""
    print("\n" + "=" * 60)
    print("Example: Complaint Summarization")
    print("=" * 60)

    try:
        analyzer = GeminiAnalyzer()
    except Exception as e:
        print(f"Note: Requires valid GEMINI_API_KEY: {e}")
        print("\nExample summary:")
        print("Patient complained about extended wait times and lack of communication.")
        return

    long_complaint = """
    I came to the clinic for my appointment and had to wait for over 2 hours.
    The staff didn't even acknowledge me or tell me how much longer the wait would be.
    When I finally saw the doctor, I was rushed through and didn't have time to ask
    my questions. The whole experience was very frustrating and I'm considering
    going to a different clinic next time.
    """

    print(f"\nOriginal complaint ({len(long_complaint)} chars):")
    print(long_complaint)

    result = analyzer.summarize_complaint(long_complaint, language="ru")

    print(f"\nSummary ({len(result.text)} chars):")
    print(result.text)
    if result.is_fallback:
        print(f"⚠️ (Fallback mode, error: {result.error})")


def example_caching():
    """Example: Classification caching behavior."""
    print("\n" + "=" * 60)
    print("Example: Caching and Performance")
    print("=" * 60)

    try:
        analyzer = GeminiAnalyzer(cache_ttl=3600)
    except Exception as e:
        print(f"Note: Requires valid GEMINI_API_KEY: {e}")
        print("\nCaching features:")
        print("- LRU cache keyed by message hash + language")
        print("- TTL configurable (default 3600 seconds)")
        print("- Automatic expiration and cleanup")
        print("- Reduces API calls for repeated messages")
        return

    message = "I need to reschedule my appointment"

    print(f"\nClassifying: '{message}'")
    print("First call...")
    result1 = analyzer.classify_request(message, language="ru")

    print("Second call (should use cache)...")
    result2 = analyzer.classify_request(message, language="ru")

    print(f"\nResults match: {result1.request_type == result2.request_type}")
    print(f"Cached size: {len(analyzer._classification_cache)} entries")

    analyzer.clear_cache()
    print(f"After clear: {len(analyzer._classification_cache)} entries")


def example_error_handling():
    """Example: Error handling and fallbacks."""
    print("\n" + "=" * 60)
    print("Example: Error Handling and Fallbacks")
    print("=" * 60)

    print("\nFallback behavior:")
    print("- API Timeouts: Cached fallback classification")
    print("- Network Errors: Fallback responses from locales")
    print("- Parse Errors: Safe default structures")
    print("\nError Notification:")
    print("- Admin alerts triggered on hard failures")
    print("- Error logged with full context")
    print("- User receives helpful fallback message")


if __name__ == "__main__":
    print("\n🤖 Gemini AI Service Examples\n")

    example_classifier()
    example_response_generation()
    example_complaint_summarization()
    example_caching()
    example_error_handling()

    print("\n" + "=" * 60)
    print("For more details, see:")
    print("- services/gemini/client.py (client configuration)")
    print("- services/gemini/analyzer.py (analysis functions)")
    print("- tests/test_gemini_*.py (comprehensive test examples)")
    print("=" * 60)
