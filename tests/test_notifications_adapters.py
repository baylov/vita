"""Tests for notification adapters."""

import pytest
from datetime import datetime, timezone

from services.notifications.adapters import (
    TelegramAdapter,
    WhatsAppAdapter,
    InstagramAdapter,
)


class TestTelegramAdapter:
    """Tests for TelegramAdapter."""

    def test_telegram_adapter_creation(self):
        """Test creating Telegram adapter."""
        adapter = TelegramAdapter()

        assert adapter.channel_name == "telegram"
        assert adapter.is_available is True
        assert adapter.mock_mode is False

    def test_telegram_adapter_enable_mock_mode(self):
        """Test enabling mock mode."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        assert adapter.mock_mode is True

    @pytest.mark.asyncio
    async def test_telegram_send_success(self):
        """Test successful Telegram send."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        result = await adapter.send(123, "Test message")

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["recipient_id"] == 123
        assert messages[0]["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_telegram_send_with_subject(self):
        """Test Telegram send with subject."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        result = await adapter.send(123, "Test message", subject="test_subject")

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_telegram_send_invalid_recipient(self):
        """Test Telegram send with invalid recipient."""
        adapter = TelegramAdapter()

        result = await adapter.send(-1, "Test message")

        assert result is False

    def test_telegram_validate_recipient_valid(self):
        """Test validating valid Telegram recipient."""
        adapter = TelegramAdapter()

        assert adapter.validate_recipient(123) is True
        assert adapter.validate_recipient(999999) is True

    def test_telegram_validate_recipient_invalid(self):
        """Test validating invalid Telegram recipient."""
        adapter = TelegramAdapter()

        assert adapter.validate_recipient(-1) is False
        assert adapter.validate_recipient(0) is False
        assert adapter.validate_recipient("123") is False

    def test_telegram_get_sent_messages(self):
        """Test getting sent messages."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message 1"))
        asyncio.run(adapter.send(456, "Message 2"))

        messages = adapter.get_sent_messages()
        assert len(messages) == 2

    def test_telegram_clear_sent_messages(self):
        """Test clearing sent messages."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        adapter.clear_sent_messages()

        assert len(adapter.get_sent_messages()) == 0


class TestWhatsAppAdapter:
    """Tests for WhatsAppAdapter."""

    def test_whatsapp_adapter_creation(self):
        """Test creating WhatsApp adapter."""
        adapter = WhatsAppAdapter()

        assert adapter.channel_name == "whatsapp"
        assert adapter.is_available is True
        assert adapter.mock_mode is False

    def test_whatsapp_adapter_enable_mock_mode(self):
        """Test enabling mock mode."""
        adapter = WhatsAppAdapter()
        adapter.enable_mock_mode()

        assert adapter.mock_mode is True

    @pytest.mark.asyncio
    async def test_whatsapp_send_success(self):
        """Test successful WhatsApp send."""
        adapter = WhatsAppAdapter()
        adapter.enable_mock_mode()

        result = await adapter.send(123, "Test message")

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["recipient_id"] == 123

    @pytest.mark.asyncio
    async def test_whatsapp_send_invalid_recipient(self):
        """Test WhatsApp send with invalid recipient."""
        adapter = WhatsAppAdapter()

        result = await adapter.send(-1, "Test message")

        assert result is False

    def test_whatsapp_validate_recipient_valid(self):
        """Test validating valid WhatsApp recipient."""
        adapter = WhatsAppAdapter()

        assert adapter.validate_recipient(123) is True

    def test_whatsapp_validate_recipient_invalid(self):
        """Test validating invalid WhatsApp recipient."""
        adapter = WhatsAppAdapter()

        assert adapter.validate_recipient(-1) is False
        assert adapter.validate_recipient(0) is False

    def test_whatsapp_get_sent_messages(self):
        """Test getting sent messages."""
        adapter = WhatsAppAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message 1"))
        asyncio.run(adapter.send(456, "Message 2"))

        messages = adapter.get_sent_messages()
        assert len(messages) == 2

    def test_whatsapp_clear_sent_messages(self):
        """Test clearing sent messages."""
        adapter = WhatsAppAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        adapter.clear_sent_messages()

        assert len(adapter.get_sent_messages()) == 0


class TestInstagramAdapter:
    """Tests for InstagramAdapter."""

    def test_instagram_adapter_creation(self):
        """Test creating Instagram adapter."""
        adapter = InstagramAdapter()

        assert adapter.channel_name == "instagram"
        assert adapter.is_available is True
        assert adapter.mock_mode is False

    def test_instagram_adapter_enable_mock_mode(self):
        """Test enabling mock mode."""
        adapter = InstagramAdapter()
        adapter.enable_mock_mode()

        assert adapter.mock_mode is True

    @pytest.mark.asyncio
    async def test_instagram_send_success(self):
        """Test successful Instagram send."""
        adapter = InstagramAdapter()
        adapter.enable_mock_mode()

        result = await adapter.send(123, "Test message")

        assert result is True
        messages = adapter.get_sent_messages()
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_instagram_send_invalid_recipient(self):
        """Test Instagram send with invalid recipient."""
        adapter = InstagramAdapter()

        result = await adapter.send(-1, "Test message")

        assert result is False

    def test_instagram_validate_recipient_valid(self):
        """Test validating valid Instagram recipient."""
        adapter = InstagramAdapter()

        assert adapter.validate_recipient(123) is True

    def test_instagram_validate_recipient_invalid(self):
        """Test validating invalid Instagram recipient."""
        adapter = InstagramAdapter()

        assert adapter.validate_recipient(-1) is False

    def test_instagram_get_sent_messages(self):
        """Test getting sent messages."""
        adapter = InstagramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message 1"))
        asyncio.run(adapter.send(456, "Message 2"))

        messages = adapter.get_sent_messages()
        assert len(messages) == 2

    def test_instagram_clear_sent_messages(self):
        """Test clearing sent messages."""
        adapter = InstagramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        adapter.clear_sent_messages()

        assert len(adapter.get_sent_messages()) == 0


class TestAdapterTimestamps:
    """Tests for adapter message timestamps."""

    def test_telegram_message_timestamp(self):
        """Test Telegram message includes timestamp."""
        adapter = TelegramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        messages = adapter.get_sent_messages()
        assert "timestamp" in messages[0]
        assert isinstance(messages[0]["timestamp"], datetime)

    def test_whatsapp_message_timestamp(self):
        """Test WhatsApp message includes timestamp."""
        adapter = WhatsAppAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        messages = adapter.get_sent_messages()
        assert "timestamp" in messages[0]
        assert isinstance(messages[0]["timestamp"], datetime)

    def test_instagram_message_timestamp(self):
        """Test Instagram message includes timestamp."""
        adapter = InstagramAdapter()
        adapter.enable_mock_mode()

        import asyncio

        asyncio.run(adapter.send(123, "Message"))

        messages = adapter.get_sent_messages()
        assert "timestamp" in messages[0]
        assert isinstance(messages[0]["timestamp"], datetime)
