# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies (ffmpeg, libffi for compatibility)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libffi8 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set PATH to include local pip installations
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Create directory for logs
RUN mkdir -p /app/logs

# Expose port for webhook (if needed)
EXPOSE 8000

# Default entrypoint - can be overridden
CMD ["python", "-m", "core.main"]
