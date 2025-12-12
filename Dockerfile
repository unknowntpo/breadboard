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

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting backend..."\n\
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &\n\
BACKEND_PID=$!\n\
echo "Backend started with PID $BACKEND_PID"\n\
\n\
echo "Starting dashboard..."\n\
uv run streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0 &\n\
DASHBOARD_PID=$!\n\
echo "Dashboard started with PID $DASHBOARD_PID"\n\
\n\
# Wait for both processes\n\
wait $BACKEND_PID $DASHBOARD_PID\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose both ports
EXPOSE 8000 8501

# Run startup script
CMD ["/app/start.sh"]
