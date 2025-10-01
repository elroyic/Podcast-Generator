FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Note: shared/ and VibeVoice-Community/ are mounted via volumes in docker-compose

# Create user and set permissions
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8015"]

