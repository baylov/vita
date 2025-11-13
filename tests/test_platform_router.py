"""Tests for message router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from integrations.platform_handlers.router import MessageRouter
from integrations.platform_handlers.base import Message, MessageType, PlatformAdapter
from core.conversation import ConversationState, get_storage, reset_storage


@pytest.fixture(autouse=True)
def reset_conversation_storage():
    """Reset conversation storage before each test."""
    reset_storage()
    yield
    reset_storage()


@pytest.fixture
def mock_telegram_adapter():
    """Create mock Telegram adapter."""
    adapter = MagicMock(spec=PlatformAdapter)
    adapter.platform_name = "telegram"
    adapter.parse_webhook = MagicMock()
    adapter.send_message = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def mock_whatsapp_adapter():
    """Create mock WhatsApp adapter."""
    adapter = MagicMock(spec=PlatformAdapter)
    adapter.platform_name = "whatsapp"
    adapter.parse_webhook = MagicMock()
    adapter.send_message = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def message_router(mock_telegram_adapter, mock_whatsapp_adapter):
    """Create MessageRouter with mock adapters."""
    return MessageRouter(
        adapters={
            "telegram": mock_telegram_adapter,
            "whatsapp": mock_whatsapp_adapter,
        }
    )


@pytest.fixture
def sample_telegram_message():
    """Create sample Telegram message."""
    return Message(
        message_id="123",
        platform="telegram",
        platform_user_id="987654321",
        message_type=MessageType.TEXT,
        text="Hello, world!",
        language_code="ru",
        username="testuser",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def sample_whatsapp_message():
    """Create sample WhatsApp message."""
    return Message(
        message_id="456",
        platform="whatsapp",
        platform_user_id="+1234567890",
        message_type=MessageType.TEXT,
        text="Hello from WhatsApp!",
        first_name="John"
    )


class TestMessageRouterInit:
    """Tests for MessageRouter initialization."""
    
    def test_init_with_adapters(self, mock_telegram_adapter, mock_whatsapp_adapter):
        """Test initialization with adapters."""
        router = MessageRouter(
            adapters={
                "telegram": mock_telegram_adapter,
                "whatsapp": mock_whatsapp_adapter,
            }
        )
        
        assert len(router.adapters) == 2
        assert "telegram" in router.adapters
        assert "whatsapp" in router.adapters
    
    def test_init_empty(self):
        """Test initialization without adapters."""
        router = MessageRouter()
        
        assert len(router.adapters) == 0
    
    def test_register_adapter(self, message_router, mock_telegram_adapter):
        """Test registering an adapter."""
        new_adapter = MagicMock(spec=PlatformAdapter)
        new_adapter.platform_name = "instagram"
        
        message_router.register_adapter("instagram", new_adapter)
        
        assert "instagram" in message_router.adapters
        assert message_router.adapters["instagram"] == new_adapter


class TestMessageRouterRouting:
    """Tests for message routing."""
    
    @pytest.mark.asyncio
    async def test_route_telegram_message(self, message_router, sample_telegram_message):
        """Test routing Telegram message."""
        context = await message_router.route_message(sample_telegram_message)
        
        assert context is not None
        assert context.platform == "telegram"
        assert context.user_id == 987654321
        assert context.current_state == ConversationState.START
        assert context.language == "ru"
    
    @pytest.mark.asyncio
    async def test_route_whatsapp_message(self, message_router, sample_whatsapp_message):
        """Test routing WhatsApp message."""
        # Set internal_user_id to avoid hashing
        sample_whatsapp_message.internal_user_id = 12345
        
        context = await message_router.route_message(sample_whatsapp_message)
        
        assert context is not None
        assert context.platform == "whatsapp"
        assert context.user_id == 12345
    
    @pytest.mark.asyncio
    async def test_route_message_with_handler(self, message_router, sample_telegram_message):
        """Test routing message with handler."""
        handler_called = False
        
        async def test_handler(message, context):
            nonlocal handler_called
            handler_called = True
            assert message == sample_telegram_message
            assert context is not None
        
        context = await message_router.route_message(sample_telegram_message, handler=test_handler)
        
        assert context is not None
        assert handler_called is True
    
    @pytest.mark.asyncio
    async def test_route_message_existing_context(self, message_router, sample_telegram_message):
        """Test routing message for user with existing context."""
        # Create initial context
        storage = get_storage()
        await storage.update(
            user_id=987654321,
            state=ConversationState.WAITING_NAME,
        )
        
        context = await message_router.route_message(sample_telegram_message)
        
        assert context is not None
        assert context.current_state == ConversationState.WAITING_NAME
    
    @pytest.mark.asyncio
    async def test_route_message_updates_platform(self, message_router):
        """Test that routing updates platform if different."""
        # Create context with telegram platform
        storage = get_storage()
        await storage.update(
            user_id=12345,
            state=ConversationState.START,
        )
        context = await storage.load(12345)
        context.platform = "telegram"
        await storage.save(context)
        
        # Route WhatsApp message for same user
        whatsapp_msg = Message(
            message_id="456",
            platform="whatsapp",
            platform_user_id="+123",
            internal_user_id=12345,
            message_type=MessageType.TEXT,
            text="Test"
        )
        
        result_context = await message_router.route_message(whatsapp_msg)
        
        assert result_context is not None
        assert result_context.platform == "whatsapp"


class TestMessageRouterParseAndRoute:
    """Tests for parse_and_route."""
    
    @pytest.mark.asyncio
    async def test_parse_and_route_success(self, message_router, mock_telegram_adapter, sample_telegram_message):
        """Test parse and route successfully."""
        mock_telegram_adapter.parse_webhook.return_value = sample_telegram_message
        
        context = await message_router.parse_and_route(
            platform="telegram",
            payload={"test": "data"}
        )
        
        assert context is not None
        mock_telegram_adapter.parse_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_and_route_no_adapter(self, message_router):
        """Test parse and route with no adapter."""
        context = await message_router.parse_and_route(
            platform="unknown",
            payload={}
        )
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_parse_and_route_no_message(self, message_router, mock_telegram_adapter):
        """Test parse and route when no message parsed."""
        mock_telegram_adapter.parse_webhook.return_value = None
        
        context = await message_router.parse_and_route(
            platform="telegram",
            payload={}
        )
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_parse_and_route_with_handler(self, message_router, mock_telegram_adapter, sample_telegram_message):
        """Test parse and route with handler."""
        mock_telegram_adapter.parse_webhook.return_value = sample_telegram_message
        handler_called = False
        
        async def test_handler(message, context):
            nonlocal handler_called
            handler_called = True
        
        await message_router.parse_and_route(
            platform="telegram",
            payload={},
            handler=test_handler
        )
        
        assert handler_called is True


class TestMessageRouterUserIdMapper:
    """Tests for user ID mapping."""
    
    @pytest.mark.asyncio
    async def test_default_mapper_telegram(self, message_router):
        """Test default mapper with Telegram user ID."""
        user_id = await message_router._default_user_id_mapper("telegram", "123456789")
        
        assert user_id == 123456789
    
    @pytest.mark.asyncio
    async def test_default_mapper_whatsapp(self, message_router):
        """Test default mapper with WhatsApp user ID."""
        user_id = await message_router._default_user_id_mapper("whatsapp", "+1234567890")
        
        # Should return consistent hash
        assert isinstance(user_id, int)
        assert user_id > 0
        
        # Same input should return same output
        user_id2 = await message_router._default_user_id_mapper("whatsapp", "+1234567890")
        assert user_id == user_id2
    
    @pytest.mark.asyncio
    async def test_default_mapper_different_platforms(self, message_router):
        """Test default mapper with same ID on different platforms."""
        user_id1 = await message_router._default_user_id_mapper("whatsapp", "123")
        user_id2 = await message_router._default_user_id_mapper("instagram", "123")
        
        # Different platforms should produce different IDs
        assert user_id1 != user_id2
    
    @pytest.mark.asyncio
    async def test_custom_mapper(self):
        """Test custom user ID mapper."""
        async def custom_mapper(platform, platform_user_id):
            return 99999
        
        router = MessageRouter(user_id_mapper=custom_mapper)
        
        message = Message(
            message_id="1",
            platform="telegram",
            platform_user_id="123",
            message_type=MessageType.TEXT,
            text="Test"
        )
        
        context = await router.route_message(message)
        
        assert context.user_id == 99999


class TestMessageRouterSendToUser:
    """Tests for sending messages to users."""
    
    @pytest.mark.asyncio
    async def test_send_to_user_success(self, message_router, sample_telegram_message):
        """Test sending message to user successfully."""
        # Create context for user
        context = await message_router.route_message(sample_telegram_message)
        assert context is not None
        
        result = await message_router.send_to_user(
            internal_user_id=context.user_id,
            text="Reply message"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_to_user_no_context(self, message_router):
        """Test sending message to user without context."""
        result = await message_router.send_to_user(
            internal_user_id=99999,
            text="Message"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_to_user_no_adapter(self, message_router):
        """Test sending message when adapter not available."""
        # Create context with unknown platform
        storage = get_storage()
        await storage.update(
            user_id=12345,
            state=ConversationState.START,
        )
        context = await storage.load(12345)
        context.platform = "unknown"
        await storage.save(context)
        
        result = await message_router.send_to_user(
            internal_user_id=12345,
            text="Message"
        )
        
        assert result is False


class TestMessageRouterGetAdapter:
    """Tests for getting adapters."""
    
    def test_get_adapter_success(self, message_router, mock_telegram_adapter):
        """Test getting adapter successfully."""
        adapter = message_router.get_adapter("telegram")
        
        assert adapter is not None
        assert adapter == mock_telegram_adapter
    
    def test_get_adapter_not_found(self, message_router):
        """Test getting adapter that doesn't exist."""
        adapter = message_router.get_adapter("unknown")
        
        assert adapter is None


class TestMessageRouterIntegration:
    """Integration tests for message router."""
    
    @pytest.mark.asyncio
    async def test_complete_message_flow(self, message_router, mock_telegram_adapter, sample_telegram_message):
        """Test complete message flow from webhook to response."""
        mock_telegram_adapter.parse_webhook.return_value = sample_telegram_message
        
        # Parse and route webhook
        context = await message_router.parse_and_route(
            platform="telegram",
            payload={"update": "data"}
        )
        
        assert context is not None
        assert context.platform == "telegram"
        
        # Send reply
        result = await message_router.send_to_user(
            internal_user_id=context.user_id,
            text="Reply"
        )
        
        assert result is True
        mock_telegram_adapter.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_platform_user(self, message_router):
        """Test user switching platforms."""
        # User sends Telegram message
        telegram_msg = Message(
            message_id="1",
            platform="telegram",
            platform_user_id="123",
            internal_user_id=12345,
            message_type=MessageType.TEXT,
            text="Hello from Telegram"
        )
        
        context1 = await message_router.route_message(telegram_msg)
        assert context1.platform == "telegram"
        
        # Same user sends WhatsApp message
        whatsapp_msg = Message(
            message_id="2",
            platform="whatsapp",
            platform_user_id="+123",
            internal_user_id=12345,
            message_type=MessageType.TEXT,
            text="Hello from WhatsApp"
        )
        
        context2 = await message_router.route_message(whatsapp_msg)
        assert context2.platform == "whatsapp"
        assert context2.user_id == context1.user_id
