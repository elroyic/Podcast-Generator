## CUDA-enabled PyTorch base (same as Presenter for compatibility)
FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir git+https://github.com/huggingface/transformers.git \
    && pip install --no-cache-dir hf_transfer

# Copy application code
COPY . .

# Note: shared/ and VibeVoice-Community/ are mounted via volumes in docker-compose

# Create user and set permissions
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8015"]

