# VITA System - Appointment Scheduling Bot

A robust bi-directional Google Sheets integration bot for appointment scheduling with multi-channel support (Telegram, WhatsApp, Instagram). The system provides comprehensive CRUD operations, AI-powered analysis, audio transcription, and error handling with automatic failover to manual mode.

## Features

- **Google Sheets Integration**: Secure bi-directional synchronization with Google Sheets
- **Telegram Bot**: Full aiogram integration for command routing and callback handling
- **Multi-Channel Support**: WhatsApp (Twilio) and Instagram (Facebook Graph API) adapters
- **Speech-to-Text**: Audio transcription for voice messages (Russian and Kazakh)
- **AI Analysis**: Google Gemini integration for intent classification and response generation
- **Internationalization (i18n)**: Full Russian (RU) and Kazakh (KZ) language support
- **Admin Management**: Dedicated admin interface for specialist and booking management
- **Error Handling**: Custom exception hierarchy with retry decorators and middleware logging
- **Health Monitoring**: Periodic health checks for Sheets and Gemini with admin notifications
- **Graceful Degradation**: Manual mode fallback when services become unavailable
- **Audit Logging**: Comprehensive logging of all administrative actions and errors

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher (3.11 recommended)
- **ffmpeg**: For audio format conversion (required for voice message support)
- **PostgreSQL**: 12 or higher (for conversation persistence, optional)
- **Docker & Docker Compose**: For containerized deployment (optional)

### External Services (Required)

1. **Google Cloud Project** with:
   - Service Account with credentials (JSON key)
   - Sheets API enabled
   - Cloud Speech-to-Text API enabled (for audio transcription)

2. **Telegram Bot Token** from BotFather

3. **Google Gemini API Key** (optional, for AI-powered analysis)

### External Services (Optional)

- **Twilio Account**: For WhatsApp integration
- **Meta/Facebook App**: For Instagram integration

## Quick Start

### Automated Setup

```bash
# Clone the repository and navigate to it
git clone <repository_url>
cd vita-system

# Run setup script (creates venv, installs deps, configures .env)
bash setup.sh

# Activate virtual environment
source venv/bin/activate

# Edit configuration
nano .env

# Run the bot
python -m core.main
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg libffi-dev

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python -m core.main
```

## Environment Configuration

### Creating `.env` File

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
nano .env
```

### Required Settings

```env
# Google Sheets (REQUIRED)
SERVICE_ACCOUNT_JSON_PATH=service_account.json
GOOGLE_SHEETS_ID=your_spreadsheet_id_here

# Telegram Bot (REQUIRED)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Admin Configuration (REQUIRED)
ADMIN_IDS=123456789,987654321  # Comma-separated Telegram user IDs

# Google Cloud (for audio transcription)
GOOGLE_APPLICATION_CREDENTIALS=service_account.json
```

### Optional Settings

```env
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Audio Processing
TRANSCRIPTION_TIMEOUT=60

# Notification Service
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY_MIN=2
NOTIFICATION_RETRY_DELAY_MAX=10

# Scheduled Digest (default: 8:00 AM)
DIGEST_SCHEDULE_HOUR=8
DIGEST_SCHEDULE_MINUTE=0

# WhatsApp (Twilio)
WHATSAPP_ACCOUNT_SID=your_twilio_account_sid
WHATSAPP_AUTH_TOKEN=your_twilio_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+1234567890

# Instagram (Facebook Graph API)
INSTAGRAM_PAGE_ACCESS_TOKEN=your_instagram_page_access_token
INSTAGRAM_APP_SECRET=your_instagram_app_secret
INSTAGRAM_VERIFY_TOKEN=your_instagram_verify_token
```

## Google Service Account Setup

### Step 1: Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **Service Accounts** (IAM & Admin → Service Accounts)
4. Click **Create Service Account**
5. Fill in the account name and description
6. Click **Create and Continue**

### Step 2: Grant Permissions

1. In the "Grant this service account access to project" section, grant:
   - **Editor** role (or specific: Sheets Editor, Cloud Speech Admin)
2. Click **Continue** and then **Done**

### Step 3: Create and Download Key

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create** - the file downloads automatically
6. Move the downloaded file to your project directory:
   ```bash
   mv ~/Downloads/service_account.json ./service_account.json
   ```

### Step 4: Share Google Sheet

1. Copy your Google Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
2. Go to **Share** button
3. Add the service account email (looks like: `account-name@project-id.iam.gserviceaccount.com`)
4. Give **Editor** permissions
5. Update `GOOGLE_SHEETS_ID` in `.env`

### Step 5: Verify Setup

```python
from integrations.google.sheets_manager import GoogleSheetsManager

manager = GoogleSheetsManager(
    spreadsheet_id="your_sheet_id",
    service_account_path="service_account.json"
)
specialists = manager.read_specialists()
print(f"Found {len(specialists)} specialists")
```

## Telegram Webhook Configuration

### Option 1: Local Development (Polling)

The bot runs in polling mode by default:

```bash
python -m core.main
```

### Option 2: Production (Webhook)

Set up webhook for better performance:

1. **Ensure bot is accessible from internet** with HTTPS
2. **Configure in `.env`**:
   ```env
   WEBHOOK_URL=https://your-domain.com/webhook/telegram
   WEBHOOK_PORT=8000
   ```
3. **Set webhook with Telegram API**:
   ```bash
   curl -F "url=https://your-domain.com/webhook/telegram" \
        -F "certificate=@certificate.pem" \
        https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook
   ```
4. **Run bot** with webhook handler enabled

See [Telegram Bot API Documentation](https://core.telegram.org/bots/api#setwebhook) for details.

## Telegram Bot Setup

### Getting Your Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name and username for your bot
4. BotFather will give you a token like: `123456789:ABCdefGHIjklmnOPQRstuvWXYZabcdefGH`
5. Copy this token to `.env` as `TELEGRAM_BOT_TOKEN`

### Setting Admin IDs

1. Search for **@userinfobot** in Telegram
2. Send `/start` and your user ID will be displayed
3. Add this ID to `.env` as `ADMIN_IDS=123456789`
4. For multiple admins: `ADMIN_IDS=123456789,987654321,555555555`

### Testing Your Bot

1. Search for your bot by username in Telegram
2. Send `/start` - you should receive a greeting
3. Send `/admin` - admin commands (if you're in ADMIN_IDS)
4. Send `/help` - help information

## WhatsApp Integration (Optional)

### Setup Instructions

1. **Create Twilio Account**: https://www.twilio.com/
2. **Enable WhatsApp Sandbox**:
   - Go to Messaging → WhatsApp → Learn
   - Click "Get Started" under Sandbox
   - Join sandbox with provided code
3. **Get Credentials**:
   - Account SID (under Account Info)
   - Auth Token (under Account Info)
   - WhatsApp phone number (in Sandbox settings)
4. **Configure `.env`**:
   ```env
   WHATSAPP_ACCOUNT_SID=your_account_sid
   WHATSAPP_AUTH_TOKEN=your_auth_token
   WHATSAPP_FROM_NUMBER=whatsapp:+1234567890
   ```
5. **Set Webhook**: In Twilio Console, set webhook to `https://your-domain.com/webhook/whatsapp`

## Instagram Integration (Optional)

### Setup Instructions

1. **Create Meta Business Account**: https://business.facebook.com/
2. **Create App**: Go to Developers → My Apps → Create App
3. **Get Credentials**:
   - App ID and App Secret (Settings → Basic)
   - Generate access token (Tools → Access Token Generator)
4. **Configure `.env`**:
   ```env
   INSTAGRAM_PAGE_ACCESS_TOKEN=your_page_access_token
   INSTAGRAM_APP_SECRET=your_app_secret
   INSTAGRAM_VERIFY_TOKEN=your_verify_token
   ```
5. **Set Webhook**: In Meta App, set webhook to `https://your-domain.com/webhook/instagram`

## Docker Deployment

### Building and Running

```bash
# Build image
docker build -t vita-bot .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Docker Compose Services

The `docker-compose.yml` includes:

- **bot**: Main Telegram bot service
- **db**: PostgreSQL database for conversation persistence
- **redis** (optional): Redis for distributed conversation caching

### Volume Mounts

- `./service_account.json`: Google credentials (read-only)
- `./.env`: Configuration file (read-only)
- `./logs`: Application logs (persistent)
- `db_data`: Database storage (persistent)

### First Run with Docker

```bash
# Create .env file
cp .env.example .env
# Edit with your credentials
nano .env

# Place Google credentials
cp ~/Downloads/service_account.json ./

# Start services
docker-compose up -d

# Verify bot is running
docker-compose logs bot | grep "Bot started"

# Check health
docker-compose ps
```

## Health Checks and Monitoring

### Built-in Health Monitoring

The system performs automatic health checks every 30 minutes:

```python
from core.health import HealthMonitor, HealthChecker

# Initialize
checker = HealthChecker(sheets_manager, gemini_client)
monitor = HealthMonitor(
    health_checker=checker,
    sheets_manager=sheets_manager,
    notifier=notifier,
    admin_ids=[123456789],
    check_interval_minutes=30
)

# Start monitoring
monitor.start()
```

### Checking Individual Services

```python
# Manual health check
from core.health import HealthChecker

checker = HealthChecker(sheets_manager, gemini_client)
status = await checker.perform_all_checks()

for service, result in status.checks.items():
    print(f"{service}: {'✓' if result.healthy else '✗'} ({result.response_time_ms}ms)")
```

### Health Status Indicators

- **Green**: All services operational
- **Yellow**: One service degraded but functioning
- **Red**: Critical service failure (manual intervention needed)

When degradation is detected, admins are notified via Telegram with:
- Affected service
- Error details
- Last working timestamp
- Manual intervention steps

## APScheduler Background Execution

### Automatic Tasks

The system uses APScheduler for:

1. **Scheduled Digest Notifications** (daily at 8:00 AM by default)
   - Collects pending booking confirmations
   - Sends summary to administrators
   - Configured via `DIGEST_SCHEDULE_HOUR` and `DIGEST_SCHEDULE_MINUTE`

2. **Health Checks** (every 30 minutes)
   - Verifies Sheets API connectivity
   - Verifies Gemini API connectivity
   - Notifies admins if degradation detected

### Custom Scheduled Tasks

To add custom scheduled tasks:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

# Add a custom job
scheduler.add_job(
    your_async_function,
    IntervalTrigger(hours=1),
    name='your_job_name'
)

scheduler.start()
```

## Admin Configuration

### Creating Admin User

1. Get your Telegram user ID using @userinfobot
2. Add to `ADMIN_IDS` environment variable:
   ```env
   ADMIN_IDS=123456789
   ```
3. Restart the bot
4. Send `/admin` command to access admin interface

### Admin Commands

```
/admin       - Show admin menu with all options
/help        - Show help information
/status      - Check bot and service status
/add_spec    - Add new specialist (multi-step dialog)
/edit_spec   - Edit existing specialist
/del_spec    - Delete specialist
/day_off     - Set specialist day off
/bookings    - View all pending bookings
/logs        - View error logs
/sync        - Manually trigger data sync
```

### Admin Actions

Admins can:
- Add/edit/delete specialists
- Set day-offs for specialists
- View pending bookings
- View error logs with filtering
- Manually sync data
- Monitor bot health
- View conversation logs

All admin actions are logged to the "Логи Админа" sheet for audit purposes.

## Log Locations

### Local Deployment

- **Application logs**: `./logs/app.log`
- **Error logs**: `./logs/errors.log`
- **Admin actions**: Logged to Google Sheets "Логи Админа" worksheet
- **System errors**: Logged to Google Sheets "Ошибки" worksheet

### Docker Deployment

```bash
# View bot logs
docker-compose logs bot

# View database logs
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f bot

# View specific time range
docker-compose logs --since 2025-01-15 bot
```

### Log Levels

Configure in `.env` or when initializing logging:

```python
from core.middleware import setup_logging

# Set to DEBUG for verbose output
setup_logging(log_level='DEBUG', log_file='logs/app.log')
```

## Troubleshooting

### Bot Not Responding

1. **Check token is correct**:
   ```bash
   curl https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe
   ```

2. **Verify admin IDs**:
   ```env
   ADMIN_IDS=123456789  # Must be valid Telegram user ID
   ```

3. **Check logs**:
   ```bash
   tail -f logs/app.log
   ```

### Audio Transcription Not Working

**Issue**: Voice messages not being transcribed

**Solutions**:
1. **Install ffmpeg**:
   ```bash
   sudo apt-get install ffmpeg
   ```

2. **Verify Google Cloud Speech API is enabled**:
   - Go to Google Cloud Console
   - Enable "Cloud Speech-to-Text API"
   - Service account has proper permissions

3. **Check credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=service_account.json
   gcloud auth application-default print-access-token
   ```

### Google Sheets Connection Error

**Issue**: `SheetsInitializationError: Failed to connect to Sheets`

**Solutions**:
1. **Verify service account JSON exists**:
   ```bash
   ls -la service_account.json
   ```

2. **Check Sheet is shared with service account**:
   - Get service account email from JSON file
   - Open Google Sheet → Share → Add email with Editor access

3. **Verify Sheet ID is correct**:
   - Copy from URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
   - Update `GOOGLE_SHEETS_ID` in `.env`

4. **Check API is enabled**:
   - Google Cloud Console → APIs & Services → Sheets API
   - Ensure it's enabled for your project

### Gemini AI Not Available

**Issue**: AI analysis falling back to manual mode

**Solutions**:
1. **Check API key is set**:
   ```bash
   echo $GEMINI_API_KEY
   ```

2. **Verify API is enabled**:
   - Go to Google AI Studio: https://ai.google.dev/
   - Create API key if needed

3. **Check quota limits**:
   - Gemini has rate limits, check Google Cloud Console

### Health Check Failures

**Issue**: Health monitor reports service failures

**Solutions**:
1. **Check network connectivity**:
   ```bash
   curl -I https://www.googleapis.com/sheets/v4/
   ```

2. **Verify credentials and permissions**:
   - Service account has all required roles
   - Sheets/APIs are properly enabled

3. **Review logs for specific errors**:
   ```bash
   grep "health\|Health" logs/app.log
   ```

### Manual Mode - Service Unavailable

**Issue**: Bot falling back to manual mode, admin notifications needed

**When it happens**:
- Sheets API down (bookings can't be saved)
- Gemini API down (AI classification unavailable)
- Audio transcription fails (voice messages can't be processed)

**How to handle**:
1. **Admin receives notification** with error details
2. **Bot continues accepting bookings** but marks as pending manual review
3. **Admin can manually sync** when services are restored:
   ```
   /admin → Sync Data
   ```

### Database Connection Issues (Docker)

**Issue**: `Error connecting to database`

**Solutions**:
1. **Check PostgreSQL is running**:
   ```bash
   docker-compose ps
   ```

2. **Verify database initialization**:
   ```bash
   docker-compose logs db
   ```

3. **Check database credentials match**:
   - `docker-compose.yml` environment variables
   - `.env` database settings (if used)

4. **Reset database** (loses all data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_client_handlers.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Coverage

The project includes comprehensive tests:

- **Sheets Manager**: CRUD operations, sync, retry logic
- **Admin Handlers**: Specialist management, booking operations
- **Client Handlers**: Booking flow, voice message handling, conflict detection
- **Platform Adapters**: Telegram, WhatsApp, Instagram
- **Notifications**: Multi-channel delivery, urgency routing
- **Audio Pipeline**: Format conversion, transcription
- **Error Handling**: Exceptions, middleware, health monitoring
- **i18n**: Language detection, translation

## Installation from Source

### Requirements for Development

```bash
# Clone repository
git clone <repository_url>
cd vita-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Configuration Validation

### Pre-deployment Checklist

```bash
# 1. Verify Python version
python --version  # Should be 3.9+

# 2. Check dependencies
python -c "import pydantic, aiogram, gspread; print('✓ Core deps installed')"

# 3. Verify environment
cat .env | grep -E "TELEGRAM_BOT_TOKEN|GOOGLE_SHEETS_ID|ADMIN_IDS"

# 4. Test Sheets connection
python -c "from integrations.google.sheets_manager import GoogleSheetsManager; \
           m = GoogleSheetsManager('YOUR_SHEET_ID', 'service_account.json'); \
           print(f'✓ Sheets connected: {len(m.read_specialists())} specialists')"

# 5. Test Telegram token
curl https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe | python -m json.tool

# 6. Run tests
pytest -q
```

## Performance Optimization

### Caching

The system uses LRU caching for classifications to reduce Gemini API calls:

```python
from services.gemini.analyzer import GeminiAnalyzer

# Cache TTL configurable (default: 1 hour)
analyzer = GeminiAnalyzer(cache_ttl_minutes=60)
```

### Async Operations

All external API calls are async for better concurrency:

```python
# Parallel booking operations
await asyncio.gather(
    notifier.notify_admin(booking),
    sheets_manager.add_booking(booking),
)
```

### Database Optimization

Use PostgreSQL for better performance with multiple concurrent users:

```yaml
# In docker-compose.yml, PostgreSQL is already configured
# For local dev, use in-memory SQLite or add PostgreSQL
```

## License

This project is part of the VITA system.

## Support and Documentation

For more detailed information, see:

- [IMPLEMENTATION.md](IMPLEMENTATION.md) - System architecture
- [RELIABILITY_IMPLEMENTATION.md](RELIABILITY_IMPLEMENTATION.md) - Error handling
- [NOTIFICATIONS_IMPLEMENTATION.md](NOTIFICATIONS_IMPLEMENTATION.md) - Notifications
- [AUDIO_PIPELINE_IMPLEMENTATION.md](AUDIO_PIPELINE_IMPLEMENTATION.md) - Audio processing
- [I18N_IMPLEMENTATION.md](I18N_IMPLEMENTATION.md) - Internationalization
- [core/README.md](core/README.md) - Core modules documentation
