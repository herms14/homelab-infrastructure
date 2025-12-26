FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reddit-manager.py .

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Set environment variables
ENV DATA_DIR=/app/data
ENV POSTS_PER_SUBREDDIT=10
ENV CACHE_TTL=300

EXPOSE 5053

CMD ["python", "-u", "reddit-manager.py"]
