FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY media-stats-api.py .

EXPOSE 5054

CMD ["gunicorn", "--bind", "0.0.0.0:5054", "--workers", "2", "media-stats-api:app"]
