FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Copy all project files
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY dashboard/ ./dashboard/
COPY yahoo_websocket_client.py ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
