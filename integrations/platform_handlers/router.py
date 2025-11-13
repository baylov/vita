"""Message routing layer for normalizing inbound messages."""

import logging
from typing import Optional, Dict, Callable, Awaitable
from datetime import datetime, timezone

from integrations.platform_handlers.base import Message, PlatformAdapter
from core.conversation import get_storage, ConversationContext, ConversationState
from core.i18n import detect_language

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes and normalizes inbound messages from multiple platforms."""
    
    def __init__(
        self,
        adapters: Optional[Dict[str, PlatformAdapter]] = None,
        user_id_mapper: Optional[Callable[[str, str], Awaitable[int]]] = None,
    ):
        """Initialize message router.
        
        Args:
            adapters: Dictionary mapping platform names to adapter instances
            user_id_mapper: Async function to map platform user IDs to internal user IDs
                           Signature: async def(platform: str, platform_user_id: str) -> int
        """
        self.adapters = adapters or {}
        self.user_id_mapper = user_id_mapper or self._default_user_id_mapper
        logger.info(f"MessageRouter initialized with {len(self.adapters)} adapters")
    
    def register_adapter(self, platform: str, adapter: PlatformAdapter) -> None:
        """Register a platform adapter.
        
        Args:
            platform: Platform name (telegram, whatsapp, instagram)
            adapter: PlatformAdapter instance
        """
        self.adapters[platform] = adapter
        logger.info(f"Registered {platform} adapter")
    
    async def route_message(
        self,
        message: Message,
        handler: Optional[Callable[[Message, ConversationContext], Awaitable[None]]] = None,
    ) -> Optional[ConversationContext]:
        """Route and process inbound message.
        
        Args:
            message: Unified Message object
            handler: Optional handler function to process the message
            
        Returns:
            Updated ConversationContext or None if processing failed
        """
        try:
            # Map platform user ID to internal user ID
            if not message.internal_user_id:
                message.internal_user_id = await self.user_id_mapper(
                    message.platform,
                    message.platform_user_id
                )
            
            logger.info(
                f"Routing message from {message.platform} user {message.platform_user_id} "
                f"(internal ID: {message.internal_user_id})"
            )
            
            # Get or create conversation context
            storage = get_storage()
            context = await storage.load(message.internal_user_id)
            
            if not context:
                # Create new context for new user
                language = detect_language(message.language_code)
                context = await storage.update(
                    user_id=message.internal_user_id,
                    state=ConversationState.START,
                )
                context.platform = message.platform
                context.language = language
                await storage.save(context)
                logger.info(f"Created new conversation context for user {message.internal_user_id}")
            
            # Update platform in context if different
            if context.platform != message.platform:
                logger.info(
                    f"Updating platform for user {message.internal_user_id}: "
                    f"{context.platform} -> {message.platform}"
                )
                context.platform = message.platform
                await storage.save(context)
            
            # Call handler if provided
            if handler:
                await handler(message, context)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to route message: {e}")
            return None
    
    async def parse_and_route(
        self,
        platform: str,
        payload: Dict,
        headers: Optional[Dict[str, str]] = None,
        handler: Optional[Callable[[Message, ConversationContext], Awaitable[None]]] = None,
    ) -> Optional[ConversationContext]:
        """Parse webhook payload and route message.
        
        Args:
            platform: Platform name
            payload: Raw webhook payload
            headers: HTTP headers from webhook request
            handler: Optional handler function to process the message
            
        Returns:
            Updated ConversationContext or None if processing failed
        """
        try:
            # Get adapter for platform
            adapter = self.adapters.get(platform)
            if not adapter:
                logger.error(f"No adapter registered for platform: {platform}")
                return None
            
            # Parse webhook payload
            message = adapter.parse_webhook(payload, headers)
            if not message:
                logger.debug(f"No message parsed from {platform} webhook")
                return None
            
            # Route message
            return await self.route_message(message, handler)
            
        except Exception as e:
            logger.error(f"Failed to parse and route {platform} webhook: {e}")
            return None
    
    async def _default_user_id_mapper(self, platform: str, platform_user_id: str) -> int:
        """Default user ID mapper: hash platform_user_id to integer.
        
        In production, this should look up or create a user record in the database
        and return the internal user ID.
        
        Args:
            platform: Platform name
            platform_user_id: Platform-specific user ID
            
        Returns:
            Internal user ID
        """
        # For Telegram, user IDs are already integers
        if platform == "telegram":
            try:
                return int(platform_user_id)
            except ValueError:
                pass
        
        # For other platforms, hash to create consistent integer ID
        # In production, replace this with database lookup/creation
        import hashlib
        hash_input = f"{platform}:{platform_user_id}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()
        # Convert first 8 hex chars to integer (max ~4 billion)
        user_id = int(hash_value[:8], 16)
        
        logger.debug(f"Mapped {platform}:{platform_user_id} to internal ID {user_id}")
        return user_id
    
    def get_adapter(self, platform: str) -> Optional[PlatformAdapter]:
        """Get adapter for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            PlatformAdapter instance or None if not registered
        """
        return self.adapters.get(platform)
    
    async def send_to_user(
        self,
        internal_user_id: int,
        text: str,
        **kwargs
    ) -> bool:
        """Send message to user via their preferred platform.
        
        Args:
            internal_user_id: Internal user ID
            text: Message text
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get user's conversation context to determine platform
            storage = get_storage()
            context = await storage.load(internal_user_id)
            
            if not context:
                logger.error(f"No context found for user {internal_user_id}")
                return False
            
            platform = context.platform
            adapter = self.adapters.get(platform)
            
            if not adapter:
                logger.error(f"No adapter for platform: {platform}")
                return False
            
            # For Telegram, recipient_id is just the user_id
            # For other platforms, would need to look up platform_user_id
            recipient_id = str(internal_user_id)
            
            return await adapter.send_message(recipient_id, text, **kwargs)
            
        except Exception as e:
            logger.error(f"Failed to send message to user {internal_user_id}: {e}")
            return False
