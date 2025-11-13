"""WhatsApp platform adapter using Twilio API."""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from integrations.platform_handlers.base import (
    PlatformAdapter,
    Message,
    MessageType,
    WebhookValidationError,
)
from services.notifications.notifier import Notifier, NotificationEvent

logger = logging.getLogger(__name__)


class WhatsAppAdapter(PlatformAdapter):
    """WhatsApp platform adapter using Twilio API."""
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        notifier: Optional[Notifier] = None,
    ):
        """Initialize WhatsApp adapter.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: WhatsApp-enabled Twilio number (format: whatsapp:+1234567890)
            notifier: Notifier instance for admin alerts
        """
        super().__init__("whatsapp")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.notifier = notifier
        self.api_base = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"
        
        if not all([account_sid, auth_token, from_number]):
            logger.warning("WhatsApp adapter initialized without credentials")
            self.is_available = False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError, httpx.HTTPError)),
    )
    async def send_message(
        self,
        recipient_id: str,
        text: str,
        **kwargs
    ) -> bool:
        """Send text message via WhatsApp.
        
        Args:
            recipient_id: WhatsApp phone number (format: whatsapp:+1234567890)
            text: Message text
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available:
            logger.error("WhatsApp adapter not available")
            return False
        
        try:
            # Ensure recipient_id has whatsapp: prefix
            to_number = recipient_id if recipient_id.startswith("whatsapp:") else f"whatsapp:{recipient_id}"
            
            url = f"{self.api_base}/Messages.json"
            data = {
                "From": self.from_number,
                "To": to_number,
                "Body": text,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                )
                response.raise_for_status()
            
            logger.debug(f"Sent WhatsApp message to {recipient_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.status_code} - {e.response.text}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {recipient_id}: {e}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((OSError, ConnectionError, httpx.HTTPError)),
    )
    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send media message via WhatsApp.
        
        Args:
            recipient_id: WhatsApp phone number
            media_url: Public URL to media file
            media_type: Type of media (image, video, document, audio)
            caption: Optional caption
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available:
            logger.error("WhatsApp adapter not available")
            return False
        
        try:
            to_number = recipient_id if recipient_id.startswith("whatsapp:") else f"whatsapp:{recipient_id}"
            
            url = f"{self.api_base}/Messages.json"
            data = {
                "From": self.from_number,
                "To": to_number,
                "MediaUrl": media_url,
            }
            
            if caption:
                data["Body"] = caption
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                )
                response.raise_for_status()
            
            logger.debug(f"Sent WhatsApp {media_type} to {recipient_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.status_code} - {e.response.text}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp media to {recipient_id}: {e}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
    
    async def send_typing(
        self,
        recipient_id: str,
        **kwargs
    ) -> bool:
        """Send typing indicator via WhatsApp.
        
        Note: WhatsApp/Twilio does not support typing indicators.
        This is a no-op.
        
        Args:
            recipient_id: WhatsApp phone number
            **kwargs: Additional arguments
            
        Returns:
            Always True (no-op)
        """
        logger.debug("WhatsApp does not support typing indicators")
        return True
    
    async def notify_error(
        self,
        recipient_id: str,
        error_message: str,
        **kwargs
    ) -> bool:
        """Send error notification via WhatsApp.
        
        Args:
            recipient_id: WhatsApp phone number
            error_message: Error message to send
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        formatted_message = f"⚠️ Ошибка: {error_message}"
        return await self.send_message(recipient_id, formatted_message, **kwargs)
    
    def parse_webhook(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Message]:
        """Parse Twilio WhatsApp webhook payload.
        
        Args:
            payload: Twilio webhook form data (dict)
            headers: HTTP headers from webhook request
            
        Returns:
            Parsed Message object or None if parsing failed
        """
        try:
            # Extract message data from Twilio webhook
            message_sid = payload.get("MessageSid", "")
            from_number = payload.get("From", "")
            body = payload.get("Body")
            media_url = payload.get("MediaUrl0")
            media_type_raw = payload.get("MediaContentType0")
            profile_name = payload.get("ProfileName")
            
            # Determine message type
            message_type = MessageType.TEXT
            media_type = None
            
            if media_url:
                if media_type_raw and media_type_raw.startswith("image"):
                    message_type = MessageType.IMAGE
                    media_type = "image"
                elif media_type_raw and media_type_raw.startswith("video"):
                    message_type = MessageType.VIDEO
                    media_type = "video"
                elif media_type_raw and media_type_raw.startswith("audio"):
                    message_type = MessageType.VOICE
                    media_type = "voice"
                else:
                    message_type = MessageType.DOCUMENT
                    media_type = "document"
            
            # Remove whatsapp: prefix from phone number
            platform_user_id = from_number.replace("whatsapp:", "")
            
            return Message(
                message_id=message_sid,
                platform="whatsapp",
                platform_user_id=platform_user_id,
                message_type=message_type,
                text=body,
                media_url=media_url,
                media_type=media_type,
                first_name=profile_name,
                timestamp=datetime.now(timezone.utc),
                raw_payload=payload,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse WhatsApp webhook: {e}")
            return None
    
    def validate_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
        url: str,
        **kwargs
    ) -> bool:
        """Validate Twilio webhook signature.
        
        Args:
            payload: Webhook form data
            signature: X-Twilio-Signature header value
            url: Full webhook URL
            **kwargs: Additional arguments
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            WebhookValidationError: If validation fails
        """
        if not self.auth_token:
            logger.warning("Cannot validate webhook: auth_token not configured")
            return False
        
        try:
            # Sort parameters and concatenate with URL
            sorted_params = sorted(payload.items())
            data_string = url + "".join([f"{k}{v}" for k, v in sorted_params])
            
            # Compute HMAC-SHA1 signature
            expected_signature = hmac.new(
                self.auth_token.encode("utf-8"),
                data_string.encode("utf-8"),
                hashlib.sha1
            ).digest()
            
            # Encode as base64
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode("utf-8")
            
            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature_b64, signature)
            
            if not is_valid:
                raise WebhookValidationError("Invalid webhook signature")
            
            return True
            
        except Exception as e:
            logger.error(f"Webhook validation failed: {e}")
            raise WebhookValidationError(f"Webhook validation failed: {e}")
    
    async def _notify_admin_error(self, recipient_id: str, error: str) -> None:
        """Notify admin of adapter error.
        
        Args:
            recipient_id: Recipient that failed
            error: Error message
        """
        if not self.notifier:
            return
        
        try:
            event = NotificationEvent(
                event_type="adapter_error",
                recipient_id=1,  # Default admin
                recipient_type="admin",
                language="ru",
                data={
                    "platform": "whatsapp",
                    "recipient_id": recipient_id,
                    "error": error,
                },
                priority="urgent",
                channels=["telegram"],
            )
            
            await self.notifier.send_urgent_escalation(event)
            
        except Exception as e:
            logger.error(f"Failed to notify admin of error: {e}")
