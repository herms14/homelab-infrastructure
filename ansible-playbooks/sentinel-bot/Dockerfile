FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add hypercorn for webhook server
RUN pip install --no-cache-dir hypercorn

# Copy application code
COPY . .

# Create data and ssh directories
RUN mkdir -p /app/data /app/.ssh

# Expose webhook port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 5050)); s.close()" || exit 1

# Run the bot
CMD ["python", "sentinel.py"]
