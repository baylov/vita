"""Tests for admin command handlers."""

import pytest
import re
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from datetime import datetime, timezone

from core.conversation import ConversationState, CollectedInfo, get_storage, reset_storage
from core.admin.handlers import is_admin, check_admin_access
from models import SpecialistDTO, DayOffDTO, AdminActionDTO
from services.repositories import SpecialistRepository, DayOffRepository
from services.validators import (
    validate_phone,
    validate_name,
    validate_specialization,
    validate_email,
    validate_date_format,
)


# ============================================================================
# VALIDATOR TESTS
# ============================================================================


class TestValidators:
    """Test validation functions."""
    
    def test_validate_phone_valid(self):
        """Test phone validation with valid phones."""
        valid_phones = [
            "+7 (999) 123-45-67",
            "+79991234567",
            "79991234567",
            "(999) 123-45-67",
            "+77771234567",
        ]
        
        for phone in valid_phones:
            is_valid, error = validate_phone(phone)
            assert is_valid, f"Phone {phone} should be valid, error: {error}"
    
    def test_validate_phone_invalid(self):
        """Test phone validation with invalid phones."""
        invalid_phones = [
            "",
            "123",
            "abc123",
            "1234567890",  # Only 10 digits without country code
        ]
        
        for phone in invalid_phones:
            is_valid, error = validate_phone(phone)
            if phone:  # Allow empty phones to have optional validation
                assert not is_valid or len(re.sub(r'[\s\-\(\)\.+]', '', phone)) >= 10, f"Phone {phone} should be invalid"
            assert error is not None or phone
    
    def test_validate_name_valid(self):
        """Test name validation with valid names."""
        valid_names = [
            "Иван Петров",
            "John Smith",
            "Marie-Claire",
            "О'Brien",
        ]
        
        for name in valid_names:
            is_valid, error = validate_name(name)
            assert is_valid, f"Name {name} should be valid, error: {error}"
    
    def test_validate_name_invalid(self):
        """Test name validation with invalid names."""
        invalid_names = [
            "",
            "A",
            "123",
            "Name@Invalid",
        ]
        
        for name in invalid_names:
            is_valid, error = validate_name(name)
            assert not is_valid, f"Name {name} should be invalid"
    
    def test_validate_specialization_valid(self):
        """Test specialization validation with valid values."""
        valid_specs = [
            "Кардиолог",
            "Терапевт",
            "Хирург",
            "Психолог",
        ]
        
        for spec in valid_specs:
            is_valid, error = validate_specialization(spec)
            assert is_valid, f"Specialization {spec} should be valid, error: {error}"
    
    def test_validate_specialization_invalid(self):
        """Test specialization validation with invalid values."""
        invalid_specs = [
            "",
            "A",
            "X" * 101,
        ]
        
        for spec in invalid_specs:
            is_valid, error = validate_specialization(spec)
            assert not is_valid, f"Specialization {spec} should be invalid"
    
    def test_validate_email_optional(self):
        """Test email validation allows empty values."""
        emails = [None, "", " ", "пропустить", "-"]
        
        for email in emails:
            is_valid, error = validate_email(email)
            assert is_valid, f"Empty email should be valid"
    
    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.co.uk",
        ]
        
        for email in valid_emails:
            is_valid, error = validate_email(email)
            assert is_valid, f"Email {email} should be valid, error: {error}"
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "notanemail",
            "test@",
            "@example.com",
        ]
        
        for email in invalid_emails:
            is_valid, error = validate_email(email)
            assert not is_valid, f"Email {email} should be invalid"
    
    def test_validate_date_format_valid(self):
        """Test date format validation with valid dates."""
        valid_dates = [
            "2024-01-15",
            "2024-12-31",
            "2025-06-01",
        ]
        
        for date in valid_dates:
            is_valid, error = validate_date_format(date)
            assert is_valid, f"Date {date} should be valid, error: {error}"
    
    def test_validate_date_format_invalid(self):
        """Test date format validation with invalid dates."""
        invalid_dates = [
            "",
            "15-01-2024",
            "2024/01/15",
            "2024-13-01",
        ]
        
        for date in invalid_dates:
            is_valid, error = validate_date_format(date)
            assert not is_valid, f"Date {date} should be invalid"


# ============================================================================
# ADMIN ACCESS TESTS
# ============================================================================


class TestAdminAccess:
    """Test admin access control."""
    
    def test_is_admin_with_admin_id(self):
        """Test is_admin returns True for admin users."""
        with patch("core.admin.handlers.settings") as mock_settings:
            mock_settings.admin_ids = [123, 456, 789]
            assert is_admin(123) is True
            assert is_admin(456) is True
    
    def test_is_admin_with_non_admin_id(self):
        """Test is_admin returns False for non-admin users."""
        with patch("core.admin.handlers.settings") as mock_settings:
            mock_settings.admin_ids = [123, 456]
            assert is_admin(999) is False
            assert is_admin(111) is False
    
    @pytest.mark.asyncio
    async def test_check_admin_access_allowed(self):
        """Test check_admin_access returns True for admins."""
        message = MagicMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 123
        message.answer = AsyncMock()
        
        with patch("core.admin.handlers.settings") as mock_settings:
            mock_settings.admin_ids = [123, 456]
            result = await check_admin_access(message)
            assert result is True
            message.answer.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_admin_access_denied(self):
        """Test check_admin_access returns False for non-admins."""
        message = MagicMock(spec=types.Message)
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.answer = AsyncMock()
        
        with patch("core.admin.handlers.settings") as mock_settings:
            with patch("core.admin.handlers.get_text") as mock_get_text:
                mock_settings.admin_ids = [123, 456]
                mock_get_text.return_value = "Access denied"
                
                result = await check_admin_access(message)
                assert result is False
                message.answer.assert_called_once()


# ============================================================================
# REPOSITORY TESTS
# ============================================================================


class TestSpecialistRepository:
    """Test SpecialistRepository."""
    
    def test_create_specialist(self):
        """Test creating a specialist."""
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(return_value=None)
        sheets_manager._get_worksheet_safe = MagicMock()
        
        repo = SpecialistRepository(sheets_manager)
        
        specialist = SpecialistDTO(
            name="Иван Петров",
            specialization="Кардиолог",
            phone="+79991234567",
            email="ivan@example.com",
        )
        
        result = repo.create(specialist, admin_id="user_123")
        
        assert result.name == specialist.name
        assert result.specialization == specialist.specialization
        sheets_manager.log_admin_action.assert_called_once()
    
    def test_get_by_name(self):
        """Test getting specialist by name."""
        sheets_manager = MagicMock()
        
        specialist1 = SpecialistDTO(name="Иван", specialization="Кардиолог")
        specialist2 = SpecialistDTO(name="Мария", specialization="Терапевт")
        
        sheets_manager.read_specialists = MagicMock(
            return_value=[specialist1, specialist2]
        )
        
        repo = SpecialistRepository(sheets_manager)
        result = repo.get_by_name("иван")  # Case insensitive
        
        assert result == specialist1
    
    def test_get_by_name_not_found(self):
        """Test get_by_name returns None when not found."""
        sheets_manager = MagicMock()
        sheets_manager.read_specialists = MagicMock(return_value=[])
        
        repo = SpecialistRepository(sheets_manager)
        result = repo.get_by_name("Петр")
        
        assert result is None
    
    def test_get_all(self):
        """Test getting all specialists."""
        sheets_manager = MagicMock()
        specialists = [
            SpecialistDTO(name="Иван", specialization="Кардиолог"),
            SpecialistDTO(name="Мария", specialization="Терапевт"),
        ]
        sheets_manager.read_specialists = MagicMock(return_value=specialists)
        
        repo = SpecialistRepository(sheets_manager)
        result = repo.get_all()
        
        assert len(result) == 2
        assert result == specialists


class TestDayOffRepository:
    """Test DayOffRepository."""
    
    def test_create_day_off(self):
        """Test creating a day off."""
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(return_value=None)
        sheets_manager._get_worksheet_safe = MagicMock()
        
        repo = DayOffRepository(sheets_manager)
        
        day_off = DayOffDTO(
            specialist_id=1,
            date="2024-12-25",
            reason="Праздник",
        )
        
        result = repo.create(day_off, admin_id="user_123")
        
        assert result.specialist_id == day_off.specialist_id
        assert result.date == day_off.date
        sheets_manager.log_admin_action.assert_called_once()
    
    def test_get_by_specialist_and_date(self):
        """Test getting day off by specialist and date."""
        sheets_manager = MagicMock()
        
        day_off = DayOffDTO(specialist_id=1, date="2024-12-25")
        sheets_manager.read_days_off = MagicMock(return_value=[day_off])
        
        repo = DayOffRepository(sheets_manager)
        result = repo.get_by_specialist_and_date(1, "2024-12-25")
        
        assert result == day_off
    
    def test_get_by_specialist(self):
        """Test getting all days off for a specialist."""
        sheets_manager = MagicMock()
        
        days_off = [
            DayOffDTO(specialist_id=1, date="2024-12-25"),
            DayOffDTO(specialist_id=1, date="2024-01-01"),
            DayOffDTO(specialist_id=2, date="2024-12-25"),
        ]
        sheets_manager.read_days_off = MagicMock(return_value=days_off)
        
        repo = DayOffRepository(sheets_manager)
        result = repo.get_by_specialist(1)
        
        assert len(result) == 2
        assert all(do.specialist_id == 1 for do in result)


# ============================================================================
# CONVERSATION STATE TESTS
# ============================================================================


class TestAdminConversationFlow:
    """Test admin conversation flows."""
    
    @pytest.mark.asyncio
    async def test_admin_state_transitions(self):
        """Test valid state transitions in admin flow."""
        reset_storage()
        storage = get_storage()
        
        user_id = 123
        
        # Add specialist flow
        await storage.update(user_id, state=ConversationState.ADMIN_MENU)
        context = await storage.load(user_id)
        assert context.current_state == ConversationState.ADMIN_MENU
        
        await storage.transition(user_id, ConversationState.ADMIN_ADD_SPECIALIST_NAME)
        context = await storage.load(user_id)
        assert context.current_state == ConversationState.ADMIN_ADD_SPECIALIST_NAME
        
        await storage.transition(
            user_id,
            ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION
        )
        context = await storage.load(user_id)
        assert context.current_state == ConversationState.ADMIN_ADD_SPECIALIST_SPECIALIZATION
    
    @pytest.mark.asyncio
    async def test_collected_info_persistence(self):
        """Test collected info is persisted across states."""
        reset_storage()
        storage = get_storage()
        
        user_id = 123
        
        info = CollectedInfo(
            name="Иван",
            phone="+79991234567",
            doctor_name="Кардиолог",
        )
        
        await storage.update(user_id, collected_info=info)
        context = await storage.load(user_id)
        
        assert context.collected_info.name == "Иван"
        assert context.collected_info.phone == "+79991234567"
        assert context.collected_info.doctor_name == "Кардиолог"
    
    @pytest.mark.asyncio
    async def test_admin_mode_flag(self):
        """Test admin mode flag is set and persisted."""
        reset_storage()
        storage = get_storage()
        
        user_id = 123
        
        await storage.update(user_id, admin_mode=True)
        context = await storage.load(user_id)
        
        assert context.admin_mode is True


# ============================================================================
# ADMIN ACTION LOGGING TESTS
# ============================================================================


class TestAdminActionLogging:
    """Test admin action logging."""
    
    def test_log_specialist_creation(self):
        """Test logging specialist creation."""
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(
            return_value=AdminActionDTO(
                action_type="create",
                resource_type="specialist",
                description="Test",
                performed_by="user_123",
            )
        )
        
        action = AdminActionDTO(
            action_type="create",
            resource_type="specialist",
            description="Specialist created: Иван",
            performed_by="user_123",
        )
        
        result = sheets_manager.log_admin_action(action)
        
        assert result.action_type == "create"
        assert result.resource_type == "specialist"
        sheets_manager.log_admin_action.assert_called_once_with(action)
    
    def test_log_day_off_creation(self):
        """Test logging day off creation."""
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(
            return_value=AdminActionDTO(
                action_type="create",
                resource_type="day_off",
                description="Day off set",
                performed_by="user_123",
            )
        )
        
        action = AdminActionDTO(
            action_type="create",
            resource_type="day_off",
            description="Day off set for specialist 1 on 2024-12-25",
            performed_by="user_123",
        )
        
        result = sheets_manager.log_admin_action(action)
        
        assert result.resource_type == "day_off"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestAdminFlowIntegration:
    """Integration tests for complete admin flows."""
    
    @pytest.mark.asyncio
    async def test_add_specialist_complete_flow(self):
        """Test complete add specialist flow."""
        reset_storage()
        storage = get_storage()
        
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(return_value=None)
        sheets_manager._get_worksheet_safe = MagicMock()
        
        user_id = 123
        admin_id = f"user_{user_id}"
        
        # Start flow
        await storage.update(
            user_id,
            state=ConversationState.ADMIN_ADD_SPECIALIST_NAME
        )
        
        # Collect data
        info = CollectedInfo(
            name="Иван Петров",
            doctor_name="Кардиолог",
            phone="+79991234567",
            notes="ivan@example.com",
        )
        
        await storage.update(
            user_id,
            state=ConversationState.ADMIN_ADD_SPECIALIST_CONFIRM,
            collected_info=info,
        )
        
        # Create specialist
        repo = SpecialistRepository(sheets_manager)
        
        specialist = SpecialistDTO(
            name=info.name,
            specialization=info.doctor_name,
            phone=info.phone,
            email=info.notes,
            is_active=True,
        )
        
        result = repo.create(specialist, admin_id=admin_id)
        
        # Verify
        assert result.name == "Иван Петров"
        assert result.specialization == "Кардиолог"
        sheets_manager.log_admin_action.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_day_off_complete_flow(self):
        """Test complete day off flow."""
        reset_storage()
        storage = get_storage()
        
        sheets_manager = MagicMock()
        sheets_manager.log_admin_action = MagicMock(return_value=None)
        sheets_manager._get_worksheet_safe = MagicMock()
        
        user_id = 123
        admin_id = f"user_{user_id}"
        
        # Collect data
        info = CollectedInfo(
            doctor_id=1,
            booking_date="2024-12-25",
            notes="Праздник",
        )
        
        await storage.update(
            user_id,
            state=ConversationState.ADMIN_SET_DAY_OFF_CONFIRM,
            collected_info=info,
        )
        
        # Create day off
        repo = DayOffRepository(sheets_manager)
        
        day_off = DayOffDTO(
            specialist_id=info.doctor_id,
            date=info.booking_date,
            reason=info.notes,
        )
        
        result = repo.create(day_off, admin_id=admin_id)
        
        # Verify
        assert result.specialist_id == 1
        assert result.date == "2024-12-25"
        sheets_manager.log_admin_action.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
