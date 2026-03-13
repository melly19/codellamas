FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies for Maven verification
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    maven \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Install uv
RUN pip install uv

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock /app/

# Copy source
COPY src /app/src

# Install Python dependencies
RUN uv sync --frozen

# Add venv to path
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "codellamas_backend.api:app", "--host", "0.0.0.0", "--port", "8000"]