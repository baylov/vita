"""
VITA System - Main entry point for the Telegram bot.

This module initializes and runs the bot with all necessary components:
- Google Sheets Manager for data persistence
- Telegram Bot with aiogram
- Admin and Client handlers
- Health monitoring
- Error handling middleware
- Scheduled tasks (APScheduler)
"""

import asyncio
import logging
import sys
from datetime import timezone, datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

from settings import settings
from core.middleware import setup_logging, ErrorHandlingMiddleware, ContextLoggingMiddleware
from core.admin.handlers import admin_router
from core.client.handlers import client_router, initialize_services as init_client_services
from core.health import HealthMonitor, HealthChecker
from integrations.google.sheets_manager import GoogleSheetsManager
from services.gemini.client import GeminiClient
from services.gemini.analyzer import GeminiAnalyzer
from services.audio.pipeline import AudioPipeline
from services.notifications.notifier import Notifier

# Setup logging
setup_logging(log_level='INFO', log_file='logs/app.log')
logger = logging.getLogger(__name__)


class BotApplication:
    """Main application class for VITA bot."""

    def __init__(self):
        """Initialize bot application with all dependencies."""
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.sheets_manager: Optional[GoogleSheetsManager] = None
        self.gemini_analyzer: Optional[GeminiAnalyzer] = None
        self.audio_pipeline: Optional[AudioPipeline] = None
        self.notifier: Optional[Notifier] = None
        self.health_monitor: Optional[HealthMonitor] = None

    async def initialize(self) -> None:
        """Initialize all bot components."""
        logger.info("Initializing VITA Bot...")

        # Validate required settings
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured in .env")

        if not settings.google_sheets_id:
            raise ValueError("GOOGLE_SHEETS_ID not configured in .env")

        if not settings.admin_ids:
            logger.warning("⚠ ADMIN_IDS not configured - admin features will be unavailable")

        # Initialize bot
        logger.info("🤖 Initializing Telegram bot...")
        self.bot = Bot(
            token=settings.telegram_bot_token,
            session=None,  # Will use default aiohttp session
        )

        # Initialize storage and dispatcher
        storage = MemoryStorage()
        self.dp = Dispatcher(storage=storage)

        # Initialize Google Sheets Manager
        logger.info("📊 Initializing Google Sheets Manager...")
        try:
            self.sheets_manager = GoogleSheetsManager(
                spreadsheet_id=settings.google_sheets_id,
                service_account_path=settings.service_account_json_path,
            )
            # Verify connection
            specialists = self.sheets_manager.read_specialists()
            logger.info(f"✓ Sheets connected: {len(specialists)} specialists found")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize Sheets Manager: {e}")
            logger.info("  Bot will continue in limited mode")

        # Initialize Gemini Analyzer (optional)
        if settings.gemini_api_key:
            logger.info("🧠 Initializing Gemini AI...")
            try:
                gemini_client = GeminiClient(api_key=settings.gemini_api_key)
                self.gemini_analyzer = GeminiAnalyzer(client=gemini_client)
                logger.info("✓ Gemini AI initialized")
            except Exception as e:
                logger.warning(f"⚠ Could not initialize Gemini: {e}")
                logger.info("  AI features will be unavailable")
        else:
            logger.info("ℹ Gemini API key not configured - AI features disabled")

        # Initialize Audio Pipeline
        logger.info("🎙 Initializing Audio Pipeline...")
        try:
            self.audio_pipeline = AudioPipeline(
                error_logger=self.sheets_manager._log_error if self.sheets_manager else None
            )
            if self.audio_pipeline.is_available():
                logger.info("✓ Audio Pipeline initialized")
            else:
                logger.warning("⚠ Audio Pipeline not available - ffmpeg may not be installed")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize Audio Pipeline: {e}")

        # Initialize Notifier
        logger.info("📢 Initializing Notifier...")
        try:
            self.notifier = Notifier(
                bot=self.bot,
                sheets_manager=self.sheets_manager,
            )
            logger.info("✓ Notifier initialized")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize Notifier: {e}")

        # Setup client services
        logger.info("🧩 Setting up client services...")
        init_client_services(
            gemini_analyzer=self.gemini_analyzer,
            audio_pipeline=self.audio_pipeline,
            sheets_manager=self.sheets_manager,
            notifier=self.notifier,
        )

        # Add middlewares to dispatcher
        logger.info("🔧 Configuring middleware...")
        self.dp.message.middleware(ContextLoggingMiddleware())
        self.dp.callback_query.middleware(ContextLoggingMiddleware())
        self.dp.message.middleware(
            ErrorHandlingMiddleware(
                sheets_manager=self.sheets_manager,
                notifier=self.notifier,
            )
        )

        # Register routers
        logger.info("📝 Registering command handlers...")
        self.dp.include_router(admin_router)
        self.dp.include_router(client_router)

        # Initialize Health Monitor
        if self.sheets_manager and self.notifier:
            logger.info("🏥 Initializing Health Monitor...")
            try:
                health_checker = HealthChecker(
                    sheets_manager=self.sheets_manager,
                    gemini_client=self.gemini_analyzer.client if self.gemini_analyzer else None,
                )
                self.health_monitor = HealthMonitor(
                    health_checker=health_checker,
                    sheets_manager=self.sheets_manager,
                    notifier=self.notifier,
                    admin_ids=settings.admin_ids,
                    check_interval_minutes=30,
                )
                self.health_monitor.start()
                logger.info("✓ Health Monitor started (30-minute intervals)")
            except Exception as e:
                logger.warning(f"⚠ Could not initialize Health Monitor: {e}")

        logger.info("✓ Bot initialization complete!")

    async def start(self) -> None:
        """Start polling for updates."""
        if not self.bot or not self.dp:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("🚀 Starting bot polling...")
        logger.info("✓ Bot ready! Waiting for messages...")

        try:
            # Get bot info for verification
            bot_info = await self.bot.get_me()
            logger.info(f"  Bot username: @{bot_info.username}")
            logger.info(f"  Bot ID: {bot_info.id}")

            if settings.admin_ids:
                logger.info(f"  Admin IDs: {', '.join(map(str, settings.admin_ids))}")
            else:
                logger.warning("  ⚠ No admin IDs configured!")

            # Start polling
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types(),
                handle_signals=True,
            )
        except KeyboardInterrupt:
            logger.info("🛑 Bot interrupted by user")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown bot and cleanup resources."""
        logger.info("🛑 Shutting down bot...")

        # Stop health monitor
        if self.health_monitor:
            try:
                self.health_monitor.stop()
                logger.info("  ✓ Health monitor stopped")
            except Exception as e:
                logger.error(f"  Error stopping health monitor: {e}")

        # Close bot session
        if self.bot:
            try:
                await self.bot.session.close()
                logger.info("  ✓ Bot session closed")
            except Exception as e:
                logger.error(f"  Error closing bot session: {e}")

        logger.info("✓ Shutdown complete")


async def main() -> None:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("VITA System - Appointment Scheduling Bot")
    logger.info(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    app = BotApplication()

    try:
        await app.initialize()
        await app.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)
