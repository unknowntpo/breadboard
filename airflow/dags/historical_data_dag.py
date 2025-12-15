"""DAG for fetching historical stock data every 6 hours."""
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from backend.infrastructure.airflow_tasks import fetch_all_symbols_historical_data

# DAG configuration
default_args = {
    "owner": "breadboard",
    "start_date": datetime(2024, 1, 1),
    "catchup": False,
}

dag = DAG(
    "historical_data_fetch",
    default_args=default_args,
    description="Fetch historical stock data every 6 hours",
    schedule_interval="0 0,6,12,18 * * *",  # Every 6 hours at 0, 6, 12, 18 UTC
    max_active_runs=1,
    tags=["stock_data", "historical"],
)


def fetch_historical_task():
    """Task to fetch historical data for all symbols."""
    return fetch_all_symbols_historical_data()


# Define task
fetch_task = PythonOperator(
    task_id="fetch_historical_data",
    python_callable=fetch_historical_task,
    dag=dag,
)

# Set dependencies
fetch_task
