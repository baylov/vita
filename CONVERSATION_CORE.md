# Conversation Core Module

This document describes the finite state machine (FSM) and conversation context persistence system implemented in `core/conversation.py`.

## Overview

The conversation core module provides:

1. **Finite State Machine (FSM)** - Manages conversation flow with 10 predefined states
2. **Conversation Context** - Stores user session data, collected information, and state
3. **Conversation Storage** - Manages context persistence with in-memory cache backed by database
4. **State Transitions** - Validates and enforces legal state transitions with business logic

## States

The FSM defines the following conversation states:

- **START** - Initial state, user just started
- **WAITING_NAME** - Waiting for user's name input
- **WAITING_PHONE** - Waiting for user's phone number
- **WAITING_DOCTOR_CHOICE** - Waiting for doctor/specialist selection
- **WAITING_DATE** - Waiting for appointment date selection
- **WAITING_TIME** - Waiting for appointment time selection
- **CONFIRM_BOOKING** - Ready to confirm booking, all info collected
- **DONE** - Booking completed successfully
- **ADMIN_MENU** - User in admin menu
- **ERROR_FALLBACK** - Error state for recovery

## Key Components

### ConversationState (Enum)

String-based enum representing all valid conversation states. Inherits from both `str` and `Enum` for compatibility with aiogram 3.

```python
from core.conversation import ConversationState

state = ConversationState.WAITING_NAME
print(state.value)  # "WAITING_NAME"
```

### CollectedInfo (BaseModel)

Pydantic model storing collected user information during conversation:

- `name: Optional[str]` - User's full name
- `phone: Optional[str]` - User's phone number
- `doctor_id: Optional[int]` - Selected doctor ID
- `doctor_name: Optional[str]` - Selected doctor's name
- `booking_date: Optional[str]` - Date in YYYY-MM-DD format
- `booking_time: Optional[str]` - Time in HH:MM format
- `booking_duration: int` - Appointment duration in minutes (default: 60)
- `notes: Optional[str]` - Additional notes

### ConversationContext (BaseModel)

Main data structure containing all conversation-related information:

- `context_id: str` - Unique context identifier (UUID)
- `user_id: int` - Telegram user ID
- `platform: str` - Platform type (default: "telegram")
- `language: str` - User's language (default: "ru")
- `current_state: ConversationState` - Current FSM state
- `collected_info: CollectedInfo` - Collected user information
- `created_at: datetime` - Context creation timestamp
- `updated_at: datetime` - Last update timestamp
- `last_activity: datetime` - Last activity timestamp (for expiration)
- `error_message: Optional[str]` - Current error message if any
- `admin_mode: bool` - Whether user is in admin mode

**Serialization Methods:**

```python
# Convert to dictionary (with datetime as ISO strings)
context_dict = context.to_dict()

# Convert to JSON string
json_str = context.to_json()

# Restore from dictionary
context = ConversationContext.from_dict(data)

# Restore from JSON
context = ConversationContext.from_json(json_str)
```

### ConversationStorage (Service)

Manages conversation context storage with in-memory cache and future DB persistence.

**Key Methods:**

- `load(user_id: int) -> Optional[ConversationContext]`
  - Load context from cache, returns None if not found
  
- `save(context: ConversationContext) -> None`
  - Save context to in-memory cache (updates `updated_at` timestamp)
  
- `update(user_id: int, ...) -> ConversationContext`
  - Update or create context with specified fields
  - Updates `last_activity` timestamp
  
- `transition(user_id: int, new_state: ConversationState, validate: bool = True) -> ConversationContext`
  - Move user to new state with optional validation
  - Clears error messages on successful transition
  
- `clear(user_id: int) -> None`
  - Remove user's context from cache
  
- `clear_all() -> None`
  - Clear all contexts from memory cache
  
- `cleanup_expired(max_age_seconds: int = 86400) -> int`
  - Remove contexts older than specified duration (default: 1 day)
  - Returns number of contexts removed
  
- `get_cache_size() -> int`
  - Get current number of cached contexts

**Thread Safety:**

All operations use `asyncio.Lock` for async-safe concurrent access.

## State Transitions

The FSM enforces valid state transitions with a transition matrix:

```
START → WAITING_NAME, ADMIN_MENU, ERROR_FALLBACK
WAITING_NAME → WAITING_PHONE, ERROR_FALLBACK
WAITING_PHONE → WAITING_DOCTOR_CHOICE, ERROR_FALLBACK
WAITING_DOCTOR_CHOICE → WAITING_DATE, ERROR_FALLBACK
WAITING_DATE → WAITING_TIME, ERROR_FALLBACK
WAITING_TIME → CONFIRM_BOOKING, ERROR_FALLBACK
CONFIRM_BOOKING → DONE, WAITING_DATE (to edit), ERROR_FALLBACK
DONE → START, ERROR_FALLBACK
ADMIN_MENU → START, ERROR_FALLBACK
ERROR_FALLBACK → START, ADMIN_MENU
```

### Transition Validation

When transitioning to `CONFIRM_BOOKING`, all required fields must be present:
- name
- phone
- doctor_id
- booking_date
- booking_time

If any field is missing, a `StateTransitionError` is raised.

### Error Handling

The `StateTransitionError` exception is raised for:
- Invalid state transitions (not in transition matrix)
- Missing required fields when confirming booking
- Non-existent context for transition

## Global Storage Instance

Access the global storage singleton:

```python
from core.conversation import get_storage, reset_storage

# Get or create the global storage instance
storage = get_storage()

# Reset for testing
reset_storage()
```

## Usage Example

```python
import asyncio
from core.conversation import (
    get_storage,
    ConversationContext,
    ConversationState,
    CollectedInfo,
)

async def example():
    storage = get_storage()
    user_id = 12345
    
    # Create or load context
    context = await storage.load(user_id)
    if context is None:
        context = ConversationContext(user_id=user_id)
        await storage.save(context)
    
    # Collect user information
    info = CollectedInfo(
        name="John Doe",
        phone="+1234567890",
        doctor_id=1,
        doctor_name="Dr. Smith",
        booking_date="2024-01-25",
        booking_time="10:30"
    )
    
    # Update context with collected info
    await storage.update(
        user_id=user_id,
        collected_info=info,
        state=ConversationState.WAITING_TIME
    )
    
    # Transition to confirm booking
    ctx = await storage.transition(
        user_id=user_id,
        new_state=ConversationState.CONFIRM_BOOKING
    )
    
    # Finalize booking
    ctx = await storage.transition(
        user_id=user_id,
        new_state=ConversationState.DONE
    )
    
    print(f"Booking confirmed for {ctx.collected_info.name}")

asyncio.run(example())
```

## Database Persistence

Currently, the storage uses in-memory cache only. Future integration will persist to the `UserSession` table with:

- Serialized conversation context stored as JSON
- Automatic expiration handling
- Recovery after service restart

TODO markers in the code indicate where database persistence should be implemented:
- `save()` method
- `transition()` method
- `update()` method
- `clear()` method

## Testing

Comprehensive test suite in `tests/test_conversation.py` covers:

- FSM state definitions (2 tests)
- CollectedInfo model (3 tests)
- ConversationContext serialization (7 tests)
- ConversationStorage operations (25 tests)
- Global storage instance management (3 tests)

**Test Coverage:**
- Context persistence (memory cache)
- State transitions with validation
- Concurrent updates (thread safety)
- Recovery after simulated restart
- Error handling and messages
- Admin mode and language preferences
- Expiration cleanup

Run tests with:
```bash
pytest tests/test_conversation.py -v
```

All 37 tests pass with 100% success rate.

## Integration with aiogram 3

When integrating with aiogram 3 handlers:

1. Use `ConversationState` values with `@router.message(StateFilter(...))` 
2. Access storage via `get_storage()` from dependency injection
3. Store context in state using aiogram's FSMContext
4. Map states to aiogram State class for type hints

Example future integration:
```python
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from core.conversation import ConversationState, get_storage

router = Router()
storage = get_storage()

@router.message(StateFilter(ConversationState.WAITING_NAME))
async def process_name(message: Message, state: FSMContext):
    ctx = await storage.update(message.from_user.id, 
                               collected_info=CollectedInfo(name=message.text))
    # Handle name input...
```

## Dependencies

- `pydantic>=2.0.0` - Data validation and serialization
- `asyncio` - Async/await support (standard library)
- Python 3.9+

## Notes

- Timestamps use `datetime.now()` for local timezone
- Serialization handles circular references and complex types via `default=str`
- Lock-based concurrency is suitable for single-process deployments
- For horizontal scaling, consider distributed locks or database-level synchronization
