FROM apache/airflow:2.8.0-python3.12

USER root

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Set AIRFLOW_HOME (default is /opt/airflow)
ENV AIRFLOW_HOME=/opt/airflow

# Copy backend code (required for imports in DAGs)
COPY --chown=airflow:root backend/ /opt/airflow/backend/
COPY --chown=airflow:root dashboard/ /opt/airflow/dashboard/

# Copy DAGs into Airflow DAGs directory
COPY --chown=airflow:root airflow/dags/ /opt/airflow/dags/

# Copy project config for dependencies
COPY --chown=airflow:root pyproject.toml uv.lock /opt/airflow/

# Install project dependencies using pip (Airflow image doesn't have uv)
# Extract and install key dependencies
RUN pip install --no-cache-dir \
    yfinance>=0.2.32 \
    clickhouse-driver>=0.2.6 \
    pandas>=2.1.3 \
    protobuf>=4.25.0 \
    python-dotenv>=1.0.0 \
    httpx>=0.25.1

# Ensure PYTHONPATH includes /opt/airflow for backend imports
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"
