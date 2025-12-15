#!/bin/bash
# Startup script for Apache Airflow

set -e

# Set Airflow home
export AIRFLOW_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/airflow"

# Configure Airflow
export AIRFLOW__CORE__EXECUTOR="SequentialExecutor"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///${AIRFLOW_HOME}/airflow.db"
export AIRFLOW__CORE__LOAD_EXAMPLES="False"
export AIRFLOW__CORE__DAGS_FOLDER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/airflow/dags"

echo "==================================="
echo "Airflow Configuration"
echo "==================================="
echo "AIRFLOW_HOME: $AIRFLOW_HOME"
echo "DAGs folder: $AIRFLOW__CORE__DAGS_FOLDER"
echo "Database: $AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"
echo "Executor: $AIRFLOW__CORE__EXECUTOR"
echo ""

# Initialize database if needed
if [ ! -f "$AIRFLOW_HOME/airflow.db" ]; then
    echo "Initializing Airflow database..."
    airflow db init
fi

# Create admin user if needed
if ! airflow users list | grep -q "admin"; then
    echo "Creating admin user..."
    airflow users create \
        --username admin \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@example.com \
        --password admin
fi

echo "Starting Airflow..."
echo "Web UI: http://localhost:8080"
echo "==================================="
echo ""

# Start Airflow standalone (runs scheduler + webserver in one process)
airflow standalone
