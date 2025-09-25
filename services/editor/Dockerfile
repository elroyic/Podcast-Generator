FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/editor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/editor/ .
COPY shared/ ./shared/

# Expose port
EXPOSE 8009

# Run the application
CMD ["python", "main.py"]