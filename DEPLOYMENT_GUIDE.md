# VITA System Deployment Guide

Complete deployment guide for production and development environments.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Webhook Configuration](#webhook-configuration)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Maintenance](#maintenance)

## Local Development Setup

### Prerequisites

- Python 3.9+ (3.11 recommended)
- pip and virtualenv
- ffmpeg
- Git

### Step-by-Step Setup

#### 1. Clone Repository

```bash
git clone <repository_url> vita-system
cd vita-system
```

#### 2. Run Automated Setup

```bash
bash setup.sh
```

This will:
- Create virtual environment
- Install all Python dependencies
- Create `.env` file from `.env.example`
- Create logs directory
- Verify all imports

#### 3. Configure Environment

Edit `.env` with your credentials:

```bash
nano .env
```

Key configurations:
- `TELEGRAM_BOT_TOKEN`: Get from BotFather
- `GOOGLE_SHEETS_ID`: Your Google Sheet ID
- `SERVICE_ACCOUNT_JSON_PATH`: Path to service account JSON
- `ADMIN_IDS`: Your Telegram user IDs (comma-separated)

#### 4. Set Up Google Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create Service Account (see README.md for detailed steps)
3. Download JSON key
4. Place in project directory: `mv ~/Downloads/service_account.json ./`

#### 5. Share Google Sheet

1. Get service account email from `service_account.json`
2. Open your Google Sheet
3. Click **Share** → Add email with **Editor** permissions

#### 6. Verify Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Test imports
python -c "import pydantic, aiogram, gspread; print('✓ All imports OK')"

# Test Sheets connection
python -c "
from integrations.google.sheets_manager import GoogleSheetsManager
m = GoogleSheetsManager('YOUR_SHEET_ID', 'service_account.json')
print(f'✓ Sheets OK: {len(m.read_specialists())} specialists')
"

# Test Telegram token
curl https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe | python -m json.tool
```

#### 7. Run Bot

```bash
source venv/bin/activate
python -m core.main
```

You should see:
```
ℹ Starting VITA bot...
✓ Bot initialized
✓ Middleware configured
✓ Admin handlers registered
✓ Client handlers registered
✓ Health monitor started
✓ Bot ready! Polling for messages...
```

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Quick Start

```bash
# Clone and navigate
git clone <repository_url> vita-system
cd vita-system

# Prepare credentials
cp .env.example .env
nano .env  # Configure

cp ~/Downloads/service_account.json ./

# Build and run
docker-compose up -d

# Verify
docker-compose logs -f bot | grep "Bot ready"
```

### Detailed Setup

#### 1. Prepare Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

Required:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
GOOGLE_SHEETS_ID=1ABC...XYZ
ADMIN_IDS=123456789
```

#### 2. Add Credentials

```bash
# Place service account JSON in project root
cp ~/Downloads/service_account.json ./

# Verify it's readable
ls -la service_account.json
```

#### 3. Build Docker Image

```bash
# Build image
docker build -t vita-bot:latest .

# Or use compose (automatic)
docker-compose build
```

#### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Should show:
# NAME               STATUS
# vita-bot          Up 5 minutes (healthy)
# vita-db           Up 5 minutes (healthy)
```

#### 5. Check Logs

```bash
# Follow bot logs
docker-compose logs -f bot

# Check database initialization
docker-compose logs db

# View specific time period
docker-compose logs --since 10m bot
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart service
docker-compose restart bot

# View logs
docker-compose logs -f bot

# Execute command in container
docker-compose exec bot python -m pytest

# View resource usage
docker-compose stats

# Remove volumes (careful: deletes database!)
docker-compose down -v
```

### Scaling with Docker

For multiple instances with load balancing:

```yaml
# docker-compose-prod.yml
version: '3.8'
services:
  bot:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

## Cloud Deployment

### AWS ECS Deployment

#### 1. Push Image to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name vita-bot

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account_id>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag vita-bot:latest <account_id>.dkr.ecr.us-east-1.amazonaws.com/vita-bot:latest

# Push image
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/vita-bot:latest
```

#### 2. Create ECS Task Definition

```json
{
  "family": "vita-bot",
  "containerDefinitions": [
    {
      "name": "vita-bot",
      "image": "<account_id>.dkr.ecr.us-east-1.amazonaws.com/vita-bot:latest",
      "environment": [
        {
          "name": "TELEGRAM_BOT_TOKEN",
          "value": "from-secrets-manager"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/vita-bot",
          "awslogs-region": "us-east-1"
        }
      }
    }
  ]
}
```

#### 3. Create ECS Service

```bash
aws ecs create-service \
  --cluster vita-production \
  --service-name vita-bot \
  --task-definition vita-bot:1 \
  --desired-count 1 \
  --launch-type FARGATE
```

### Google Cloud Run Deployment

#### 1. Build and Push to GCR

```bash
# Enable required APIs
gcloud services enable containerregistry.googleapis.com run.googleapis.com

# Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/vita-bot

# Deploy to Cloud Run
gcloud run deploy vita-bot \
  --image gcr.io/PROJECT_ID/vita-bot \
  --platform managed \
  --region us-central1 \
  --set-env-vars TELEGRAM_BOT_TOKEN=<token>,GOOGLE_SHEETS_ID=<id>
```

#### 2. Configure Secrets

```bash
# Create secret for service account
gcloud secrets create vita-service-account \
  --replication-policy="automatic" \
  --data-file=service_account.json

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding vita-service-account \
  --member=serviceAccount:vita-bot@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### Kubernetes Deployment

#### 1. Create ConfigMap and Secrets

```bash
# Create ConfigMap for environment
kubectl create configmap vita-config --from-file=.env

# Create Secret for credentials
kubectl create secret generic vita-secrets \
  --from-file=service_account.json
```

#### 2. Create Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vita-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vita-bot
  template:
    metadata:
      labels:
        app: vita-bot
    spec:
      containers:
      - name: bot
        image: vita-bot:latest
        imagePullPolicy: Always
        envFrom:
        - configMapRef:
            name: vita-config
        volumeMounts:
        - name: service-account
          mountPath: /app/credentials
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: service-account
        secret:
          secretName: vita-secrets
```

Apply:
```bash
kubectl apply -f deployment.yaml
kubectl get pods -l app=vita-bot
```

## Webhook Configuration

### Telegram Webhook Setup

#### Production Requirements

1. **HTTPS Certificate** (Let's Encrypt recommended)
2. **Public Domain** with DNS configured
3. **Port 443** accessible from internet
4. **IP Whitelisting** (optional)

#### Step 1: Set Up HTTPS

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificate locations:
# - /etc/letsencrypt/live/your-domain.com/fullchain.pem
# - /etc/letsencrypt/live/your-domain.com/privkey.pem
```

#### Step 2: Configure Bot

```env
# Add to .env
WEBHOOK_URL=https://your-domain.com/webhook/telegram
WEBHOOK_PORT=443
WEBHOOK_PATH=/webhook/telegram
```

#### Step 3: Set Webhook

```bash
# Test token first
TELEGRAM_BOT_TOKEN="your_token"

# Set webhook
curl -F "url=https://your-domain.com/webhook/telegram" \
     https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook

# Verify webhook
curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo | python -m json.tool
```

#### Step 4: Remove Webhook

To return to polling (remove webhook):

```bash
curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook
```

### WhatsApp Webhook Setup

1. **Verify Token**: Create random string
2. **Configure in .env**:
   ```env
   WHATSAPP_WEBHOOK_URL=https://your-domain.com/webhook/whatsapp
   WHATSAPP_VERIFY_TOKEN=random_verification_string
   ```
3. **Twilio Configuration**:
   - Go to Twilio Console → Messaging → WhatsApp
   - Set Webhook URL
   - Set Verify Token

### Instagram Webhook Setup

1. Create verify token
2. Configure webhook in Meta App settings
3. Add to `.env`:
   ```env
   INSTAGRAM_WEBHOOK_URL=https://your-domain.com/webhook/instagram
   ```

## Post-Deployment Verification

### Health Checks

```bash
# Check bot responsiveness
curl https://api.telegram.org/bot{TOKEN}/getMe

# Test Sheets connection
docker-compose exec bot python -c "
from integrations.google.sheets_manager import GoogleSheetsManager
m = GoogleSheetsManager('SHEET_ID', 'service_account.json')
print(f'Specialists: {len(m.read_specialists())}')
"

# Check logs for errors
docker-compose logs bot | grep -i error
```

### Functional Testing

```bash
# Test bot commands
1. Send /start to bot
2. Send /admin (if admin)
3. Send /help

# Test booking flow
1. Send specialist name
2. Verify conversation state progresses
3. Check Google Sheets for entry
```

### Performance Monitoring

```bash
# Container resource usage
docker-compose stats

# Database connection pool
docker-compose exec db psql -U vita_user -d vita_db -c "SELECT count(*) FROM pg_stat_activity;"

# Bot response time
time curl https://api.telegram.org/bot{TOKEN}/getMe
```

## Maintenance

### Regular Tasks

#### Daily
- Check bot logs for errors
- Verify health check status
- Monitor resource usage

#### Weekly
- Review error logs in Sheets
- Backup database (if applicable)
- Test emergency failover procedures

#### Monthly
- Update dependencies
- Security audit
- Performance review

### Backup and Restore

#### Backup Database

```bash
# Docker PostgreSQL backup
docker-compose exec db pg_dump -U vita_user vita_db > backup.sql

# Restore from backup
docker-compose exec -T db psql -U vita_user vita_db < backup.sql
```

#### Backup Google Sheets

```bash
# Export as CSV
gspread.SpreadsheetNotFound will naturally prompt backup

# Manual export: Sheet → File → Download → CSV
```

### Updating Deployment

#### Update Code

```bash
# Pull latest changes
git pull origin main

# Rebuild image
docker-compose build --no-cache

# Restart services
docker-compose up -d
```

#### Update Dependencies

```bash
# Update requirements.txt
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Rebuild Docker image
docker build --no-cache -t vita-bot:latest .
```

#### Rolling Update (Kubernetes)

```bash
# Trigger rolling update
kubectl set image deployment/vita-bot vita-bot=vita-bot:v2.0

# Monitor rollout
kubectl rollout status deployment/vita-bot

# Rollback if needed
kubectl rollout undo deployment/vita-bot
```

### Monitoring and Alerting

#### Prometheus Metrics (Optional)

Add to requirements.txt:
```
prometheus-client>=0.16.0
```

Configure monitoring:
```python
from prometheus_client import Counter, Histogram

bot_messages = Counter('bot_messages_total', 'Total messages processed')
processing_time = Histogram('message_processing_seconds', 'Message processing time')
```

#### Log Aggregation

For multi-instance deployments, use ELK Stack:

```bash
# Docker Compose with Elasticsearch, Logstash, Kibana
docker-compose -f docker-compose.prod.yml up -d
```

#### Alert Configuration

Set alerts for:
- Bot downtime (container not running)
- High error rate (>10 errors/hour)
- Database issues
- API quota exceeded

### Security Best Practices

1. **Secrets Management**
   - Use environment variables for sensitive data
   - Never commit `.env` or `service_account.json`
   - Rotate credentials regularly

2. **Network Security**
   - Use HTTPS/TLS for all connections
   - Firewall: Allow only necessary ports
   - IP whitelisting for webhooks (if possible)

3. **Database Security**
   - Enable PostgreSQL authentication
   - Use strong passwords
   - Encrypt database connections
   - Regular backups with encryption

4. **Dependency Security**
   - Regularly update dependencies
   - Review security advisories
   - Use vulnerability scanning tools

5. **Access Control**
   - Limit admin IDs to essential personnel
   - Log all admin actions
   - Regular security audits

### Scaling Considerations

#### Horizontal Scaling

For high load:

1. **Multiple bot instances**
   - Load balancer distributes requests
   - Shared database for state
   - Consider Redis for distributed cache

2. **Database scaling**
   - Read replicas for reporting
   - Connection pooling
   - Partitioning for large tables

3. **API optimization**
   - Rate limiting
   - Request caching
   - Batch operations where possible

#### Vertical Scaling

If single instance:

1. **Increase resources**
   - More CPU cores
   - More RAM
   - Faster storage

2. **Optimize code**
   - Profile bottlenecks
   - Cache frequently accessed data
   - Async/await optimization

### Troubleshooting Deployment Issues

See main [README.md](README.md#troubleshooting) for common issues and solutions.

### Support and Documentation

- **Docs**: See [README.md](README.md) and implementation guides
- **Issues**: Check GitHub Issues
- **Logs**: Review application logs for error details

---

**Last Updated**: 2025-01-15
**Version**: 1.0
