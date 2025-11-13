"""Tests for WhatsApp platform adapter."""

import pytest
import base64
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.platform_handlers.whatsapp import WhatsAppAdapter
from integrations.platform_handlers.base import Message, MessageType, WebhookValidationError


@pytest.fixture
def whatsapp_adapter():
    """Create WhatsAppAdapter with test credentials."""
    return WhatsAppAdapter(
        account_sid="test_account_sid",
        auth_token="test_auth_token",
        from_number="whatsapp:+1234567890"
    )


@pytest.fixture
def whatsapp_adapter_no_creds():
    """Create WhatsAppAdapter without credentials."""
    return WhatsAppAdapter()


class TestWhatsAppSendMessage:
    """Tests for sending messages via WhatsApp."""
    
    @pytest.mark.asyncio
    async def test_send_text_message_success(self, whatsapp_adapter):
        """Test sending text message successfully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await whatsapp_adapter.send_message(
                recipient_id="whatsapp:+9876543210",
                text="Test message"
            )
            
            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "Messages.json" in call_args[0][0]
            assert call_args[1]["data"]["Body"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_send_message_adds_whatsapp_prefix(self, whatsapp_adapter):
        """Test that whatsapp: prefix is added if missing."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await whatsapp_adapter.send_message(
                recipient_id="+9876543210",
                text="Test message"
            )
            
            assert result is True
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["To"] == "whatsapp:+9876543210"
    
    @pytest.mark.asyncio
    async def test_send_message_not_available(self, whatsapp_adapter_no_creds):
        """Test sending message when adapter is not available."""
        result = await whatsapp_adapter_no_creds.send_message(
            recipient_id="whatsapp:+9876543210",
            text="Test message"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, whatsapp_adapter):
        """Test sending message with API error.
        
        Note: We patch _notify_admin_error to avoid complications with missing notifier.
        """
        with patch.object(whatsapp_adapter, '_notify_admin_error', new=AsyncMock()):
            with patch("httpx.AsyncClient") as mock_client_class:
                import httpx
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "Bad Request"
                
                # Create a proper async context manager that raises on post
                async def failing_post(*args, **kwargs):
                    raise httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=mock_response)
                
                mock_client = MagicMock()
                mock_client.post = failing_post
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client
                
                result = await whatsapp_adapter.send_message(
                    recipient_id="whatsapp:+9876543210",
                    text="Test message"
                )
                
                assert result is False


class TestWhatsAppSendMedia:
    """Tests for sending media via WhatsApp."""
    
    @pytest.mark.asyncio
    async def test_send_media_success(self, whatsapp_adapter):
        """Test sending media successfully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await whatsapp_adapter.send_media(
                recipient_id="whatsapp:+9876543210",
                media_url="https://example.com/image.jpg",
                media_type="image",
                caption="Test caption"
            )
            
            assert result is True
            call_args = mock_client.post.call_args
            assert call_args[1]["data"]["MediaUrl"] == "https://example.com/image.jpg"
            assert call_args[1]["data"]["Body"] == "Test caption"


class TestWhatsAppSendTyping:
    """Tests for sending typing indicator via WhatsApp."""
    
    @pytest.mark.asyncio
    async def test_send_typing_noop(self, whatsapp_adapter):
        """Test that typing indicator is a no-op for WhatsApp."""
        result = await whatsapp_adapter.send_typing(recipient_id="whatsapp:+9876543210")
        
        assert result is True


class TestWhatsAppNotifyError:
    """Tests for sending error notifications via WhatsApp."""
    
    @pytest.mark.asyncio
    async def test_notify_error(self, whatsapp_adapter):
        """Test sending error notification."""
        with patch.object(whatsapp_adapter, "send_message", return_value=True) as mock_send:
            result = await whatsapp_adapter.notify_error(
                recipient_id="whatsapp:+9876543210",
                error_message="Test error"
            )
            
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "⚠️ Ошибка:" in call_args[0][1]


class TestWhatsAppParseWebhook:
    """Tests for parsing WhatsApp webhooks."""
    
    def test_parse_text_message(self, whatsapp_adapter):
        """Test parsing text message."""
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "Body": "Hello, world!",
            "ProfileName": "John Doe"
        }
        
        parsed = whatsapp_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.platform == "whatsapp"
        assert parsed.platform_user_id == "+9876543210"
        assert parsed.message_type == MessageType.TEXT
        assert parsed.text == "Hello, world!"
        assert parsed.first_name == "John Doe"
    
    def test_parse_image_message(self, whatsapp_adapter):
        """Test parsing image message."""
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "Body": "Caption",
            "MediaUrl0": "https://example.com/image.jpg",
            "MediaContentType0": "image/jpeg",
            "ProfileName": "John Doe"
        }
        
        parsed = whatsapp_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.IMAGE
        assert parsed.media_url == "https://example.com/image.jpg"
        assert parsed.media_type == "image"
        assert parsed.text == "Caption"
    
    def test_parse_video_message(self, whatsapp_adapter):
        """Test parsing video message."""
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "MediaUrl0": "https://example.com/video.mp4",
            "MediaContentType0": "video/mp4"
        }
        
        parsed = whatsapp_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.VIDEO
        assert parsed.media_type == "video"
    
    def test_parse_audio_message(self, whatsapp_adapter):
        """Test parsing audio message."""
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "MediaUrl0": "https://example.com/audio.ogg",
            "MediaContentType0": "audio/ogg"
        }
        
        parsed = whatsapp_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.VOICE
        assert parsed.media_type == "voice"
    
    def test_parse_document_message(self, whatsapp_adapter):
        """Test parsing document message."""
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "MediaUrl0": "https://example.com/file.pdf",
            "MediaContentType0": "application/pdf"
        }
        
        parsed = whatsapp_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.DOCUMENT
        assert parsed.media_type == "document"
    
    def test_parse_invalid_webhook(self, whatsapp_adapter):
        """Test parsing invalid webhook data."""
        parsed = whatsapp_adapter.parse_webhook({})
        
        assert parsed is not None  # Should still create message with empty fields


class TestWhatsAppValidateWebhook:
    """Tests for validating WhatsApp webhooks."""
    
    def test_validate_webhook_success(self, whatsapp_adapter):
        """Test successful webhook validation."""
        url = "https://example.com/webhook"
        payload = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+9876543210",
            "Body": "Test"
        }
        
        # Calculate expected signature
        sorted_params = sorted(payload.items())
        data_string = url + "".join([f"{k}{v}" for k, v in sorted_params])
        expected_sig = hmac.new(
            "test_auth_token".encode("utf-8"),
            data_string.encode("utf-8"),
            hashlib.sha1
        ).digest()
        signature = base64.b64encode(expected_sig).decode("utf-8")
        
        result = whatsapp_adapter.validate_webhook(payload, signature, url=url)
        
        assert result is True
    
    def test_validate_webhook_invalid_signature(self, whatsapp_adapter):
        """Test webhook validation with invalid signature."""
        with pytest.raises(WebhookValidationError):
            whatsapp_adapter.validate_webhook(
                payload={"test": "data"},
                signature="invalid_signature",
                url="https://example.com/webhook"
            )
    
    def test_validate_webhook_no_auth_token(self, whatsapp_adapter_no_creds):
        """Test webhook validation without auth token."""
        result = whatsapp_adapter_no_creds.validate_webhook(
            payload={},
            signature="signature",
            url="https://example.com/webhook"
        )
        
        assert result is False


class TestWhatsAppIntegration:
    """Integration tests for WhatsApp adapter."""
    
    @pytest.mark.asyncio
    async def test_complete_send_flow(self, whatsapp_adapter):
        """Test complete send flow."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Send text
            result1 = await whatsapp_adapter.send_message("+123", "Text")
            assert result1 is True
            
            # Send media
            result2 = await whatsapp_adapter.send_media("+123", "url", "image")
            assert result2 is True
            
            # Send typing (no-op)
            result3 = await whatsapp_adapter.send_typing("+123")
            assert result3 is True
            
            assert mock_client.post.call_count == 2  # Text + Media
    
    def test_parse_multiple_message_types(self, whatsapp_adapter):
        """Test parsing multiple message types."""
        # Text
        msg1 = whatsapp_adapter.parse_webhook({
            "MessageSid": "1",
            "From": "whatsapp:+123",
            "Body": "Test"
        })
        assert msg1.message_type == MessageType.TEXT
        
        # Image
        msg2 = whatsapp_adapter.parse_webhook({
            "MessageSid": "2",
            "From": "whatsapp:+123",
            "MediaUrl0": "url",
            "MediaContentType0": "image/jpeg"
        })
        assert msg2.message_type == MessageType.IMAGE
