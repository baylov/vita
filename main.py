import sys
import os

sys.dont_write_bytecode = True

import asyncio
import logging
from pathlib import Path

import aiogram
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.config import get_settings
from core.logging import setup_logging, get_logger


logger = None


def check_startup_requirements(settings) -> bool:
    """
    Perform basic startup checks.
    
    Args:
        settings: Application settings
    
    Returns:
        True if all checks pass, False otherwise
    """
    checks_passed = True
    
    # Check for required API keys
    try:
        if not settings.api_keys.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            checks_passed = False
    except Exception as e:
        logger.error(f"Error checking TELEGRAM_BOT_TOKEN: {e}")
        checks_passed = False
    
    try:
        if not settings.api_keys.gemini_api_key:
            logger.error("GEMINI_API_KEY is not set")
            checks_passed = False
    except Exception as e:
        logger.error(f"Error checking GEMINI_API_KEY: {e}")
        checks_passed = False
    
    # Check if Google credentials file is reachable (if specified)
    if settings.api_keys.google_application_credentials:
        creds_path = Path(settings.api_keys.google_application_credentials)
        if not creds_path.exists():
            logger.warning(
                f"Google credentials file not found: {settings.api_keys.google_application_credentials}"
            )
            checks_passed = False
        else:
            logger.info(f"Google credentials file found: {creds_path}")
    
    return checks_passed


async def init_bot(settings):
    """Initialize the bot and dispatcher."""
    try:
        token = settings.api_keys.telegram_bot_token
        if not token or len(token) < 10:
            raise ValueError("Invalid bot token provided")
        
        bot = Bot(token=token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        logger.info("Bot and Dispatcher initialized successfully")
        return bot, dp
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise


async def main():
    """Main application entry point."""
    global logger
    
    try:
        # Load settings
        settings = get_settings()
        logger.info(f"Settings loaded: {settings.app_name}")
        logger.info(f"Log level: {settings.log_level}")
        logger.info(f"Database URL: {settings.database.connection_url}")
        
        # Perform startup checks
        if not check_startup_requirements(settings):
            logger.warning("Some startup checks failed, but application will continue")
        
        # Initialize bot and dispatcher
        try:
            bot, dp = await init_bot(settings)
            logger.info(f"{settings.app_name} initialized successfully")
        except Exception as e:
            logger.warning(f"Bot initialization skipped: {e}")
            logger.warning("Application will continue without bot connection")
            logger.info("(This is expected for development/testing environments)")
        
        logger.info("Application is ready. Waiting for handlers and further implementation...")
        logger.info("Application stub running (no handlers configured yet)")
        
    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Initialize logging first
    logger = setup_logging(log_level="INFO", log_dir="logs", app_name="bot")
    logger.info("VitaPlus Admin Bot starting...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
