"""Unit tests for conversation core module."""

import asyncio
import json
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from core.conversation import (
    CollectedInfo,
    ConversationContext,
    ConversationState,
    ConversationStorage,
    StateTransitionError,
    get_storage,
    reset_storage,
)


class TestConversationState:
    """Tests for ConversationState enum."""

    def test_all_states_defined(self):
        """Test that all required states are defined."""
        expected_states = [
            "START",
            "WAITING_NAME",
            "WAITING_PHONE",
            "WAITING_DOCTOR_CHOICE",
            "WAITING_DATE",
            "WAITING_TIME",
            "CONFIRM_BOOKING",
            "DONE",
            "ADMIN_MENU",
            "ERROR_FALLBACK",
        ]
        actual_states = [s.value for s in ConversationState]
        assert sorted(actual_states) == sorted(expected_states)

    def test_state_value_comparison(self):
        """Test that state values can be compared."""
        assert ConversationState.START.value == "START"
        assert ConversationState.DONE.value == "DONE"


class TestCollectedInfo:
    """Tests for CollectedInfo model."""

    def test_create_empty_info(self):
        """Test creating empty collected info."""
        info = CollectedInfo()
        assert info.name is None
        assert info.phone is None
        assert info.doctor_id is None
        assert info.booking_date is None
        assert info.booking_time is None
        assert info.booking_duration == 60

    def test_create_with_values(self):
        """Test creating collected info with values."""
        info = CollectedInfo(
            name="John Doe",
            phone="+1234567890",
            doctor_id=1,
            doctor_name="Dr. Smith",
            booking_date="2024-01-15",
            booking_time="10:00",
        )
        assert info.name == "John Doe"
        assert info.phone == "+1234567890"
        assert info.doctor_id == 1
        assert info.doctor_name == "Dr. Smith"
        assert info.booking_date == "2024-01-15"
        assert info.booking_time == "10:00"

    def test_serialization(self):
        """Test serialization of collected info."""
        info = CollectedInfo(name="Alice", phone="555-1234")
        data = info.model_dump()
        assert data["name"] == "Alice"
        assert data["phone"] == "555-1234"


class TestConversationContext:
    """Tests for ConversationContext model."""

    def test_create_context(self):
        """Test creating a conversation context."""
        context = ConversationContext(user_id=123)
        assert context.user_id == 123
        assert context.platform == "telegram"
        assert context.language == "ru"
        assert context.current_state == ConversationState.START
        assert context.context_id is not None
        assert context.admin_mode is False

    def test_context_timestamps(self):
        """Test that timestamps are set correctly."""
        context = ConversationContext(user_id=123)
        assert context.created_at is not None
        assert context.updated_at is not None
        assert context.last_activity is not None

    def test_to_dict(self):
        """Test serialization to dict."""
        context = ConversationContext(user_id=123, language="kz")
        data = context.to_dict()
        assert data["user_id"] == 123
        assert data["language"] == "kz"
        assert data["current_state"] == "START"
        assert isinstance(data["created_at"], str)

    def test_to_json(self):
        """Test serialization to JSON string."""
        context = ConversationContext(user_id=123)
        json_str = context.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["user_id"] == 123

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "context_id": "test-id",
            "user_id": 123,
            "platform": "telegram",
            "language": "ru",
            "current_state": "WAITING_NAME",
            "collected_info": {"name": "Test User"},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
        }
        context = ConversationContext.from_dict(data)
        assert context.user_id == 123
        assert context.current_state == ConversationState.WAITING_NAME
        assert context.collected_info.name == "Test User"

    def test_from_json(self):
        """Test deserialization from JSON string."""
        context = ConversationContext(user_id=456, language="kz")
        json_str = context.to_json()
        restored = ConversationContext.from_json(json_str)
        assert restored.user_id == 456
        assert restored.language == "kz"
        assert restored.current_state == ConversationState.START

    def test_round_trip_serialization(self):
        """Test round-trip serialization preserves all data."""
        original = ConversationContext(
            user_id=789,
            platform="web",
            language="kz",
            admin_mode=True,
        )
        original.collected_info.name = "Round Trip"
        original.collected_info.phone = "123-456"

        json_str = original.to_json()
        restored = ConversationContext.from_json(json_str)

        assert restored.user_id == original.user_id
        assert restored.platform == original.platform
        assert restored.language == original.language
        assert restored.admin_mode == original.admin_mode
        assert restored.collected_info.name == original.collected_info.name
        assert restored.collected_info.phone == original.collected_info.phone


class TestConversationStorage:
    """Tests for ConversationStorage service."""

    @pytest_asyncio.fixture
    async def storage(self):
        """Create a fresh storage instance for each test."""
        reset_storage()
        return get_storage()

    @pytest.mark.asyncio
    async def test_storage_initialization(self):
        """Test storage initializes correctly."""
        reset_storage()
        storage = get_storage()
        assert storage.get_cache_size() == 0

    @pytest.mark.asyncio
    async def test_save_and_load(self, storage):
        """Test saving and loading a context."""
        context = ConversationContext(user_id=100)
        await storage.save(context)

        loaded = await storage.load(100)
        assert loaded is not None
        assert loaded.user_id == 100
        assert loaded.context_id == context.context_id

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, storage):
        """Test loading a non-existent context returns None."""
        loaded = await storage.load(999)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_update_existing(self, storage):
        """Test updating an existing context."""
        context = ConversationContext(user_id=200)
        await storage.save(context)

        # Update the context
        info = CollectedInfo(name="Alice", phone="555-1234")
        updated = await storage.update(
            user_id=200,
            state=ConversationState.WAITING_NAME,
            collected_info=info,
        )

        assert updated.current_state == ConversationState.WAITING_NAME
        assert updated.collected_info.name == "Alice"

        # Verify it's persisted
        loaded = await storage.load(200)
        assert loaded.current_state == ConversationState.WAITING_NAME

    @pytest.mark.asyncio
    async def test_update_creates_new_context(self, storage):
        """Test update creates a new context if it doesn't exist."""
        info = CollectedInfo(name="Bob")
        updated = await storage.update(
            user_id=300,
            state=ConversationState.WAITING_PHONE,
            collected_info=info,
        )

        assert updated.user_id == 300
        assert updated.current_state == ConversationState.WAITING_PHONE
        assert updated.collected_info.name == "Bob"

    @pytest.mark.asyncio
    async def test_transition_valid(self, storage):
        """Test valid state transition."""
        context = ConversationContext(user_id=400)
        await storage.save(context)

        # Transition from START to WAITING_NAME
        transitioned = await storage.transition(
            user_id=400,
            new_state=ConversationState.WAITING_NAME,
            validate=True,
        )

        assert transitioned.current_state == ConversationState.WAITING_NAME

    @pytest.mark.asyncio
    async def test_transition_invalid_flow(self, storage):
        """Test invalid state transition raises error."""
        context = ConversationContext(user_id=500)
        await storage.save(context)

        # Cannot go from START to DONE directly
        with pytest.raises(StateTransitionError):
            await storage.transition(
                user_id=500,
                new_state=ConversationState.DONE,
                validate=True,
            )

    @pytest.mark.asyncio
    async def test_transition_missing_required_fields(self, storage):
        """Test transition to CONFIRM_BOOKING without required fields."""
        context = ConversationContext(user_id=600)
        context.current_state = ConversationState.WAITING_TIME
        await storage.save(context)

        # Cannot confirm booking without required fields
        with pytest.raises(StateTransitionError) as exc_info:
            await storage.transition(
                user_id=600,
                new_state=ConversationState.CONFIRM_BOOKING,
                validate=True,
            )
        assert "missing_fields" in str(exc_info.value).lower() or "name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transition_confirm_with_all_fields(self, storage):
        """Test successful transition to CONFIRM_BOOKING with all fields."""
        info = CollectedInfo(
            name="Charlie",
            phone="555-9876",
            doctor_id=1,
            booking_date="2024-01-20",
            booking_time="14:30",
        )
        context = ConversationContext(user_id=700, collected_info=info)
        context.current_state = ConversationState.WAITING_TIME
        await storage.save(context)

        # Should succeed with all required fields
        transitioned = await storage.transition(
            user_id=700,
            new_state=ConversationState.CONFIRM_BOOKING,
            validate=True,
        )
        assert transitioned.current_state == ConversationState.CONFIRM_BOOKING

    @pytest.mark.asyncio
    async def test_transition_without_validation(self, storage):
        """Test transition without validation allows any move."""
        context = ConversationContext(user_id=800)
        await storage.save(context)

        # Even though this would fail with validation, it succeeds without it
        transitioned = await storage.transition(
            user_id=800,
            new_state=ConversationState.DONE,
            validate=False,
        )
        assert transitioned.current_state == ConversationState.DONE

    @pytest.mark.asyncio
    async def test_transition_clears_error(self, storage):
        """Test that successful transition clears error message."""
        context = ConversationContext(user_id=900)
        context.error_message = "Previous error"
        await storage.save(context)

        transitioned = await storage.transition(
            user_id=900,
            new_state=ConversationState.WAITING_NAME,
        )
        assert transitioned.error_message is None

    @pytest.mark.asyncio
    async def test_clear_context(self, storage):
        """Test clearing a specific context."""
        context = ConversationContext(user_id=1000)
        await storage.save(context)
        assert storage.get_cache_size() == 1

        await storage.clear(1000)
        assert storage.get_cache_size() == 0

        loaded = await storage.load(1000)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_clear_all_contexts(self, storage):
        """Test clearing all contexts."""
        # Add multiple contexts
        for user_id in [1100, 1101, 1102]:
            context = ConversationContext(user_id=user_id)
            await storage.save(context)

        assert storage.get_cache_size() == 3

        await storage.clear_all()
        assert storage.get_cache_size() == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, storage):
        """Test cleaning up expired contexts."""
        # Add a recent context
        recent = ConversationContext(user_id=1200)
        await storage.save(recent)

        # Add an old context
        old = ConversationContext(user_id=1201)
        old.last_activity = datetime.now() - timedelta(days=2)
        await storage.save(old)

        assert storage.get_cache_size() == 2

        # Clean up contexts older than 1 day
        removed = await storage.cleanup_expired(max_age_seconds=86400)

        assert removed == 1
        assert storage.get_cache_size() == 1

        # Verify the recent one is still there
        remaining = await storage.load(1200)
        assert remaining is not None
        assert remaining.user_id == 1200

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self, storage):
        """Test that contexts for different users are isolated."""
        info1 = CollectedInfo(name="User 1")
        info2 = CollectedInfo(name="User 2")

        await storage.update(user_id=1300, collected_info=info1)
        await storage.update(user_id=1301, collected_info=info2)

        ctx1 = await storage.load(1300)
        ctx2 = await storage.load(1301)

        assert ctx1.collected_info.name == "User 1"
        assert ctx2.collected_info.name == "User 2"

        # Modifying one doesn't affect the other
        ctx1.collected_info.name = "Modified User 1"
        await storage.save(ctx1)

        ctx2_check = await storage.load(1301)
        assert ctx2_check.collected_info.name == "User 2"

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, storage):
        """Test thread-safe concurrent updates."""

        async def update_context(user_id: int, iterations: int):
            for i in range(iterations):
                await storage.update(
                    user_id=user_id,
                    state=ConversationState.WAITING_NAME
                    if i % 2 == 0
                    else ConversationState.WAITING_PHONE,
                )

        # Run concurrent updates
        await asyncio.gather(
            update_context(1400, 10),
            update_context(1401, 10),
            update_context(1402, 10),
        )

        # Verify all contexts exist
        assert storage.get_cache_size() == 3

        for user_id in [1400, 1401, 1402]:
            ctx = await storage.load(user_id)
            assert ctx is not None
            assert ctx.user_id == user_id

    @pytest.mark.asyncio
    async def test_context_persistence_after_restart_simulation(self, storage):
        """Test that context can be recovered after simulated restart."""
        # Create and save a context
        original = ConversationContext(user_id=1500, language="kz")
        original.collected_info.name = "Persistence Test"
        original.collected_info.phone = "555-5555"
        original.current_state = ConversationState.WAITING_DATE
        await storage.save(original)

        # Simulate serialization (as would happen when persisting to DB)
        serialized = original.to_json()

        # Simulate restart - get new storage instance
        reset_storage()
        new_storage = get_storage()

        # Load from serialized data
        restored = ConversationContext.from_json(serialized)
        await new_storage.save(restored)

        # Verify recovery
        recovered = await new_storage.load(1500)
        assert recovered is not None
        assert recovered.user_id == 1500
        assert recovered.language == "kz"
        assert recovered.collected_info.name == "Persistence Test"
        assert recovered.current_state == ConversationState.WAITING_DATE

    @pytest.mark.asyncio
    async def test_transition_sequence(self, storage):
        """Test a realistic sequence of transitions."""
        user_id = 1600
        context = ConversationContext(user_id=user_id)
        await storage.save(context)

        # START -> WAITING_NAME
        ctx = await storage.transition(user_id, ConversationState.WAITING_NAME)
        assert ctx.current_state == ConversationState.WAITING_NAME

        # WAITING_NAME -> WAITING_PHONE
        ctx = await storage.update(
            user_id, collected_info=CollectedInfo(name="Test User")
        )
        ctx = await storage.transition(user_id, ConversationState.WAITING_PHONE)
        assert ctx.current_state == ConversationState.WAITING_PHONE

        # WAITING_PHONE -> WAITING_DOCTOR_CHOICE
        ctx = await storage.update(
            user_id, collected_info=CollectedInfo(name="Test User", phone="555-1111")
        )
        ctx = await storage.transition(
            user_id, ConversationState.WAITING_DOCTOR_CHOICE
        )
        assert ctx.current_state == ConversationState.WAITING_DOCTOR_CHOICE

        # WAITING_DOCTOR_CHOICE -> WAITING_DATE
        ctx = await storage.update(
            user_id,
            collected_info=CollectedInfo(
                name="Test User", phone="555-1111", doctor_id=1, doctor_name="Dr. Test"
            ),
        )
        ctx = await storage.transition(user_id, ConversationState.WAITING_DATE)
        assert ctx.current_state == ConversationState.WAITING_DATE

        # WAITING_DATE -> WAITING_TIME
        ctx = await storage.update(
            user_id,
            collected_info=CollectedInfo(
                name="Test User",
                phone="555-1111",
                doctor_id=1,
                doctor_name="Dr. Test",
                booking_date="2024-01-25",
            ),
        )
        ctx = await storage.transition(user_id, ConversationState.WAITING_TIME)
        assert ctx.current_state == ConversationState.WAITING_TIME

        # WAITING_TIME -> CONFIRM_BOOKING
        ctx = await storage.update(
            user_id,
            collected_info=CollectedInfo(
                name="Test User",
                phone="555-1111",
                doctor_id=1,
                doctor_name="Dr. Test",
                booking_date="2024-01-25",
                booking_time="10:30",
            ),
        )
        ctx = await storage.transition(user_id, ConversationState.CONFIRM_BOOKING)
        assert ctx.current_state == ConversationState.CONFIRM_BOOKING

        # CONFIRM_BOOKING -> DONE
        ctx = await storage.transition(user_id, ConversationState.DONE)
        assert ctx.current_state == ConversationState.DONE

    @pytest.mark.asyncio
    async def test_error_fallback_transitions(self, storage):
        """Test transitions to and from ERROR_FALLBACK state."""
        user_id = 1700
        context = ConversationContext(user_id=user_id)
        context.current_state = ConversationState.WAITING_NAME
        await storage.save(context)

        # Can transition to ERROR_FALLBACK from any state
        ctx = await storage.transition(
            user_id, ConversationState.ERROR_FALLBACK, validate=True
        )
        assert ctx.current_state == ConversationState.ERROR_FALLBACK

        # From ERROR_FALLBACK, can go back to START
        ctx = await storage.transition(user_id, ConversationState.START, validate=True)
        assert ctx.current_state == ConversationState.START

    @pytest.mark.asyncio
    async def test_admin_mode_flag(self, storage):
        """Test setting and checking admin mode flag."""
        user_id = 1800
        ctx = await storage.update(user_id, admin_mode=True)
        assert ctx.admin_mode is True

        ctx = await storage.update(user_id, admin_mode=False)
        assert ctx.admin_mode is False

        # Verify it persists
        loaded = await storage.load(user_id)
        assert loaded.admin_mode is False

    @pytest.mark.asyncio
    async def test_error_message_handling(self, storage):
        """Test setting and clearing error messages."""
        user_id = 1900
        context = ConversationContext(user_id=user_id)
        await storage.save(context)

        # Set error message
        ctx = await storage.update(user_id, error_message="Something went wrong")
        assert ctx.error_message == "Something went wrong"

        # Error clears on transition
        await storage.transition(
            user_id, ConversationState.WAITING_NAME, validate=False
        )
        loaded = await storage.load(user_id)
        assert loaded.error_message is None

    @pytest.mark.asyncio
    async def test_last_activity_updated(self, storage):
        """Test that last_activity is updated on operations."""
        user_id = 2000
        context = ConversationContext(user_id=user_id)
        await storage.save(context)
        first_activity = (await storage.load(user_id)).last_activity

        # Wait a bit
        await asyncio.sleep(0.1)

        # Update should update last_activity
        await storage.update(user_id, state=ConversationState.WAITING_NAME)
        second_activity = (await storage.load(user_id)).last_activity

        assert second_activity > first_activity


class TestGlobalStorageInstance:
    """Tests for global storage instance management."""

    def test_get_storage_singleton(self):
        """Test that get_storage returns the same instance."""
        reset_storage()
        storage1 = get_storage()
        storage2 = get_storage()
        assert storage1 is storage2

    def test_reset_storage(self):
        """Test that reset_storage creates a new instance."""
        storage1 = get_storage()
        reset_storage()
        storage2 = get_storage()
        assert storage1 is not storage2

    @pytest.mark.asyncio
    async def test_storage_singleton_persistence(self):
        """Test that data persists across get_storage calls."""
        reset_storage()
        storage1 = get_storage()
        context = ConversationContext(user_id=2100)
        await storage1.save(context)

        storage2 = get_storage()
        loaded = await storage2.load(2100)
        assert loaded is not None
        assert loaded.user_id == 2100
