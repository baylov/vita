"""Instagram platform adapter using Facebook Graph API."""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from integrations.platform.base import (
    PlatformAdapter,
    Message,
    MessageType,
    WebhookValidationError,
)
from services.notifications.notifier import Notifier, NotificationEvent

logger = logging.getLogger(__name__)


class InstagramAdapter(PlatformAdapter):
    """Instagram platform adapter using Facebook Graph API."""
    
    def __init__(
        self,
        page_access_token: Optional[str] = None,
        app_secret: Optional[str] = None,
        verify_token: Optional[str] = None,
        notifier: Optional[Notifier] = None,
    ):
        """Initialize Instagram adapter.
        
        Args:
            page_access_token: Facebook Page access token
            app_secret: Facebook App secret for webhook validation
            verify_token: Verify token for webhook subscription handshake
            notifier: Notifier instance for admin alerts
        """
        super().__init__("instagram")
        self.page_access_token = page_access_token
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.notifier = notifier
        self.api_base = "https://graph.facebook.com/v18.0"
        
        if not all([page_access_token, app_secret]):
            logger.warning("Instagram adapter initialized without credentials")
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
        """Send text message via Instagram.
        
        Args:
            recipient_id: Instagram-scoped user ID (IGSID)
            text: Message text
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available:
            logger.error("Instagram adapter not available")
            return False
        
        try:
            url = f"{self.api_base}/me/messages"
            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": text},
                "messaging_type": "RESPONSE",
            }
            params = {"access_token": self.page_access_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=data,
                    params=params,
                )
                response.raise_for_status()
            
            logger.debug(f"Sent Instagram message to {recipient_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Instagram API error: {e.response.status_code} - {e.response.text}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Instagram message to {recipient_id}: {e}")
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
        """Send media message via Instagram.
        
        Args:
            recipient_id: Instagram-scoped user ID
            media_url: Public URL to media file
            media_type: Type of media (image, video, audio)
            caption: Optional caption (not supported for Instagram DM)
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available:
            logger.error("Instagram adapter not available")
            return False
        
        try:
            url = f"{self.api_base}/me/messages"
            
            # Map media types to Instagram attachment types
            attachment_type = "image" if media_type == "image" else "file"
            
            data = {
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": attachment_type,
                        "payload": {"url": media_url}
                    }
                },
                "messaging_type": "RESPONSE",
            }
            params = {"access_token": self.page_access_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=data,
                    params=params,
                )
                response.raise_for_status()
            
            # Send caption as separate message if provided
            if caption:
                await self.send_message(recipient_id, caption)
            
            logger.debug(f"Sent Instagram {media_type} to {recipient_id}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Instagram API error: {e.response.status_code} - {e.response.text}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
            
        except Exception as e:
            logger.error(f"Failed to send Instagram media to {recipient_id}: {e}")
            await self._notify_admin_error(recipient_id, str(e))
            return False
    
    async def send_typing(
        self,
        recipient_id: str,
        **kwargs
    ) -> bool:
        """Send typing indicator via Instagram.
        
        Args:
            recipient_id: Instagram-scoped user ID
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available:
            logger.error("Instagram adapter not available")
            return False
        
        try:
            url = f"{self.api_base}/me/messages"
            data = {
                "recipient": {"id": recipient_id},
                "sender_action": "typing_on",
            }
            params = {"access_token": self.page_access_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=data,
                    params=params,
                )
                response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send typing indicator to {recipient_id}: {e}")
            return False
    
    async def notify_error(
        self,
        recipient_id: str,
        error_message: str,
        **kwargs
    ) -> bool:
        """Send error notification via Instagram.
        
        Args:
            recipient_id: Instagram-scoped user ID
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
        """Parse Instagram webhook payload.
        
        Args:
            payload: Instagram webhook JSON payload
            headers: HTTP headers from webhook request
            
        Returns:
            Parsed Message object or None if parsing failed
        """
        try:
            # Handle webhook verification challenge
            if "hub.challenge" in payload:
                logger.info("Received Instagram webhook verification challenge")
                return None
            
            # Parse messaging events
            entries = payload.get("entry", [])
            if not entries:
                return None
            
            for entry in entries:
                messaging_events = entry.get("messaging", [])
                
                for event in messaging_events:
                    # Parse message event
                    if "message" in event:
                        return self._parse_message_event(event)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse Instagram webhook: {e}")
            return None
    
    def _parse_message_event(self, event: Dict[str, Any]) -> Message:
        """Parse Instagram message event.
        
        Args:
            event: Instagram messaging event
            
        Returns:
            Parsed Message object
        """
        sender_id = event.get("sender", {}).get("id", "")
        message_data = event.get("message", {})
        message_id = message_data.get("mid", "")
        timestamp = event.get("timestamp", 0)
        
        # Extract message content
        text = message_data.get("text")
        attachments = message_data.get("attachments", [])
        
        message_type = MessageType.TEXT
        media_url = None
        media_type = None
        
        # Parse attachments
        if attachments:
            attachment = attachments[0]
            attachment_type = attachment.get("type", "")
            payload = attachment.get("payload", {})
            media_url = payload.get("url")
            
            if attachment_type == "image":
                message_type = MessageType.IMAGE
                media_type = "image"
            elif attachment_type == "video":
                message_type = MessageType.VIDEO
                media_type = "video"
            elif attachment_type == "audio":
                message_type = MessageType.VOICE
                media_type = "audio"
            else:
                message_type = MessageType.DOCUMENT
                media_type = "document"
        
        return Message(
            message_id=message_id,
            platform="instagram",
            platform_user_id=sender_id,
            message_type=message_type,
            text=text,
            media_url=media_url,
            media_type=media_type,
            timestamp=datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc) if timestamp else datetime.now(timezone.utc),
            raw_payload=event,
        )
    
    def validate_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
        **kwargs
    ) -> bool:
        """Validate Instagram webhook signature.
        
        Args:
            payload: Webhook JSON payload (as bytes or string)
            signature: X-Hub-Signature-256 header value
            **kwargs: Additional arguments
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            WebhookValidationError: If validation fails
        """
        if not self.app_secret:
            logger.warning("Cannot validate webhook: app_secret not configured")
            return False
        
        try:
            # Convert payload to bytes if needed
            if isinstance(payload, dict):
                import json
                payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
            elif isinstance(payload, str):
                payload_bytes = payload.encode("utf-8")
            else:
                payload_bytes = payload
            
            # Compute HMAC-SHA256 signature
            expected_signature = hmac.new(
                self.app_secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Remove sha256= prefix from signature if present
            if signature.startswith("sha256="):
                signature = signature[7:]
            
            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                raise WebhookValidationError("Invalid webhook signature")
            
            return True
            
        except Exception as e:
            logger.error(f"Webhook validation failed: {e}")
            raise WebhookValidationError(f"Webhook validation failed: {e}")
    
    def verify_webhook_subscription(
        self,
        mode: str,
        token: str,
        challenge: str
    ) -> Optional[str]:
        """Handle webhook subscription verification.
        
        Args:
            mode: hub.mode parameter
            token: hub.verify_token parameter
            challenge: hub.challenge parameter
            
        Returns:
            Challenge string if verification succeeds, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Instagram webhook subscription verified")
            return challenge
        
        logger.warning("Instagram webhook verification failed")
        return None
    
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
                    "platform": "instagram",
                    "recipient_id": recipient_id,
                    "error": error,
                },
                priority="urgent",
                channels=["telegram"],
            )
            
            await self.notifier.send_urgent_escalation(event)
            
        except Exception as e:
            logger.error(f"Failed to notify admin of error: {e}")
