"""Tests for Airflow DAG."""
import pytest
from unittest.mock import patch, MagicMock


def test_dag_imports():
    """Test that DAG imports without errors."""
    try:
        from airflow.dags.historical_data_dag import dag
        assert dag is not None
        assert dag.dag_id == "historical_data_fetch"
    except Exception as e:
        pytest.fail(f"DAG import failed: {e}")


def test_dag_schedule():
    """Test DAG has correct schedule."""
    from airflow.dags.historical_data_dag import dag
    assert dag.schedule_interval == "0 0,6,12,18 * * *"


def test_dag_has_tasks():
    """Test DAG has expected tasks."""
    from airflow.dags.historical_data_dag import dag
    assert len(dag.tasks) >= 1
    task_ids = [task.task_id for task in dag.tasks]
    assert "fetch_historical_data" in task_ids


def test_dag_max_active_runs():
    """Test DAG max_active_runs is set to 1."""
    from airflow.dags.historical_data_dag import dag
    assert dag.max_active_runs == 1


@patch("backend.infrastructure.airflow_tasks.yahoo_websocket_client")
@patch("backend.infrastructure.airflow_tasks.get_historical_service")
def test_fetch_all_symbols_success(mock_service, mock_yahoo):
    """Test fetching all symbols returns expected structure."""
    from backend.infrastructure.airflow_tasks import fetch_all_symbols_historical_data

    # Mock yahoo client
    mock_yahoo.get_historical_data.return_value = {
        "symbol": "TEST",
        "records": [
            {
                "date": "2024-01-01",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 102.0,
                "volume": 1000000,
            }
        ],
        "record_count": 1,
    }

    # Mock service
    mock_service_instance = MagicMock()
    mock_service.return_value = mock_service_instance

    # Test with small symbol list
    result = fetch_all_symbols_historical_data(symbols=["TEST"], period="1d")

    assert result["status"] == "completed"
    assert result["total_symbols"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "success"
    assert result["results"][0]["symbol"] == "TEST"
    assert result["results"][0]["records_inserted"] == 1


@patch("backend.infrastructure.airflow_tasks.yahoo_websocket_client")
@patch("backend.infrastructure.airflow_tasks.get_historical_service")
def test_fetch_symbol_error_handling(mock_service, mock_yahoo):
    """Test error handling in fetch_symbol_historical_data."""
    from backend.infrastructure.airflow_tasks import fetch_symbol_historical_data

    # Mock yahoo client to raise exception
    mock_yahoo.get_historical_data.side_effect = Exception("Connection failed")

    result = fetch_symbol_historical_data("INVALID")

    assert result["status"] == "error"
    assert result["symbol"] == "INVALID"
    assert "Connection failed" in result["error"]


@patch("backend.infrastructure.airflow_tasks.yahoo_websocket_client")
@patch("backend.infrastructure.airflow_tasks.get_historical_service")
def test_fetch_symbol_no_data(mock_service, mock_yahoo):
    """Test handling when no data is returned."""
    from backend.infrastructure.airflow_tasks import fetch_symbol_historical_data

    # Mock yahoo client to return empty data
    mock_yahoo.get_historical_data.return_value = None

    result = fetch_symbol_historical_data("EMPTY")

    assert result["status"] == "no_data"
    assert result["symbol"] == "EMPTY"
    assert result["records_inserted"] == 0


def test_default_symbols_defined():
    """Test that DEFAULT_SYMBOLS is properly defined."""
    from backend.infrastructure.airflow_tasks import DEFAULT_SYMBOLS

    assert isinstance(DEFAULT_SYMBOLS, list)
    assert len(DEFAULT_SYMBOLS) > 0
    assert "AAPL" in DEFAULT_SYMBOLS
