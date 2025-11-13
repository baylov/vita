"""Examples of using platform adapters for unified messaging."""

import asyncio
from aiogram import Bot
from integrations.platform_handlers import (
    Message,
    MessageType,
    TelegramAdapter,
    WhatsAppAdapter,
    InstagramAdapter,
    MessageRouter,
)
from settings import settings


async def example_telegram_adapter():
    """Example: Using TelegramAdapter."""
    print("=== Telegram Adapter Example ===\n")
    
    # Initialize bot and adapter
    bot = Bot(token=settings.telegram_bot_token or "fake_token")
    adapter = TelegramAdapter(bot=bot)
    
    # Send text message
    print("Sending text message...")
    await adapter.send_message(
        recipient_id="123456789",
        text="Hello from Telegram adapter!"
    )
    
    # Send typing indicator
    print("Sending typing indicator...")
    await adapter.send_typing(recipient_id="123456789")
    
    # Send image
    print("Sending image...")
    await adapter.send_media(
        recipient_id="123456789",
        media_url="https://example.com/image.jpg",
        media_type="image",
        caption="Check out this image!"
    )
    
    # Parse incoming webhook (Update object)
    print("\nParsing incoming message...")
    # In production, this would be an actual Update object from aiogram
    # Here we're just showing the structure
    from aiogram.types import Update, Message as AiogramMessage, User, Chat
    from datetime import datetime, timezone
    
    mock_user = User(id=123456789, is_bot=False, first_name="John")
    mock_chat = Chat(id=123456789, type="private")
    mock_message = AiogramMessage(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=mock_chat,
        from_user=mock_user,
        text="Hello!"
    )
    
    parsed = adapter.parse_webhook(mock_message)
    print(f"Parsed message: {parsed.text} from {parsed.get_full_name()}")
    
    await bot.session.close()


async def example_whatsapp_adapter():
    """Example: Using WhatsAppAdapter."""
    print("\n=== WhatsApp Adapter Example ===\n")
    
    # Initialize adapter
    adapter = WhatsAppAdapter(
        account_sid=settings.whatsapp_account_sid or "fake_sid",
        auth_token=settings.whatsapp_auth_token or "fake_token",
        from_number=settings.whatsapp_from_number or "whatsapp:+1234567890"
    )
    
    # Note: WhatsApp adapter requires valid Twilio credentials to work
    if not adapter.is_available:
        print("WhatsApp adapter not available (credentials not configured)")
        return
    
    # Send text message
    print("Sending text message...")
    await adapter.send_message(
        recipient_id="whatsapp:+9876543210",
        text="Hello from WhatsApp adapter!"
    )
    
    # Send media
    print("Sending media...")
    await adapter.send_media(
        recipient_id="whatsapp:+9876543210",
        media_url="https://example.com/document.pdf",
        media_type="document",
        caption="Here's your document"
    )
    
    # Parse incoming webhook
    print("\nParsing incoming webhook...")
    webhook_payload = {
        "MessageSid": "SM123456",
        "From": "whatsapp:+9876543210",
        "Body": "Hello from WhatsApp!",
        "ProfileName": "John Doe"
    }
    
    parsed = adapter.parse_webhook(webhook_payload)
    print(f"Parsed message: {parsed.text} from {parsed.get_full_name()}")
    
    # Validate webhook signature
    print("\nValidating webhook signature...")
    # In production, these would come from the webhook request
    url = "https://example.com/webhook"
    signature = "test_signature"
    try:
        is_valid = adapter.validate_webhook(webhook_payload, signature, url=url)
        print(f"Webhook valid: {is_valid}")
    except Exception as e:
        print(f"Webhook validation error: {e}")


async def example_instagram_adapter():
    """Example: Using InstagramAdapter."""
    print("\n=== Instagram Adapter Example ===\n")
    
    # Initialize adapter
    adapter = InstagramAdapter(
        page_access_token=settings.instagram_page_access_token or "fake_token",
        app_secret=settings.instagram_app_secret or "fake_secret",
        verify_token=settings.instagram_verify_token or "fake_verify_token"
    )
    
    if not adapter.is_available:
        print("Instagram adapter not available (credentials not configured)")
        return
    
    # Send text message
    print("Sending text message...")
    await adapter.send_message(
        recipient_id="123456789",
        text="Hello from Instagram adapter!"
    )
    
    # Send typing indicator
    print("Sending typing indicator...")
    await adapter.send_typing(recipient_id="123456789")
    
    # Send image
    print("Sending image...")
    await adapter.send_media(
        recipient_id="123456789",
        media_url="https://example.com/image.jpg",
        media_type="image",
        caption="Check this out!"
    )
    
    # Parse incoming webhook
    print("\nParsing incoming webhook...")
    webhook_payload = {
        "entry": [{
            "messaging": [{
                "sender": {"id": "123456789"},
                "message": {
                    "mid": "m_123",
                    "text": "Hello from Instagram!"
                },
                "timestamp": 1609459200000
            }]
        }]
    }
    
    parsed = adapter.parse_webhook(webhook_payload)
    if parsed:
        print(f"Parsed message: {parsed.text} from user {parsed.platform_user_id}")
    
    # Handle webhook verification
    print("\nHandling webhook verification...")
    challenge = adapter.verify_webhook_subscription(
        mode="subscribe",
        token=adapter.verify_token,
        challenge="test_challenge_123"
    )
    print(f"Verification challenge: {challenge}")


async def example_message_router():
    """Example: Using MessageRouter for unified message handling."""
    print("\n=== Message Router Example ===\n")
    
    # Initialize adapters
    bot = Bot(token=settings.telegram_bot_token or "fake_token")
    telegram_adapter = TelegramAdapter(bot=bot)
    whatsapp_adapter = WhatsAppAdapter(
        account_sid=settings.whatsapp_account_sid or "fake_sid",
        auth_token=settings.whatsapp_auth_token or "fake_token",
        from_number=settings.whatsapp_from_number or "whatsapp:+1234567890"
    )
    instagram_adapter = InstagramAdapter(
        page_access_token=settings.instagram_page_access_token or "fake_token",
        app_secret=settings.instagram_app_secret or "fake_secret"
    )
    
    # Create router
    router = MessageRouter(
        adapters={
            "telegram": telegram_adapter,
            "whatsapp": whatsapp_adapter,
            "instagram": instagram_adapter,
        }
    )
    
    print(f"Router initialized with {len(router.adapters)} adapters")
    
    # Define message handler
    async def handle_message(message: Message, context):
        """Handle incoming message."""
        print(f"\nHandling message from {message.platform}:")
        print(f"  User: {message.get_full_name()}")
        print(f"  Text: {message.text}")
        print(f"  Conversation state: {context.current_state}")
    
    # Route Telegram message
    print("\n1. Routing Telegram message...")
    telegram_message = Message(
        message_id="1",
        platform="telegram",
        platform_user_id="123456789",
        message_type=MessageType.TEXT,
        text="Hello from Telegram!",
        first_name="John",
        last_name="Doe"
    )
    
    context = await router.route_message(telegram_message, handler=handle_message)
    print(f"   Created context for user {context.user_id}")
    
    # Route WhatsApp message from same user (different platform)
    print("\n2. Routing WhatsApp message from same user...")
    whatsapp_message = Message(
        message_id="2",
        platform="whatsapp",
        platform_user_id="+9876543210",
        internal_user_id=context.user_id,  # Same user, different platform
        message_type=MessageType.TEXT,
        text="Hello from WhatsApp!"
    )
    
    await router.route_message(whatsapp_message, handler=handle_message)
    
    # Send reply to user (automatically uses their preferred platform)
    print("\n3. Sending reply to user...")
    await router.send_to_user(
        internal_user_id=context.user_id,
        text="Thanks for your message!"
    )
    
    # Parse and route webhook directly
    print("\n4. Parsing and routing webhook...")
    webhook_payload = {
        "entry": [{
            "messaging": [{
                "sender": {"id": "987654321"},
                "message": {
                    "mid": "m_123",
                    "text": "Instagram message"
                }
            }]
        }]
    }
    
    await router.parse_and_route(
        platform="instagram",
        payload=webhook_payload,
        handler=handle_message
    )
    
    await bot.session.close()


async def example_error_handling():
    """Example: Error handling with adapters."""
    print("\n=== Error Handling Example ===\n")
    
    # Initialize adapter
    bot = Bot(token=settings.telegram_bot_token or "fake_token")
    adapter = TelegramAdapter(bot=bot)
    
    # Send error notification
    print("Sending error notification...")
    await adapter.notify_error(
        recipient_id="123456789",
        error_message="Something went wrong with your booking"
    )
    
    # Handle send failure
    print("\nHandling send failure...")
    result = await adapter.send_message(
        recipient_id="invalid_id",
        text="This will fail"
    )
    
    if not result:
        print("Message send failed - adapter returned False")
        # In production, this would trigger admin notification via Notifier
    
    await bot.session.close()


async def example_custom_user_mapper():
    """Example: Custom user ID mapper for MessageRouter."""
    print("\n=== Custom User Mapper Example ===\n")
    
    # Define custom mapper that looks up users in database
    async def database_user_mapper(platform: str, platform_user_id: str) -> int:
        """Map platform user ID to internal user ID via database lookup."""
        # In production, this would query the database
        # For example: user = await db.users.find_one({"platform": platform, "platform_user_id": platform_user_id})
        # For demo, we'll just hash it consistently
        import hashlib
        hash_input = f"{platform}:{platform_user_id}"
        user_id = int(hashlib.sha256(hash_input.encode()).hexdigest()[:8], 16)
        print(f"Mapped {platform}:{platform_user_id} -> internal ID {user_id}")
        return user_id
    
    # Create router with custom mapper
    router = MessageRouter(user_id_mapper=database_user_mapper)
    
    # Register adapters
    bot = Bot(token=settings.telegram_bot_token or "fake_token")
    router.register_adapter("telegram", TelegramAdapter(bot=bot))
    
    # Route message - will use custom mapper
    message = Message(
        message_id="1",
        platform="telegram",
        platform_user_id="123456789",
        message_type=MessageType.TEXT,
        text="Test"
    )
    
    context = await router.route_message(message)
    print(f"User context created with ID: {context.user_id}")
    
    await bot.session.close()


async def main():
    """Run all examples."""
    print("Platform Adapters Examples")
    print("=" * 60)
    
    await example_telegram_adapter()
    await example_whatsapp_adapter()
    await example_instagram_adapter()
    await example_message_router()
    await example_error_handling()
    await example_custom_user_mapper()
    
    print("\n" + "=" * 60)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
