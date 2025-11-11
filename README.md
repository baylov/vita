# VitaPlus Admin Bot

A Python-based administrator bot for VitaPlus AI, powered by Telegram integration, Google Gemini AI, and various third-party services.

## Project Structure

```
.
├── config/              # Configuration management
│   ├── __init__.py
│   └── config.py        # Settings classes and configuration loader
├── core/                # Core utilities
│   ├── __init__.py
│   └── logging.py       # Logging configuration and setup
├── services/            # Business logic and services
│   └── __init__.py
├── integrations/        # Third-party integrations
│   └── __init__.py
├── platform/            # Platform-specific logic
│   └── __init__.py
├── data/                # Data storage and models
│   └── __init__.py
├── locales/             # Localization files
│   └── __init__.py
├── logs/                # Application logs
│   └── .gitkeep
├── tests/               # Test suite
│   └── __init__.py
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
└── README.md            # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd vitaplus-admin-bot
   ```

2. **Create a Python virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and fill in the required values:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token (from BotFather)
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google service account JSON key file
   - `GOOGLE_SHEET_ID`: ID of the Google Sheet you want to work with
   - `TWILIO_SID` and `TWILIO_AUTH_TOKEN`: Twilio credentials (if using SMS features)
   - `INSTAGRAM_APP_ID` and `INSTAGRAM_APP_SECRET`: Instagram app credentials (if using Instagram integration)
   - `ADMIN_IDS`: Comma-separated list of Telegram user IDs with admin access
   - `DB_URL`: Database URL (optional, defaults to local SQLite)
   - `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - `HEALTHCHECK_INTERVAL`: Interval in seconds for health checks

5. **Prepare credentials files** (if needed):
   - If using Google services, place your service account JSON key file at the path specified in `GOOGLE_APPLICATION_CREDENTIALS`

### Running the Application

```bash
python main.py
```

The application will:
- Load configuration from `.env`
- Initialize logging to both console and rotating file logs
- Perform startup checks for required credentials
- Initialize the Telegram bot
- Log a startup message

### Development

#### Running with environment variable loading
The application uses `python-dotenv` to load environment variables from `.env` in development mode.

#### Viewing logs
- Console output: Watch the terminal for real-time logs
- File output: Check `logs/bot.log` for detailed structured JSON logs
- Log files rotate when they reach 10MB, with up to 5 backups retained

#### Database
- By default, the application uses a local SQLite database at `data/vitaplus_bot.db`
- To use a different database, set the `DB_URL` environment variable (e.g., PostgreSQL, MySQL)

## Configuration

The application uses a hierarchical configuration system with sensible defaults:

- **Database Settings**: Connection pooling, timeout, and recycling parameters
- **API Keys**: All external service credentials loaded from environment
- **Notification Settings**: Retry limits, timeouts, and health check intervals
- **Logging**: Configurable log level with console and file output

All settings are validated at startup to ensure required values are present.

## Architecture Overview

- **config/**: Application configuration and settings management
- **core/**: Core utilities including logging
- **services/**: Business logic and service implementations
- **integrations/**: Third-party service integrations (Telegram, Google, Twilio, Instagram, etc.)
- **platform/**: Platform-specific implementations
- **data/**: Data models and database-related code
- **tests/**: Unit and integration tests

## Dependencies

Key dependencies include:
- **aiogram**: Telegram bot framework
- **google-genai**: Google Gemini API client
- **sqlalchemy**: ORM and database toolkit
- **APScheduler**: Task scheduling
- **python-dotenv**: Environment variable loading
- **loguru**: Advanced logging (with fallback to stdlib logging)
- **pydantic**: Data validation and settings management

See `requirements.txt` for the complete list of dependencies and versions.

## Future Development

This is a scaffold project. Future tickets will add:
- Message handlers and command processing
- Database models and migrations
- Service implementations
- Integration workflows
- Comprehensive test coverage

## License

[To be determined]
