## CUDA-enabled PyTorch base (adjust tag to your host driver/CUDA runtime)
## This image includes torch/torchaudio with CUDA preinstalled
FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir git+https://github.com/huggingface/transformers.git \
    && pip install --no-cache-dir hf_transfer

# Copy service code
COPY . .

# If the repository includes a local VibeVoice/ directory, make it importable
# and optionally install its Python package if present
ENV PYTHONPATH=/app:/app/shared:/app/services/presenter:/app/VibeVoice:${PYTHONPATH}
RUN if [ -f /app/VibeVoice/setup.py ] || [ -f /app/VibeVoice/pyproject.toml ]; then \
      pip install --no-cache-dir -e /app/VibeVoice; \
    else \
      echo "VibeVoice local package not detected; will load from HuggingFace"; \
    fi

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Ensure we run from /app where main.py exists when building from ./services/presenter
WORKDIR /app

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]