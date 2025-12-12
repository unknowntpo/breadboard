# Breadboard - Real-time Stock Dashboard

![Gemini_Generated_Image_o9uow0o9uow0o9uo.png](logo.png)

Real-time stock pricing dashboard with WebSocket integration, time-series storage, and interactive visualization.

## Features

- 📊 Real-time price updates from Yahoo Finance WebSocket
- 💾 Time-series data storage with ClickHouse
- 📈 Interactive Streamlit dashboard
- 🔔 Price drop alerts (>= 5%)
- 📅 Historical data fetching every 6 hours
- 🚀 Kubernetes deployment with Tilt for live reload
- ⚡ Fast dependency management with `uv`

## Architecture

```
Yahoo Finance WebSocket → asyncio.Queue → Stream Processor → ClickHouse
                                              ↓
                                         Alert System
                                              ↓
                                        WebSocket Broadcast
                                              ↓
                                      Streamlit Dashboard
```

### Components

- **Backend (FastAPI)**: WebSocket client, stream processing, REST API
- **Dashboard (Streamlit)**: Real-time monitoring, historical analysis, alerts
- **Database (ClickHouse)**: Time-series storage for stock prices and OHLCV data
- **Scheduler (APScheduler)**: Automated historical data fetch every 6 hours

## Quick Start

### Prerequisites

- Python 3.11+
- OrbStack (for local Kubernetes cluster)
- Tilt CLI
- kubectl

### Setup

1. **Clone the repository**

```bash
cd breadboard
```

2. **Ensure OrbStack cluster is running**

```bash
kubectl config current-context  # Should show OrbStack context
```

3. **Start all services with Tilt**

```bash
tilt up
```

This will:
- Build Docker images with live reload
- Deploy ClickHouse, backend, and dashboard to Kubernetes
- Set up port forwarding
- Display service URLs

4. **Initialize ClickHouse schema**

```bash
kubectl exec -it deployment/clickhouse -n breadboard -- clickhouse-client < backend/schema.sql
```

5. **Access the dashboard**

- **Dashboard**: http://localhost:8501
- **Backend API**: http://localhost:8000/docs
- **ClickHouse**: http://localhost:8123

## Development

### Live Reload

Tilt provides live reload for both backend and dashboard:

- **Backend changes**: Modify files in `backend/` → automatic sync & restart
- **Dashboard changes**: Modify `dashboard/app.py` → automatic sync
- **Dependencies**: Edit `pyproject.toml` or `uv.lock` → triggers `uv sync`

### View Logs

```bash
# Tilt UI (recommended)
# Access at http://localhost:10350

# Or use kubectl
kubectl logs -f deployment/backend -n breadboard
kubectl logs -f deployment/dashboard -n breadboard
kubectl logs -f deployment/clickhouse -n breadboard
```

### Stop Services

```bash
tilt down
```

## CI/CD

GitHub Actions workflow runs on every push:

```yaml
# .github/workflows/test.yml
- Creates Kind cluster
- Runs `tilt ci`
- Tests service health
- Validates API endpoints
```

## Kubernetes Namespace

All resources are deployed to the `breadboard` namespace for isolation:

```bash
# View all resources in the namespace
kubectl get all -n breadboard

# Delete the namespace (removes all resources)
kubectl delete namespace breadboard
```

## Configuration

Environment variables (`.env.example`):

```bash
# ClickHouse
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_DB=breadboard

# Backend
LOG_LEVEL=INFO

# Dashboard
BACKEND_URL=http://backend:8000
```

## API Endpoints

### REST API

- `GET /health` - Health check
- `GET /api/v1/stocks/{symbol}` - Latest price for symbol
- `GET /api/v1/history?symbol=X&start=Y&end=Z` - Historical OHLCV data
- `GET /api/v1/stocks/{symbol}/recent?limit=N` - Recent price history

### WebSocket

- `WS /ws/realtime` - Real-time price updates and alerts

## Monitored Symbols

Default watchlist:
- Stocks: AAPL, NVDA, TSLA, META, AMZN, GOOGL, MSFT, AMD, NFLX, COIN
- Crypto: BTC-USD, ETH-USD, SOL-USD
- ETFs: SPY, QQQ

Customize in `backend/main.py` → `SYMBOLS_TO_TRACK`

## Data Schema

### Real-time Prices

```sql
CREATE TABLE stock_prices (
    timestamp DateTime,
    symbol String,
    price Float64,
    volume UInt64,
    change_percent Float64
) ENGINE = MergeTree()
ORDER BY (symbol, timestamp);
```

### Historical Data

```sql
CREATE TABLE historical_data (
    date Date,
    symbol String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64
) ENGINE = MergeTree()
ORDER BY (symbol, date);
```

## Troubleshooting

### ClickHouse connection errors

```bash
# Check if ClickHouse is running
kubectl get pods -l app=clickhouse -n breadboard

# Restart ClickHouse
kubectl rollout restart deployment/clickhouse -n breadboard
```

### Backend not receiving data

```bash
# Check backend logs
kubectl logs -f deployment/backend -n breadboard

# Verify queue size
curl http://localhost:8000/health
```

### Dashboard not loading

```bash
# Check dashboard logs
kubectl logs -f deployment/dashboard -n breadboard

# Verify backend connectivity
kubectl exec -it deployment/dashboard -n breadboard -- curl backend:8000/health
```

## Project Structure

```
breadboard/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── db.py            # ClickHouse client
│   ├── processor.py     # Stream processor
│   ├── schema.sql       # Database schema
│   └── Dockerfile
├── dashboard/
│   ├── __init__.py
│   ├── app.py           # Streamlit UI
│   └── Dockerfile
├── k8s/
│   ├── namespace.yaml   # Breadboard namespace
│   ├── clickhouse.yaml  # ClickHouse deployment
│   ├── backend.yaml     # Backend deployment
│   └── dashboard.yaml   # Dashboard deployment
├── .github/
│   └── workflows/
│       └── test.yml     # CI pipeline
├── Tiltfile             # Tilt configuration
├── pyproject.toml       # Python dependencies
├── yahoo_websocket_client.py  # WebSocket utilities
└── README.md
```

## Phase 2 Roadmap

See `plan/epic_refactor_flink_airflow_nats.md` for migration to production stack:

- **Kafka**: Replace asyncio.Queue for guaranteed delivery
- **Flink**: Advanced stream processing (windowing, CEP)
- **Airflow**: Complex DAG workflows
- **NATS JetStream**: Distributed pub/sub for alerts

## License

MIT

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request
