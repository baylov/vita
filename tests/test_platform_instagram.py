"""Tests for Instagram platform adapter."""

import pytest
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.platform.instagram import InstagramAdapter
from integrations.platform.base import Message, MessageType, WebhookValidationError


@pytest.fixture
def instagram_adapter():
    """Create InstagramAdapter with test credentials."""
    return InstagramAdapter(
        page_access_token="test_page_token",
        app_secret="test_app_secret",
        verify_token="test_verify_token"
    )


@pytest.fixture
def instagram_adapter_no_creds():
    """Create InstagramAdapter without credentials."""
    return InstagramAdapter()


class TestInstagramSendMessage:
    """Tests for sending messages via Instagram."""
    
    @pytest.mark.asyncio
    async def test_send_text_message_success(self, instagram_adapter):
        """Test sending text message successfully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await instagram_adapter.send_message(
                recipient_id="123456789",
                text="Test message"
            )
            
            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "me/messages" in call_args[0][0]
            assert call_args[1]["json"]["message"]["text"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_send_message_not_available(self, instagram_adapter_no_creds):
        """Test sending message when adapter is not available."""
        result = await instagram_adapter_no_creds.send_message(
            recipient_id="123456789",
            text="Test message"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, instagram_adapter):
        """Test sending message with API error.
        
        Note: We patch _notify_admin_error to avoid complications with missing notifier.
        """
        with patch.object(instagram_adapter, '_notify_admin_error', new=AsyncMock()):
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
                
                result = await instagram_adapter.send_message(
                    recipient_id="123456789",
                    text="Test message"
                )
                
                assert result is False


class TestInstagramSendMedia:
    """Tests for sending media via Instagram."""
    
    @pytest.mark.asyncio
    async def test_send_image(self, instagram_adapter):
        """Test sending image."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await instagram_adapter.send_media(
                recipient_id="123456789",
                media_url="https://example.com/image.jpg",
                media_type="image"
            )
            
            assert result is True
            call_args = mock_client.post.call_args
            attachment = call_args[1]["json"]["message"]["attachment"]
            assert attachment["type"] == "image"
            assert attachment["payload"]["url"] == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_send_media_with_caption(self, instagram_adapter):
        """Test sending media with caption sends separate text message."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            with patch.object(instagram_adapter, "send_message") as mock_send:
                result = await instagram_adapter.send_media(
                    recipient_id="123456789",
                    media_url="https://example.com/image.jpg",
                    media_type="image",
                    caption="Test caption"
                )
                
                assert result is True
                mock_send.assert_called_once_with("123456789", "Test caption")


class TestInstagramSendTyping:
    """Tests for sending typing indicator via Instagram."""
    
    @pytest.mark.asyncio
    async def test_send_typing_success(self, instagram_adapter):
        """Test sending typing indicator successfully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await instagram_adapter.send_typing(recipient_id="123456789")
            
            assert result is True
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["sender_action"] == "typing_on"


class TestInstagramNotifyError:
    """Tests for sending error notifications via Instagram."""
    
    @pytest.mark.asyncio
    async def test_notify_error(self, instagram_adapter):
        """Test sending error notification."""
        with patch.object(instagram_adapter, "send_message", return_value=True) as mock_send:
            result = await instagram_adapter.notify_error(
                recipient_id="123456789",
                error_message="Test error"
            )
            
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "⚠️ Ошибка:" in call_args[0][1]


class TestInstagramParseWebhook:
    """Tests for parsing Instagram webhooks."""
    
    def test_parse_text_message(self, instagram_adapter):
        """Test parsing text message."""
        payload = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123456789"},
                    "message": {
                        "mid": "m_123",
                        "text": "Hello, world!"
                    },
                    "timestamp": 1609459200000
                }]
            }]
        }
        
        parsed = instagram_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.platform == "instagram"
        assert parsed.platform_user_id == "123456789"
        assert parsed.message_type == MessageType.TEXT
        assert parsed.text == "Hello, world!"
    
    def test_parse_image_message(self, instagram_adapter):
        """Test parsing image message."""
        payload = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123456789"},
                    "message": {
                        "mid": "m_123",
                        "attachments": [{
                            "type": "image",
                            "payload": {"url": "https://example.com/image.jpg"}
                        }]
                    },
                    "timestamp": 1609459200000
                }]
            }]
        }
        
        parsed = instagram_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.IMAGE
        assert parsed.media_url == "https://example.com/image.jpg"
        assert parsed.media_type == "image"
    
    def test_parse_video_message(self, instagram_adapter):
        """Test parsing video message."""
        payload = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123456789"},
                    "message": {
                        "mid": "m_123",
                        "attachments": [{
                            "type": "video",
                            "payload": {"url": "https://example.com/video.mp4"}
                        }]
                    }
                }]
            }]
        }
        
        parsed = instagram_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.VIDEO
        assert parsed.media_type == "video"
    
    def test_parse_audio_message(self, instagram_adapter):
        """Test parsing audio message."""
        payload = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123456789"},
                    "message": {
                        "mid": "m_123",
                        "attachments": [{
                            "type": "audio",
                            "payload": {"url": "https://example.com/audio.mp3"}
                        }]
                    }
                }]
            }]
        }
        
        parsed = instagram_adapter.parse_webhook(payload)
        
        assert parsed is not None
        assert parsed.message_type == MessageType.VOICE
        assert parsed.media_type == "audio"
    
    def test_parse_verification_challenge(self, instagram_adapter):
        """Test parsing webhook verification challenge."""
        payload = {"hub.challenge": "test_challenge"}
        
        parsed = instagram_adapter.parse_webhook(payload)
        
        assert parsed is None
    
    def test_parse_empty_webhook(self, instagram_adapter):
        """Test parsing empty webhook."""
        parsed = instagram_adapter.parse_webhook({"entry": []})
        
        assert parsed is None


class TestInstagramValidateWebhook:
    """Tests for validating Instagram webhooks."""
    
    def test_validate_webhook_success(self, instagram_adapter):
        """Test successful webhook validation."""
        payload = '{"test": "data"}'
        
        # Calculate expected signature
        expected_sig = hmac.new(
            "test_app_secret".encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_sig}"
        
        result = instagram_adapter.validate_webhook(payload, signature)
        
        assert result is True
    
    def test_validate_webhook_without_prefix(self, instagram_adapter):
        """Test webhook validation without sha256= prefix."""
        payload = '{"test": "data"}'
        
        expected_sig = hmac.new(
            "test_app_secret".encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        result = instagram_adapter.validate_webhook(payload, expected_sig)
        
        assert result is True
    
    def test_validate_webhook_invalid_signature(self, instagram_adapter):
        """Test webhook validation with invalid signature."""
        with pytest.raises(WebhookValidationError):
            instagram_adapter.validate_webhook(
                payload='{"test": "data"}',
                signature="sha256=invalid_signature"
            )
    
    def test_validate_webhook_no_app_secret(self, instagram_adapter_no_creds):
        """Test webhook validation without app secret."""
        result = instagram_adapter_no_creds.validate_webhook(
            payload={},
            signature="signature"
        )
        
        assert result is False


class TestInstagramVerifySubscription:
    """Tests for webhook subscription verification."""
    
    def test_verify_subscription_success(self, instagram_adapter):
        """Test successful subscription verification."""
        result = instagram_adapter.verify_webhook_subscription(
            mode="subscribe",
            token="test_verify_token",
            challenge="test_challenge"
        )
        
        assert result == "test_challenge"
    
    def test_verify_subscription_wrong_token(self, instagram_adapter):
        """Test subscription verification with wrong token."""
        result = instagram_adapter.verify_webhook_subscription(
            mode="subscribe",
            token="wrong_token",
            challenge="test_challenge"
        )
        
        assert result is None
    
    def test_verify_subscription_wrong_mode(self, instagram_adapter):
        """Test subscription verification with wrong mode."""
        result = instagram_adapter.verify_webhook_subscription(
            mode="unsubscribe",
            token="test_verify_token",
            challenge="test_challenge"
        )
        
        assert result is None


class TestInstagramIntegration:
    """Integration tests for Instagram adapter."""
    
    @pytest.mark.asyncio
    async def test_complete_send_flow(self, instagram_adapter):
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
            result1 = await instagram_adapter.send_message("123", "Text")
            assert result1 is True
            
            # Send typing
            result2 = await instagram_adapter.send_typing("123")
            assert result2 is True
            
            # Send image
            result3 = await instagram_adapter.send_media("123", "url", "image")
            assert result3 is True
            
            assert mock_client.post.call_count == 3
    
    def test_parse_multiple_message_types(self, instagram_adapter):
        """Test parsing multiple message types."""
        # Text
        msg1 = instagram_adapter.parse_webhook({
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123"},
                    "message": {"mid": "m1", "text": "Test"}
                }]
            }]
        })
        assert msg1.message_type == MessageType.TEXT
        
        # Image
        msg2 = instagram_adapter.parse_webhook({
            "entry": [{
                "messaging": [{
                    "sender": {"id": "123"},
                    "message": {
                        "mid": "m2",
                        "attachments": [{
                            "type": "image",
                            "payload": {"url": "url"}
                        }]
                    }
                }]
            }]
        })
        assert msg2.message_type == MessageType.IMAGE
