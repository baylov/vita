"""Tests for Telegram platform adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Update, Message as AiogramMessage, User, Chat, CallbackQuery

from integrations.platform.telegram import TelegramAdapter
from integrations.platform.base import Message, MessageType


@pytest.fixture
def mock_bot():
    """Create mock aiogram Bot."""
    bot = AsyncMock(spec=Bot)
    bot.send_message = AsyncMock(return_value=True)
    bot.send_photo = AsyncMock(return_value=True)
    bot.send_video = AsyncMock(return_value=True)
    bot.send_document = AsyncMock(return_value=True)
    bot.send_audio = AsyncMock(return_value=True)
    bot.send_chat_action = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def telegram_adapter(mock_bot):
    """Create TelegramAdapter with mock bot."""
    adapter = TelegramAdapter(bot=mock_bot)
    return adapter


@pytest.fixture
def mock_user():
    """Create mock Telegram user."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.first_name = "John"
    user.last_name = "Doe"
    user.username = "johndoe"
    user.language_code = "ru"
    return user


@pytest.fixture
def mock_chat():
    """Create mock Telegram chat."""
    chat = MagicMock(spec=Chat)
    chat.id = 123456789
    chat.type = "private"
    return chat


class TestTelegramSendMessage:
    """Tests for sending messages via Telegram."""
    
    @pytest.mark.asyncio
    async def test_send_text_message_success(self, telegram_adapter, mock_bot):
        """Test sending text message successfully."""
        result = await telegram_adapter.send_message(
            recipient_id="123456789",
            text="Test message"
        )
        
        assert result is True
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456789,
            text="Test message"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_with_kwargs(self, telegram_adapter, mock_bot):
        """Test sending message with additional kwargs."""
        result = await telegram_adapter.send_message(
            recipient_id="123456789",
            text="Test message",
            parse_mode="HTML"
        )
        
        assert result is True
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456789,
            text="Test message",
            parse_mode="HTML"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_invalid_recipient_id(self, telegram_adapter, mock_bot):
        """Test sending message with invalid recipient ID."""
        result = await telegram_adapter.send_message(
            recipient_id="invalid",
            text="Test message"
        )
        
        assert result is False
        mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_message_bot_not_configured(self):
        """Test sending message when bot is not configured."""
        adapter = TelegramAdapter(bot=None)
        result = await adapter.send_message(
            recipient_id="123456789",
            text="Test message"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, telegram_adapter, mock_bot):
        """Test sending message with API error."""
        mock_bot.send_message.side_effect = Exception("API error")
        
        result = await telegram_adapter.send_message(
            recipient_id="123456789",
            text="Test message"
        )
        
        assert result is False


class TestTelegramSendMedia:
    """Tests for sending media via Telegram."""
    
    @pytest.mark.asyncio
    async def test_send_image(self, telegram_adapter, mock_bot):
        """Test sending image."""
        result = await telegram_adapter.send_media(
            recipient_id="123456789",
            media_url="https://example.com/image.jpg",
            media_type="image",
            caption="Test caption"
        )
        
        assert result is True
        mock_bot.send_photo.assert_called_once_with(
            chat_id=123456789,
            photo="https://example.com/image.jpg",
            caption="Test caption"
        )
    
    @pytest.mark.asyncio
    async def test_send_video(self, telegram_adapter, mock_bot):
        """Test sending video."""
        result = await telegram_adapter.send_media(
            recipient_id="123456789",
            media_url="https://example.com/video.mp4",
            media_type="video"
        )
        
        assert result is True
        mock_bot.send_video.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_document(self, telegram_adapter, mock_bot):
        """Test sending document."""
        result = await telegram_adapter.send_media(
            recipient_id="123456789",
            media_url="https://example.com/file.pdf",
            media_type="document"
        )
        
        assert result is True
        mock_bot.send_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_audio(self, telegram_adapter, mock_bot):
        """Test sending audio."""
        result = await telegram_adapter.send_media(
            recipient_id="123456789",
            media_url="https://example.com/audio.mp3",
            media_type="audio"
        )
        
        assert result is True
        mock_bot.send_audio.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_unsupported_media_type(self, telegram_adapter, mock_bot):
        """Test sending unsupported media type."""
        result = await telegram_adapter.send_media(
            recipient_id="123456789",
            media_url="https://example.com/file",
            media_type="unknown"
        )
        
        assert result is False


class TestTelegramSendTyping:
    """Tests for sending typing indicator via Telegram."""
    
    @pytest.mark.asyncio
    async def test_send_typing_success(self, telegram_adapter, mock_bot):
        """Test sending typing indicator successfully."""
        result = await telegram_adapter.send_typing(recipient_id="123456789")
        
        assert result is True
        mock_bot.send_chat_action.assert_called_once_with(
            chat_id=123456789,
            action="typing"
        )


class TestTelegramNotifyError:
    """Tests for sending error notifications via Telegram."""
    
    @pytest.mark.asyncio
    async def test_notify_error(self, telegram_adapter, mock_bot):
        """Test sending error notification."""
        result = await telegram_adapter.notify_error(
            recipient_id="123456789",
            error_message="Test error"
        )
        
        assert result is True
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "⚠️ Ошибка:" in call_args[1]["text"]


class TestTelegramParseWebhook:
    """Tests for parsing Telegram webhooks."""
    
    def test_parse_text_message(self, telegram_adapter, mock_user, mock_chat):
        """Test parsing text message."""
        message = AiogramMessage(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=mock_chat,
            from_user=mock_user,
            text="Hello, world!"
        )
        
        parsed = telegram_adapter.parse_webhook(message)
        
        assert parsed is not None
        assert parsed.platform == "telegram"
        assert parsed.platform_user_id == "123456789"
        assert parsed.message_type == MessageType.TEXT
        assert parsed.text == "Hello, world!"
        assert parsed.first_name == "John"
        assert parsed.last_name == "Doe"
        assert parsed.username == "johndoe"
    
    def test_parse_voice_message(self, telegram_adapter, mock_user, mock_chat):
        """Test parsing voice message."""
        from aiogram.types import Voice
        
        voice = Voice(
            file_id="voice_file_id_123",
            file_unique_id="unique_123",
            duration=10
        )
        
        message = AiogramMessage(
            message_id=2,
            date=datetime.now(timezone.utc),
            chat=mock_chat,
            from_user=mock_user,
            voice=voice
        )
        
        parsed = telegram_adapter.parse_webhook(message)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.VOICE
        assert parsed.media_url == "voice_file_id_123"
        assert parsed.media_type == "voice"
        assert parsed.text is None
    
    def test_parse_photo_message(self, telegram_adapter, mock_user, mock_chat):
        """Test parsing photo message."""
        from aiogram.types import PhotoSize
        
        photo = PhotoSize(
            file_id="photo_file_id_123",
            file_unique_id="unique_123",
            width=100,
            height=100
        )
        
        message = AiogramMessage(
            message_id=3,
            date=datetime.now(timezone.utc),
            chat=mock_chat,
            from_user=mock_user,
            photo=[photo],
            caption="Photo caption"
        )
        
        parsed = telegram_adapter.parse_webhook(message)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.IMAGE
        assert parsed.media_url == "photo_file_id_123"
        assert parsed.text == "Photo caption"
    
    def test_parse_callback_query(self, telegram_adapter, mock_user):
        """Test parsing callback query."""
        callback_query = CallbackQuery(
            id="callback_123",
            from_user=mock_user,
            chat_instance="instance_123",
            data="button_data"
        )
        
        parsed = telegram_adapter.parse_webhook(callback_query)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.CALLBACK
        assert parsed.callback_data == "button_data"
        assert parsed.platform_user_id == "123456789"
    
    def test_parse_invalid_webhook(self, telegram_adapter):
        """Test parsing invalid webhook data."""
        parsed = telegram_adapter.parse_webhook({"invalid": "data"})
        
        assert parsed is None


class TestTelegramValidateWebhook:
    """Tests for validating Telegram webhooks."""
    
    def test_validate_webhook_always_true(self, telegram_adapter):
        """Test that Telegram webhook validation always returns True."""
        result = telegram_adapter.validate_webhook(
            payload={},
            signature="not_used"
        )
        
        assert result is True


class TestTelegramIntegration:
    """Integration tests for Telegram adapter."""
    
    @pytest.mark.asyncio
    async def test_complete_send_flow(self, telegram_adapter, mock_bot):
        """Test complete send flow with multiple message types."""
        # Send text message
        result1 = await telegram_adapter.send_message("123", "Text")
        assert result1 is True
        
        # Send typing indicator
        result2 = await telegram_adapter.send_typing("123")
        assert result2 is True
        
        # Send image
        result3 = await telegram_adapter.send_media("123", "url", "image")
        assert result3 is True
        
        # Verify all calls made
        assert mock_bot.send_message.call_count == 1
        assert mock_bot.send_chat_action.call_count == 1
        assert mock_bot.send_photo.call_count == 1
    
    def test_parse_multiple_message_types(self, telegram_adapter, mock_user, mock_chat):
        """Test parsing multiple message types."""
        from aiogram.types import Voice
        
        # Text message
        msg1 = AiogramMessage(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=mock_chat,
            from_user=mock_user,
            text="Test"
        )
        parsed1 = telegram_adapter.parse_webhook(msg1)
        assert parsed1.message_type == MessageType.TEXT
        
        # Voice message
        voice = Voice(
            file_id="voice_123",
            file_unique_id="unique_123",
            duration=10
        )
        msg2 = AiogramMessage(
            message_id=2,
            date=datetime.now(timezone.utc),
            chat=mock_chat,
            from_user=mock_user,
            voice=voice
        )
        parsed2 = telegram_adapter.parse_webhook(msg2)
        assert parsed2.message_type == MessageType.VOICE
