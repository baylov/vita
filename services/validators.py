"""Validators for admin operations."""

import re
from typing import Optional


def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate phone number format.
    
    Accepts formats like:
    - +7 (999) 123-45-67
    - +79991234567
    - 79991234567
    - (999) 123-45-67
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Номер телефона не может быть пустым"
    
    # Remove common separators and spaces
    cleaned = re.sub(r'[\s\-\(\)\.+]', '', phone)
    
    # Must contain only digits
    if not cleaned.isdigit():
        return False, "Номер телефона должен содержать только цифры и разделители"
    
    # Check length - Kazakhstan/Russia numbers are typically 10-11 digits
    # Allow 10-12 digits (with possible country codes)
    if len(cleaned) < 10 or len(cleaned) > 12:
        return False, "Номер телефона должен быть от 10 до 12 цифр"
    
    # Check for Kazakhstan/Russia numbers (starting with 7, 8, or just digits)
    if len(cleaned) > 11:
        # If more than 11 digits, it should start with country code (7)
        if not cleaned.startswith('7'):
            return False, "Формат номера должен соответствовать Казахстану/России"
    
    return True, None


def validate_specialization(specialization: str) -> tuple[bool, Optional[str]]:
    """
    Validate specialization name.
    
    Args:
        specialization: Specialization name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not specialization or not specialization.strip():
        return False, "Специализация не может быть пустой"
    
    # Check length
    if len(specialization) < 2:
        return False, "Специализация должна быть не менее 2 символов"
    
    if len(specialization) > 100:
        return False, "Специализация не может быть более 100 символов"
    
    return True, None


def validate_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate specialist name.
    
    Args:
        name: Name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Имя не может быть пустым"
    
    # Check length
    if len(name) < 2:
        return False, "Имя должно быть не менее 2 символов"
    
    if len(name) > 100:
        return False, "Имя не может быть более 100 символов"
    
    # Allow letters (Cyrillic and Latin), spaces, hyphens, and apostrophes
    # Pattern: Russian letters (а-яёА-ЯЁ), Latin letters (a-zA-Z), spaces, hyphens, apostrophes
    if not re.match(r"^[а-яёА-ЯЁa-zA-Z\s\-']+$", name):
        return False, "Имя может содержать только буквы, пробелы, дефисы и апострофы"
    
    return True, None


def validate_email(email: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate email address (optional field).
    
    Args:
        email: Email to validate (can be None/empty)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not email.strip():
        return True, None  # Email is optional
    
    # Check if it's a skip marker
    if email.strip().lower() in ["skip", "пропустить", "-"]:
        return True, None  # Treat as optional
    
    # Simple email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Некорректный формат email"
    
    return True, None


def validate_time_format(time_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate time format (HH:MM).
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not time_str:
        return False, "Время не может быть пустым"
    
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid format")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        
        if hours < 0 or hours > 23:
            return False, "Часы должны быть от 0 до 23"
        
        if minutes < 0 or minutes > 59:
            return False, "Минуты должны быть от 0 до 59"
        
        return True, None
    except (ValueError, IndexError):
        return False, "Время должно быть в формате HH:MM"


def validate_date_format(date_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate date format (YYYY-MM-DD).
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return False, "Дата не может быть пустой"
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, "Дата должна быть в формате YYYY-MM-DD"


def validate_working_hours(start_time: str, end_time: str) -> tuple[bool, Optional[str]]:
    """
    Validate working hours (start < end).
    
    Args:
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    start_valid, start_error = validate_time_format(start_time)
    if not start_valid:
        return False, f"Время начала: {start_error}"
    
    end_valid, end_error = validate_time_format(end_time)
    if not end_valid:
        return False, f"Время конца: {end_error}"
    
    # Convert to minutes for comparison
    start_h, start_m = map(int, start_time.split(':'))
    end_h, end_m = map(int, end_time.split(':'))
    
    start_mins = start_h * 60 + start_m
    end_mins = end_h * 60 + end_m
    
    if start_mins >= end_mins:
        return False, "Время начала должно быть раньше времени конца"
    
    return True, None
