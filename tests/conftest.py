"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_clickhouse_service():
    """Mock ClickHouse service."""
    service = MagicMock()
    service.save_historical_data = MagicMock(return_value=None)
    return service


@pytest.fixture
def mock_yahoo_client():
    """Mock Yahoo Finance client."""
    client = MagicMock()
    client.get_historical_data = MagicMock(
        return_value={
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
    )
    return client
