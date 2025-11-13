#!/bin/bash

##############################################################################
# VITA System Setup Script
#
# Automates initial setup for deployment:
# - Creates virtual environment
# - Installs Python dependencies
# - Copies .env from .env.example if not present
# - Verifies configuration files
# - Sets up logs directory
#
# Idempotent: Safe to run multiple times
##############################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

##############################################################################
# Step 1: Detect Python version
##############################################################################
log_info "Checking Python version..."

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_success "Found Python $PYTHON_VERSION"

# Check minimum version (3.9)
REQUIRED_VERSION="3.9"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
    log_error "Python 3.9 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

##############################################################################
# Step 2: Create virtual environment (if not exists)
##############################################################################
log_info "Setting up virtual environment..."

VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
log_success "Virtual environment activated"

##############################################################################
# Step 3: Upgrade pip, setuptools, wheel
##############################################################################
log_info "Upgrading pip, setuptools, and wheel..."
python -m pip install --upgrade pip setuptools wheel -q
log_success "Pip tools updated"

##############################################################################
# Step 4: Install Python dependencies
##############################################################################
log_info "Installing Python dependencies from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt -q
log_success "Dependencies installed"

##############################################################################
# Step 5: Check system dependencies
##############################################################################
log_info "Checking system dependencies..."

MISSING_DEPS=()

if ! command -v ffmpeg &> /dev/null; then
    MISSING_DEPS+=("ffmpeg")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    log_warning "Some system dependencies are missing: ${MISSING_DEPS[@]}"
    log_info "Install them with:"
    echo "  Ubuntu/Debian: sudo apt-get install -y ${MISSING_DEPS[@]}"
    echo "  macOS: brew install ${MISSING_DEPS[@]}"
    echo "  Windows: Download from respective project websites"
fi

log_success "System dependency check completed"

##############################################################################
# Step 6: Setup environment configuration
##############################################################################
log_info "Setting up environment configuration..."

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        log_info "Copying $ENV_EXAMPLE to $ENV_FILE..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_warning "Please edit $ENV_FILE with your configuration:"
        echo "  - Set TELEGRAM_BOT_TOKEN"
        echo "  - Set GOOGLE_SHEETS_ID"
        echo "  - Set SERVICE_ACCOUNT_JSON_PATH"
        echo "  - Set ADMIN_IDS (comma-separated user IDs)"
        echo "  - Add optional integrations (WhatsApp, Instagram, etc.)"
    else
        log_error "$ENV_EXAMPLE not found!"
        exit 1
    fi
else
    log_success ".env file already exists"
fi

##############################################################################
# Step 7: Verify credentials file
##############################################################################
log_info "Verifying Google credentials setup..."

if grep -q "service_account.json" "$ENV_FILE"; then
    SERVICE_ACCOUNT_PATH=$(grep "SERVICE_ACCOUNT_JSON_PATH" "$ENV_FILE" | cut -d'=' -f2)
    SERVICE_ACCOUNT_PATH="${SERVICE_ACCOUNT_PATH#\"}"
    SERVICE_ACCOUNT_PATH="${SERVICE_ACCOUNT_PATH%\"}"
    
    if [ ! -f "$SERVICE_ACCOUNT_PATH" ]; then
        log_warning "Google service account file not found at: $SERVICE_ACCOUNT_PATH"
        log_info "Please obtain credentials from Google Cloud Console and place at: $SERVICE_ACCOUNT_PATH"
    else
        log_success "Google service account file found"
    fi
else
    log_warning "SERVICE_ACCOUNT_JSON_PATH not set in .env"
fi

##############################################################################
# Step 8: Create logs directory
##############################################################################
log_info "Setting up logs directory..."

if [ ! -d "logs" ]; then
    mkdir -p logs
    log_success "Created logs directory"
else
    log_success "logs directory already exists"
fi

##############################################################################
# Step 9: Verify Python imports
##############################################################################
log_info "Verifying Python module imports..."

python -c "
import sys
try:
    import pydantic
    import pydantic_settings
    import gspread
    import aiogram
    import tenacity
    print('✓ Core modules imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
" || {
    log_error "Failed to import required modules"
    exit 1
}

log_success "All core modules verified"

##############################################################################
# Step 10: Summary and next steps
##############################################################################
log_info "================================================"
log_success "Setup completed successfully!"
log_info "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure environment:"
echo "   Edit .env file with your credentials:"
echo "     - TELEGRAM_BOT_TOKEN: Get from BotFather on Telegram"
echo "     - GOOGLE_SHEETS_ID: From your Google Sheet URL"
echo "     - SERVICE_ACCOUNT_JSON_PATH: Path to Google service account JSON"
echo "     - ADMIN_IDS: Your Telegram user ID (or multiple, comma-separated)"
echo ""
echo "2. Set up Google Credentials:"
echo "   - Go to Google Cloud Console"
echo "   - Create service account with Sheets and Speech-to-Text APIs"
echo "   - Download JSON key to: $SERVICE_ACCOUNT_PATH"
echo ""
echo "3. Configure Google Sheets:"
echo "   - Share your Google Sheet with the service account email"
echo "   - Verify GOOGLE_SHEETS_ID is correct in .env"
echo ""
echo "4. Run locally:"
echo "   python -m core.main"
echo ""
echo "5. Or use Docker:"
echo "   docker-compose up -d"
echo ""
echo "For detailed setup instructions, see README.md"
echo ""
