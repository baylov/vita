"""Base abstraction for platform adapters."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages."""
    
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CALLBACK = "callback"


class Message(BaseModel):
    """Unified message representation across platforms."""
    
    model_config = ConfigDict(from_attributes=True)
    
    message_id: str
    platform: str  # telegram, whatsapp, instagram
    platform_user_id: str  # Platform-specific user identifier
    internal_user_id: Optional[int] = None  # Mapped internal user ID
    message_type: MessageType = MessageType.TEXT
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    callback_data: Optional[str] = None
    language_code: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    
    def get_full_name(self) -> str:
        """Get full name of sender."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.username or f"User {self.platform_user_id}"


class WebhookValidationError(Exception):
    """Raised when webhook signature validation fails."""
    pass


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters."""
    
    def __init__(self, platform_name: str):
        """Initialize adapter.
        
        Args:
            platform_name: Name of the platform (telegram, whatsapp, instagram)
        """
        self.platform_name = platform_name
        self.is_available = True
        logger.info(f"Initialized {platform_name} adapter")
    
    @abstractmethod
    async def send_message(
        self,
        recipient_id: str,
        text: str,
        **kwargs
    ) -> bool:
        """Send text message to recipient.
        
        Args:
            recipient_id: Platform-specific recipient ID
            text: Message text
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def send_media(
        self,
        recipient_id: str,
        media_url: str,
        media_type: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send media message to recipient.
        
        Args:
            recipient_id: Platform-specific recipient ID
            media_url: URL or path to media file
            media_type: Type of media (image, video, document, audio)
            caption: Optional caption for media
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def send_typing(
        self,
        recipient_id: str,
        **kwargs
    ) -> bool:
        """Send typing indicator to recipient.
        
        Args:
            recipient_id: Platform-specific recipient ID
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def notify_error(
        self,
        recipient_id: str,
        error_message: str,
        **kwargs
    ) -> bool:
        """Send error notification to recipient.
        
        Args:
            recipient_id: Platform-specific recipient ID
            error_message: Error message to send
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def parse_webhook(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Message]:
        """Parse webhook payload into unified Message object.
        
        Args:
            payload: Raw webhook payload
            headers: HTTP headers from webhook request
            
        Returns:
            Parsed Message object or None if parsing failed
        """
        pass
    
    @abstractmethod
    def validate_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
        **kwargs
    ) -> bool:
        """Validate webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook request
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            WebhookValidationError: If validation fails
        """
        pass
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return self.platform_name
    
    def set_availability(self, available: bool) -> None:
        """Set adapter availability."""
        self.is_available = available
        logger.info(f"{self.platform_name} adapter availability: {available}")
