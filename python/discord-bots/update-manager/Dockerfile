FROM python:3.11-slim

WORKDIR /app

# Install SSH client
RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY update_manager.py .

CMD ["python", "update_manager.py"]
