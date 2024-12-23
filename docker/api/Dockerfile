# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Set working directory
WORKDIR /app

# Copy pyproject.toml first for better caching
COPY pyproject.toml ./

# Install dependencies without installing the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-deps -r pyproject.toml

# Copy the project into the image
COPY src ./src
COPY README.md ./

# Install project in editable mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]