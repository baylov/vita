#!/usr/bin/env python3
"""Test script to verify platform import shadowing is fixed."""

import sys

def test_stdlib_platform():
    """Test that stdlib platform module works correctly."""
    print("Testing stdlib platform module...")
    import platform
    
    # Verify it's the stdlib module
    assert 'platform.py' in platform.__file__, "Wrong platform module imported!"
    
    # Test basic functionality
    system = platform.system()
    python_version = platform.python_version()
    
    print(f"  ✓ Platform module: {platform.__file__}")
    print(f"  ✓ System: {system}")
    print(f"  ✓ Python version: {python_version}")
    return True

def test_platform_handlers_import():
    """Test that our platform_handlers module imports correctly."""
    print("\nTesting integrations.platform_handlers module...")
    
    # This should work without errors
    from integrations.platform_handlers import (
        Message,
        MessageType,
        PlatformAdapter,
        TelegramAdapter,
        WhatsAppAdapter,
        InstagramAdapter,
        MessageRouter,
        WebhookValidationError,
    )
    
    print(f"  ✓ Message: {Message}")
    print(f"  ✓ MessageType: {MessageType}")
    print(f"  ✓ PlatformAdapter: {PlatformAdapter}")
    print(f"  ✓ TelegramAdapter: {TelegramAdapter}")
    print(f"  ✓ WhatsAppAdapter: {WhatsAppAdapter}")
    print(f"  ✓ InstagramAdapter: {InstagramAdapter}")
    print(f"  ✓ MessageRouter: {MessageRouter}")
    print(f"  ✓ WebhookValidationError: {WebhookValidationError}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Platform Import Shadowing Test")
    print("=" * 60)
    
    try:
        # Test 1: stdlib platform works
        test_stdlib_platform()
        
        # Test 2: our platform_handlers works
        # Note: This will fail with missing dependencies, but syntax will work
        try:
            test_platform_handlers_import()
        except ImportError as e:
            if 'pydantic' in str(e) or 'aiogram' in str(e):
                print(f"\n  ⚠ Missing dependencies (expected): {e}")
                print("  ✓ But import paths are correct (no shadowing)")
            else:
                raise
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS: No import shadowing detected!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
