ARG DOCKER_BUILDKIT=1

FROM python:3.12-slim AS build

ENV PATH="/root/.local/bin/:$PATH" \
    PYTHONFAULTHANDLER=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_ROOT_USER_ACTION=ignore \
    LANG=C.UTF-8 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12 \
    UV_PROJECT_ENVIRONMENT="/usr/local/"

# Install system dependencies and UV
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy project configuration
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY src ./src

# Install project in development mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

#####################################################################

FROM build AS runtime

COPY --from=build /app /app
COPY --from=build /usr/local /usr/local

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]