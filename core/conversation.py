"""Conversation core module for finite state machine and context persistence."""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Finite state machine states for conversation flow."""

    START = "START"
    WAITING_NAME = "WAITING_NAME"
    WAITING_PHONE = "WAITING_PHONE"
    WAITING_DOCTOR_CHOICE = "WAITING_DOCTOR_CHOICE"
    WAITING_DATE = "WAITING_DATE"
    WAITING_TIME = "WAITING_TIME"
    CONFIRM_BOOKING = "CONFIRM_BOOKING"
    DONE = "DONE"
    ADMIN_MENU = "ADMIN_MENU"
    ERROR_FALLBACK = "ERROR_FALLBACK"
    
    # Admin flow states
    ADMIN_ADD_SPECIALIST_NAME = "ADMIN_ADD_SPECIALIST_NAME"
    ADMIN_ADD_SPECIALIST_SPECIALIZATION = "ADMIN_ADD_SPECIALIST_SPECIALIZATION"
    ADMIN_ADD_SPECIALIST_PHONE = "ADMIN_ADD_SPECIALIST_PHONE"
    ADMIN_ADD_SPECIALIST_EMAIL = "ADMIN_ADD_SPECIALIST_EMAIL"
    ADMIN_ADD_SPECIALIST_CONFIRM = "ADMIN_ADD_SPECIALIST_CONFIRM"
    ADMIN_EDIT_SPECIALIST_SELECT = "ADMIN_EDIT_SPECIALIST_SELECT"
    ADMIN_EDIT_SPECIALIST_FIELD = "ADMIN_EDIT_SPECIALIST_FIELD"
    ADMIN_EDIT_SPECIALIST_VALUE = "ADMIN_EDIT_SPECIALIST_VALUE"
    ADMIN_DELETE_SPECIALIST_SELECT = "ADMIN_DELETE_SPECIALIST_SELECT"
    ADMIN_DELETE_SPECIALIST_CONFIRM = "ADMIN_DELETE_SPECIALIST_CONFIRM"
    ADMIN_SET_DAY_OFF_SPECIALIST = "ADMIN_SET_DAY_OFF_SPECIALIST"
    ADMIN_SET_DAY_OFF_DATE = "ADMIN_SET_DAY_OFF_DATE"
    ADMIN_SET_DAY_OFF_REASON = "ADMIN_SET_DAY_OFF_REASON"
    ADMIN_SET_DAY_OFF_CONFIRM = "ADMIN_SET_DAY_OFF_CONFIRM"


class CollectedInfo(BaseModel):
    """Data structure for collected user information during conversation."""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    phone: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    booking_date: Optional[str] = None  # YYYY-MM-DD format
    booking_time: Optional[str] = None  # HH:MM format
    booking_duration: int = 60  # minutes
    notes: Optional[str] = None


class ConversationContext(BaseModel):
    """Context for a user's conversation state and data."""

    model_config = ConfigDict(from_attributes=True)

    context_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: int
    platform: str = "telegram"  # telegram, web, etc.
    language: str = "ru"  # ru or kz
    current_state: ConversationState = ConversationState.START
    collected_info: CollectedInfo = Field(default_factory=CollectedInfo)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    last_activity: datetime = Field(default_factory=lambda: datetime.now())
    error_message: Optional[str] = None
    admin_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to dictionary."""
        data = self.model_dump()
        data["current_state"] = self.current_state.value
        # Convert datetime objects to ISO format strings
        for key in ["created_at", "updated_at", "last_activity"]:
            if isinstance(data.get(key), datetime):
                data[key] = data[key].isoformat()
        return data

    def to_json(self) -> str:
        """Serialize context to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationContext":
        """Deserialize context from dictionary."""
        data_copy = data.copy()
        if isinstance(data_copy.get("current_state"), str):
            data_copy["current_state"] = ConversationState(data_copy["current_state"])
        return cls(**data_copy)

    @classmethod
    def from_json(cls, json_str: str) -> "ConversationContext":
        """Deserialize context from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class ConversationStorage:
    """Storage service for conversation contexts with in-memory cache and DB persistence."""

    def __init__(self):
        """Initialize storage with empty in-memory cache."""
        self._cache: dict[int, ConversationContext] = {}
        self._lock = asyncio.Lock()
        logger.info("ConversationStorage initialized")

    async def load(self, user_id: int) -> Optional[ConversationContext]:
        """Load conversation context for a user.
        
        Attempts to load from in-memory cache first, then from DB if not found.
        
        Args:
            user_id: The user ID to load context for
            
        Returns:
            ConversationContext if found, None otherwise
        """
        async with self._lock:
            # Check in-memory cache
            if user_id in self._cache:
                logger.debug(f"Loaded context from cache for user {user_id}")
                return self._cache[user_id]

            # In a real implementation, this would load from DB (UserSession table)
            # For now, we return None and let the caller create a new context
            logger.debug(f"No context found in cache for user {user_id}")
            return None

    async def save(self, context: ConversationContext) -> None:
        """Save conversation context.
        
        Updates the in-memory cache. In a real implementation, this would also
        persist to the UserSession table in the database.
        
        Args:
            context: The context to save
        """
        context.updated_at = datetime.now()
        async with self._lock:
            self._cache[context.user_id] = context
            logger.debug(f"Saved context for user {context.user_id}")
            # TODO: Persist to UserSession table in DB

    async def update(
        self,
        user_id: int,
        state: Optional[ConversationState] = None,
        collected_info: Optional[CollectedInfo] = None,
        error_message: Optional[str] = None,
        admin_mode: Optional[bool] = None,
    ) -> ConversationContext:
        """Update conversation context for a user.
        
        If context doesn't exist, creates a new one. Updates only provided fields.
        
        Args:
            user_id: The user ID
            state: New conversation state (optional)
            collected_info: Updated collected info (optional)
            error_message: Error message to set (optional)
            admin_mode: Admin mode flag (optional)
            
        Returns:
            Updated ConversationContext
        """
        async with self._lock:
            context = self._cache.get(user_id)
            
            if context is None:
                # Create new context if it doesn't exist
                context = ConversationContext(user_id=user_id)
                logger.info(f"Created new context for user {user_id}")
            
            if state is not None:
                context.current_state = state
            
            if collected_info is not None:
                context.collected_info = collected_info
            
            if error_message is not None:
                context.error_message = error_message
            
            if admin_mode is not None:
                context.admin_mode = admin_mode
            
            context.updated_at = datetime.now()
            context.last_activity = datetime.now()
            self._cache[user_id] = context
            logger.debug(f"Updated context for user {user_id}")
            # TODO: Persist to UserSession table in DB
            return context

    async def transition(
        self, user_id: int, new_state: ConversationState, validate: bool = True
    ) -> ConversationContext:
        """Transition a user to a new state with validation.
        
        Args:
            user_id: The user ID
            new_state: The target state
            validate: Whether to validate the transition (default: True)
            
        Returns:
            Updated ConversationContext
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        async with self._lock:
            context = self._cache.get(user_id)
            
            if context is None:
                logger.warning(f"Cannot transition user {user_id}: context not found")
                raise StateTransitionError(
                    f"No context found for user {user_id}"
                )
            
            current_state = context.current_state
            
            if validate:
                self._validate_transition(context, new_state)
            
            logger.info(
                f"Transitioning user {user_id} from {current_state.value} to {new_state.value}"
            )
            context.current_state = new_state
            context.updated_at = datetime.now()
            context.last_activity = datetime.now()
            context.error_message = None  # Clear error on successful transition
            self._cache[user_id] = context
            # TODO: Persist to UserSession table in DB
            return context

    def _validate_transition(
        self, context: ConversationContext, new_state: ConversationState
    ) -> None:
        """Validate that a state transition is allowed.
        
        Args:
            context: The conversation context
            new_state: The target state
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        current_state = context.current_state
        info = context.collected_info

        # Cannot confirm booking without required fields
        if new_state == ConversationState.CONFIRM_BOOKING:
            missing_fields = []
            if not info.name:
                missing_fields.append("name")
            if not info.phone:
                missing_fields.append("phone")
            if not info.doctor_id:
                missing_fields.append("doctor_id")
            if not info.booking_date:
                missing_fields.append("booking_date")
            if not info.booking_time:
                missing_fields.append("booking_time")

            if missing_fields:
                raise StateTransitionError(
                    f"Cannot confirm booking without: {', '.join(missing_fields)}"
                )

        # Cannot go to DONE state without confirming booking first
        if (
            new_state == ConversationState.DONE
            and current_state != ConversationState.CONFIRM_BOOKING
        ):
            raise StateTransitionError(
                f"Cannot go to DONE state from {current_state.value}"
            )

        # Validate general state flow
        valid_transitions: dict[ConversationState, list[ConversationState]] = {
            ConversationState.START: [
                ConversationState.WAITING_NAME,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.WAITING_NAME: [
                ConversationState.WAITING_PHONE,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.WAITING_PHONE: [
                ConversationState.WAITING_DOCTOR_CHOICE,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.WAITING_DOCTOR_CHOICE: [
                ConversationState.WAITING_DATE,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.WAITING_DATE: [
                ConversationState.WAITING_TIME,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.WAITING_TIME: [
                ConversationState.CONFIRM_BOOKING,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.CONFIRM_BOOKING: [
                ConversationState.DONE,
                ConversationState.WAITING_DATE,  # Allow going back to change date/time
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.DONE: [
                ConversationState.START,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_MENU: [
                ConversationState.START,
                ConversationState.ADMIN_ADD_SPECIALIST_NAME,
                ConversationState.ADMIN_EDIT_SPECIALIST_SELECT,
                ConversationState.ADMIN_DELETE_SPECIALIST_SELECT,
                ConversationState.ADMIN_SET_DAY_OFF_SPECIALIST,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_ADD_SPECIALIST_NAME: [
                ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION: [
                ConversationState.ADMIN_ADD_SPECIALIST_PHONE,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_ADD_SPECIALIST_PHONE: [
                ConversationState.ADMIN_ADD_SPECIALIST_EMAIL,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_ADD_SPECIALIST_EMAIL: [
                ConversationState.ADMIN_ADD_SPECIALIST_CONFIRM,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_ADD_SPECIALIST_CONFIRM: [
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_EDIT_SPECIALIST_SELECT: [
                ConversationState.ADMIN_EDIT_SPECIALIST_FIELD,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_EDIT_SPECIALIST_FIELD: [
                ConversationState.ADMIN_EDIT_SPECIALIST_VALUE,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_EDIT_SPECIALIST_VALUE: [
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_DELETE_SPECIALIST_SELECT: [
                ConversationState.ADMIN_DELETE_SPECIALIST_CONFIRM,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_DELETE_SPECIALIST_CONFIRM: [
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_SET_DAY_OFF_SPECIALIST: [
                ConversationState.ADMIN_SET_DAY_OFF_DATE,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_SET_DAY_OFF_DATE: [
                ConversationState.ADMIN_SET_DAY_OFF_REASON,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_SET_DAY_OFF_REASON: [
                ConversationState.ADMIN_SET_DAY_OFF_CONFIRM,
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ADMIN_SET_DAY_OFF_CONFIRM: [
                ConversationState.ADMIN_MENU,
                ConversationState.ERROR_FALLBACK,
            ],
            ConversationState.ERROR_FALLBACK: [
                ConversationState.START,
                ConversationState.ADMIN_MENU,
            ],
        }

        allowed_states = valid_transitions.get(current_state, [])
        if new_state not in allowed_states:
            raise StateTransitionError(
                f"Invalid transition from {current_state.value} to {new_state.value}. "
                f"Allowed transitions: {[s.value for s in allowed_states]}"
            )

        logger.debug(
            f"Transition validation passed for {current_state.value} -> {new_state.value}"
        )

    async def clear(self, user_id: int) -> None:
        """Clear conversation context for a user.
        
        Args:
            user_id: The user ID to clear context for
        """
        async with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
                logger.info(f"Cleared context for user {user_id}")
            # TODO: Also clear from UserSession table in DB

    async def clear_all(self) -> None:
        """Clear all conversation contexts from memory cache."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared all {count} contexts from memory cache")

    def get_cache_size(self) -> int:
        """Get the current number of contexts in memory cache."""
        return len(self._cache)

    async def cleanup_expired(self, max_age_seconds: int = 86400) -> int:
        """Clean up expired conversation contexts (default: older than 1 day).
        
        Args:
            max_age_seconds: Maximum age of a context in seconds (default: 1 day)
            
        Returns:
            Number of contexts removed
        """
        async with self._lock:
            now = datetime.now()
            expired_users = []

            for user_id, context in self._cache.items():
                age = (now - context.last_activity).total_seconds()
                if age > max_age_seconds:
                    expired_users.append(user_id)

            for user_id in expired_users:
                del self._cache[user_id]

            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired contexts")

            return len(expired_users)


# Global storage instance
_storage: Optional[ConversationStorage] = None


def get_storage() -> ConversationStorage:
    """Get or create the global conversation storage instance."""
    global _storage
    if _storage is None:
        _storage = ConversationStorage()
    return _storage


def reset_storage() -> None:
    """Reset the global storage instance (useful for testing)."""
    global _storage
    _storage = None
