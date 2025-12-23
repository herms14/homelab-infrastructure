FROM python:3.12-slim

WORKDIR /app

# Install SSH client for paramiko
RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sysadmin-bot.py .

# Create SSH directory
RUN mkdir -p /app/ssh

CMD ["python", "-u", "sysadmin-bot.py"]
