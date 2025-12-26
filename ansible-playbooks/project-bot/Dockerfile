# Project Bot - Discord-GitLab Kanban Integration
# Lightweight Python container for Discord bot + webhook server

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY project-bot.py .

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Expose webhook port
EXPOSE 5055

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5055/health')" || exit 1

# Run bot with unbuffered output for real-time logging
CMD ["python", "-u", "project-bot.py"]
