FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and service code
COPY ../shared /app/shared
COPY . /app

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8006

# Run the application
CMD ["python", "main.py"]