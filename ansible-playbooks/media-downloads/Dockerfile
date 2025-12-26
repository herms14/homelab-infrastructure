FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY download-monitor.py .

# Run as non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5052/health')" || exit 1

CMD ["python", "-u", "download-monitor.py"]
