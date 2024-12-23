# docker/worker/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY . .

# Install Python dependencies using UV
RUN uv pip install --no-cache -e . && \
    uv pip install --no-cache -e fast_flights

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV IS_WORKER=true

# Make entrypoint script executable
RUN chmod +x /app/docker/worker/entrypoint.sh

# Run the worker script
CMD ["python", "-u", "src/worker/main.py"]