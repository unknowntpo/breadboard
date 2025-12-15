# Initial POC - Phase 1 Implementation Plan

## 🎯 Current Progress

### Infrastructure & Config
- [x] Created Tiltfile (Kubernetes orchestration with OrbStack/Kind)
- [x] Created `.env.example` (environment template)
- [x] Created `pyproject.toml` with dependencies + uv tool
- [x] Removed Docker Compose (using K8s only)

### Kubernetes Manifests
- [x] `k8s/namespace.yaml` (breadboard namespace)
- [x] `k8s/clickhouse.yaml` (ClickHouse deployment + ConfigMap for auth)
- [x] `k8s/clickhouse-init.yml` (Schema init Job)
- [x] `k8s/app.yml` (Unified backend+dashboard deployment)

### Backend
- [x] `backend/main.py` (FastAPI app - refactored to minimal setup)
- [x] `backend/config.py` (Settings with python-dotenv)
- [x] `backend/processor.py` (Stream processor with DI)
- [x] `backend/schema.sql` (ClickHouse DDL)
- [x] Unified `Dockerfile` (merged backend+dashboard)
- [x] **Adopt clean architecture** - Domain, Repository, Service, API layers
  - [x] `backend/domain/entities.py` (Pydantic models)
  - [x] `backend/domain/interfaces.py` (Repository ABCs)
  - [x] `backend/repository/clickhouse_client.py` (DB connection)
  - [x] `backend/repository/stock_repository.py` (Repository implementations)
  - [x] `backend/services/stock_service.py` (Stock business logic)
  - [x] `backend/services/historical_service.py` (Historical logic)
  - [x] `backend/services/alert_service.py` (Alert logic)
  - [x] `backend/api/schemas.py` (Response DTOs)
  - [x] `backend/api/dependencies.py` (FastAPI DI)
  - [x] `backend/api/routes/health.py` (Health endpoint)
  - [x] `backend/api/routes/stocks.py` (Stock endpoints)
  - [x] `backend/api/routes/history.py` (History endpoint)
  - [x] `backend/api/websocket/realtime.py` (WebSocket handler)
  - [x] `backend/infrastructure/yahoo_client.py` (Yahoo WS client)
  - [x] `backend/infrastructure/scheduler.py` (APScheduler setup) - **REPLACED WITH AIRFLOW**
  - [x] **Airflow migration** (Phase 1.5)
    - [x] `backend/infrastructure/airflow_tasks.py` (Reusable task logic)
    - [x] `airflow/dags/historical_data_dag.py` (DAG definition)
    - [x] `scripts/run_airflow.sh` (Airflow startup script)
    - [x] Updated `backend/main.py` (removed APScheduler)
    - [x] Updated `pyproject.toml` (apache-airflow instead of apscheduler)
    - [x] Tests for DAG functionality
- [x] `backend/db.py` (Legacy - kept for reference, can be deleted)
- [ ] Ibis stream processing (Phase 2+)
- [ ] Advanced analytics (Phase 2+)

### Dashboard
- [x] `dashboard/app.py` (Streamlit UI)
- [x] Enhanced with dynamic Y-axis Altair charts
- [x] Enhanced with blinking percentage text on updates
- [x] Real-time monitoring page
- [x] Historical analysis page
- [x] Alerts page

### CI/CD
- [x] `.github/workflows/test.yml` (CI with Kind)
- [ ] CI workflow tested and passing

### Tests
- [ ] `tests/unit/test_processor.py`
- [ ] `tests/integration/test_e2e.py`

### Documentation
- [x] `README.md` with setup instructions
- [ ] Architecture diagram in README
- [ ] Validate all workflows documented

### System Validation
- [ ] Test Tilt + OrbStack workflow end-to-end
- [ ] Test GitHub Actions CI (Kind cluster)
- [ ] Dashboard shows live prices (1-2s updates)
- [ ] Alerts appear on >5% price drop
- [ ] Historical chart loads for any symbol/date
- [ ] System survives 1h continuous operation
- [ ] ClickHouse contains data from ≥2 fetch cycles

### Recent Enhancements (Completed)
- ✅ Merged backend+dashboard into single Docker image
- ✅ Refactored to python-dotenv for config management
- ✅ Dynamic Y-axis scaling with Altair charts
- ✅ Blinking percentage text animation on price updates

---

## Goal
Build minimal viable real-time stock dashboard. **Simplest tools possible → get it working → scale later.**

---

## Phase 1: MVP Stack (Confirmed)

### Infrastructure (Minimal)
- **1 VM/local machine** - Development on local
- **1 ClickHouse container** - `docker run clickhouse/clickhouse-server`
- **NO Kafka** - Use asyncio.Queue for buffering (Phase 2+)
- **NO Flink** - Use Ibis in-memory mode (Phase 2+)
- **NO Airflow** - Use APScheduler in FastAPI (Phase 2+)
- **NO NATS** - Use FastAPI WebSocket for alerts (Phase 2+)

### Application Stack
| Component | Phase 1 Tool | Phase 2+ Migration |
|-----------|--------------|-------------------|
| **Stream Processing** | **Ibis (in-memory mode)** | Flink |
| **Message Queue** | asyncio.Queue | Redis Streams → Kafka |
| **Batch Jobs** | APScheduler (cron) | Airflow DAGs |
| **Database** | ClickHouse (Docker) | ClickHouse cluster |
| **Alerts** | FastAPI WebSocket | NATS JetStream |
| **API Backend** | FastAPI | FastAPI (keep) |
| **Dashboard** | Streamlit | Streamlit (keep) |

---

## Why Ibis for Stream Processing?

**Ibis** (https://ibis-project.org/posts/unified-stream-batch/)
- ✅ **Unified API** for stream + batch processing
- ✅ **In-memory backend** for Phase 1 (zero infrastructure)
- ✅ **Migration path** to Flink backend later (same code)
- ✅ **Python-native** - no Java/Scala needed
- ✅ **Familiar API** - SQL-like operations

**Example:**
```python
import ibis
from ibis import _

# Phase 1: In-memory backend
con = ibis.memtable(stock_data)

# Same API works with Flink backend in Phase 2
# con = ibis.flink.connect(...)

# Windowing, aggregations, joins - unified syntax
result = (
    con
    .window(by=ibis.window(preceding=60, following=0))
    .aggregate(avg_price=_.price.mean())
)
```

**Phase 1:** In-memory processing (asyncio.Queue → Ibis → ClickHouse)
**Phase 2+:** Switch to Flink backend (same Ibis code, just change connection)

---

## Architecture (Phase 1)

```
┌─────────────────────────────────────────────────────────────┐
│              SINGLE FASTAPI APPLICATION                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Startup Tasks:                                     │    │
│  │  1. Connect to Yahoo Finance WebSocket             │    │
│  │  2. Initialize Ibis in-memory backend              │    │
│  │  3. Start APScheduler (cron: 0,6,12,18 UTC)        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  WebSocket Stream (Yahoo Finance)                           │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │ asyncio.Queue │ (buffer: 10K messages)                   │
│  └──────┬───────┘                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────┐                  │
│  │   Ibis In-Memory Processing          │                  │
│  │  - Windowed aggregations (1min, 5min)│                  │
│  │  - Alert detection (price drop >5%)  │                  │
│  │  - Data transformation (OHLCV calc)  │                  │
│  └──────┬───────────────────┬───────────┘                  │
│         │                   │                               │
│         │                   ▼                               │
│         │          ┌──────────────────┐                    │
│         │          │ Alert Detected   │                    │
│         │          │ Broadcast via    │                    │
│         │          │ WebSocket        │                    │
│         │          └──────────────────┘                    │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │ ClickHouse   │ (writes: real-time + aggregated)         │
│  └──────┬───────┘                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────┐                  │
│  │  REST API Endpoints:                 │                  │
│  │  • GET /api/v1/stocks/{symbol}       │                  │
│  │  • GET /api/v1/history               │                  │
│  │  • WS  /ws/realtime                  │                  │
│  └──────┬───────────────────────────────┘                  │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────────┐
   │    Streamlit     │
   │    Dashboard     │
   │  - Live chart    │
   │  - Alerts UI     │
   │  - Historical    │
   └──────────────────┘

APScheduler (background):
  Every 6h (0,6,12,18 UTC) → Fetch historical OHLCV → ClickHouse
```

---

## Implementation Steps

### Step 1: Infrastructure Setup (15 min)
```bash
# Start ClickHouse
docker run -d --name clickhouse \
  -p 9000:9000 -p 8123:8123 \
  clickhouse/clickhouse-server

# Create tables
clickhouse-client --query "
CREATE TABLE stock_prices (
  timestamp DateTime,
  symbol String,
  price Float64,
  volume UInt64,
  change_percent Float64,
  open Float64,
  high Float64,
  low Float64,
  close Float64
) ENGINE = MergeTree()
ORDER BY (symbol, timestamp);

CREATE TABLE stock_alerts (
  timestamp DateTime,
  symbol String,
  alert_type String,
  message String,
  price Float64,
  change_percent Float64
) ENGINE = MergeTree()
ORDER BY (timestamp);
"
```

### Step 2: Dependencies (pyproject.toml)
```toml
[project]
name = "breadboard"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi[all]",
  "uvicorn[standard]",
  "streamlit",
  "ibis-framework[duckdb]",  # In-memory backend
  "clickhouse-driver",
  "clickhouse-connect",
  "apscheduler",
  "websockets",
  "yfinance",
  "pandas",
  "python-dotenv",
]
```

### Step 3: Project Structure
```
breadboard/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (dotenv)
│   ├── websocket_client.py  # Yahoo Finance WS
│   ├── stream_processor.py  # Ibis processing logic
│   ├── db.py                # ClickHouse client
│   ├── scheduler.py         # APScheduler jobs
│   ├── models.py            # Pydantic models
│   ├── schema.sql           # ClickHouse table definitions
│   └── Dockerfile           # Backend container image
├── dashboard/
│   ├── app.py               # Streamlit main
│   ├── pages/
│   │   ├── 1_realtime.py    # Live monitoring
│   │   └── 2_historical.py  # Historical analysis
│   ├── components/
│   │   ├── chart.py         # Chart components
│   │   └── alerts.py        # Alert widgets
│   └── Dockerfile           # Dashboard container image
├── k8s/
│   ├── clickhouse.yaml      # ClickHouse deployment
│   ├── backend.yaml         # Backend deployment + service
│   └── dashboard.yaml       # Dashboard deployment + service
├── .github/
│   └── workflows/
│       ├── test.yml         # CI with Kind
│       └── deploy.yml       # CD to production (Phase 2+)
├── tests/
│   ├── unit/
│   │   └── test_processor.py
│   └── integration/
│       └── test_e2e.py
├── plan/
│   ├── design.md            # Architecture + estimations
│   └── epic_initial_poc.md  # This file
├── yahoo_websocket_client.py  # Existing (reuse logic)
├── pyproject.toml
├── Tiltfile                 # Tilt orchestration
├── docker-compose.yml       # Docker Compose (local dev option)
├── .env.example
└── README.md
```

### Step 4: Key Implementation Files

#### backend/main.py (Core Application)
```python
from fastapi import FastAPI, WebSocket
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

from backend.websocket_client import YahooWebSocketClient
from backend.stream_processor import StreamProcessor
from backend.scheduler import setup_historical_jobs

app = FastAPI()

# Global state
message_queue = asyncio.Queue(maxsize=10000)
ws_connections: list[WebSocket] = []
processor = StreamProcessor()

@app.on_event("startup")
async def startup():
    # 1. Start Yahoo Finance WebSocket
    ws_client = YahooWebSocketClient(message_queue)
    asyncio.create_task(ws_client.connect())

    # 2. Start Ibis stream processor
    asyncio.create_task(processor.process_stream(message_queue))

    # 3. Schedule historical data fetch (every 6h)
    scheduler = AsyncIOScheduler()
    setup_historical_jobs(scheduler)
    scheduler.start()

@app.get("/api/v1/stocks/{symbol}")
async def get_stock(symbol: str):
    # Query ClickHouse for latest price
    pass

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_connections.append(websocket)
    # Stream updates + alerts
    pass
```

#### backend/stream_processor.py (Ibis Processing)
```python
import ibis
from ibis import _
import asyncio

class StreamProcessor:
    def __init__(self):
        # Phase 1: In-memory backend
        self.con = ibis.memtable([])

    async def process_stream(self, queue: asyncio.Queue):
        """Process messages from queue using Ibis."""
        batch = []

        while True:
            try:
                # Collect messages into micro-batches
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                batch.append(msg)

                # Process every 100 messages or 1 second
                if len(batch) >= 100:
                    await self._process_batch(batch)
                    batch = []

            except asyncio.TimeoutError:
                if batch:
                    await self._process_batch(batch)
                    batch = []

    async def _process_batch(self, batch: list):
        """Use Ibis to transform and aggregate."""
        # Create in-memory table
        df = pd.DataFrame(batch)
        table = ibis.memtable(df)

        # 1-minute windowed aggregation
        result = (
            table
            .group_by(["symbol"])
            .aggregate(
                avg_price=_.price.mean(),
                max_price=_.price.max(),
                min_price=_.price.min(),
                volume=_.volume.sum()
            )
        )

        # Check for alerts (price drop >5%)
        alerts = result.filter(_.change_percent < -5.0)

        # Write to ClickHouse
        await self._write_to_clickhouse(result)
        await self._broadcast_alerts(alerts)
```

#### backend/scheduler.py (APScheduler Jobs)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import yfinance as yf

def fetch_historical_data():
    """Fetch daily OHLCV for all symbols."""
    symbols = ["AAPL", "NVDA", "TSLA", ...]  # From config

    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        # Write to ClickHouse

def setup_historical_jobs(scheduler: AsyncIOScheduler):
    """Schedule historical data fetch every 6 hours."""
    scheduler.add_job(
        fetch_historical_data,
        CronTrigger(hour='0,6,12,18'),  # 0:00, 6:00, 12:00, 18:00 UTC
        id='historical_fetch'
    )
```

#### dashboard/app.py (Streamlit UI)
```python
import streamlit as st
import websocket
import json

st.set_page_config(page_title="Breadboard", layout="wide")

st.title("📊 Real-time Stock Dashboard")

# Sidebar
with st.sidebar:
    st.header("Watchlist")
    symbols = st.multiselect("Symbols", ["AAPL", "NVDA", "TSLA"])

# Main content
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Live Price Chart")
    chart_placeholder = st.empty()

    # WebSocket connection to FastAPI
    ws = websocket.create_connection("ws://localhost:8000/ws/realtime")

    while True:
        msg = json.loads(ws.recv())
        # Update chart with st.line_chart()

with col2:
    st.subheader("🔔 Alerts")
    alert_placeholder = st.empty()

    # Display alerts from WebSocket
```

### Step 5: Environment Configuration (.env.example)
```bash
# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# Yahoo Finance
YAHOO_WS_URL=wss://streamer.finance.yahoo.com/

# Symbols to track
SYMBOLS=AAPL,NVDA,TSLA,META,AMZN,GOOGL,MSFT

# Alert threshold
ALERT_THRESHOLD=-5.0  # Price drop percentage

# Historical fetch schedule (cron)
HISTORICAL_FETCH_CRON=0,6,12,18  # Every 6 hours
```

### Step 6: Kubernetes Manifests (k8s/)
```yaml
# k8s/clickhouse.yml
apiVersion: v1
kind: Service
metadata:
  name: clickhouse
spec:
  ports:
    - port: 9000
      name: native
    - port: 8123
      name: http
  selector:
    app: clickhouse
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clickhouse
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clickhouse
  template:
    metadata:
      labels:
        app: clickhouse
    spec:
      containers:
      - name: clickhouse
        image: clickhouse/clickhouse-server:latest
        ports:
        - containerPort: 9000
        - containerPort: 8123
        env:
        - name: CLICKHOUSE_DB
          value: breadboard
```

```yaml
# k8s/backend.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: breadboard-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: CLICKHOUSE_HOST
          value: clickhouse
        - name: CLICKHOUSE_PORT
          value: "9000"
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  type: LoadBalancer
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: backend
```

```yaml
# k8s/dashboard.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dashboard
  template:
    metadata:
      labels:
        app: dashboard
    spec:
      containers:
      - name: dashboard
        image: breadboard-dashboard:latest
        ports:
        - containerPort: 8501
        env:
        - name: BACKEND_URL
          value: http://backend:8000
---
apiVersion: v1
kind: Service
metadata:
  name: dashboard
spec:
  type: LoadBalancer
  ports:
    - port: 8501
      targetPort: 8501
  selector:
    app: dashboard
```

### Step 7: Tiltfile
```python
# Tiltfile
# Local dev uses OrbStack, CI uses Kind

# Build Docker images
docker_build('breadboard-backend',
  context='.',
  dockerfile='backend/Dockerfile',
  live_update=[
    sync('backend/', '/app/backend/'),
    run('pip install -e .', trigger=['pyproject.toml']),
  ]
)

docker_build('breadboard-dashboard',
  context='.',
  dockerfile='dashboard/Dockerfile',
  live_update=[
    sync('dashboard/', '/app/dashboard/'),
  ]
)

# Deploy to Kubernetes
k8s_yaml(['k8s/clickhouse.yml', 'k8s/backend.yml', 'k8s/dashboard.yml'])

# Port forwards
k8s_resource('backend', port_forwards='8000:8000')
k8s_resource('dashboard', port_forwards='8501:8501')
k8s_resource('clickhouse', port_forwards=['9000:9000', '8123:8123'])

# Local resources (optional: run Python directly for faster iteration)
# Uncomment if you prefer local Python over containerized
# local_resource('backend-local',
#   serve_cmd='uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000',
#   deps=['backend/'],
#   resource_deps=['clickhouse'],  # Wait for ClickHouse to be ready
# )

# local_resource('dashboard-local',
#   serve_cmd='streamlit run dashboard/app.py --server.port 8501',
#   deps=['dashboard/'],
#   resource_deps=['backend-local'],
# )
```

### Step 8: Dockerfiles

**backend/Dockerfile**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy application code
COPY backend/ ./backend/
COPY yahoo_websocket_client.py .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**dashboard/Dockerfile**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy dashboard code
COPY dashboard/ ./dashboard/

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

### Step 9: docker-compose.yml (Alternative to Kubernetes for local dev)
```yaml
version: '3.8'

services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
      - "8123:8123"
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./backend/schema.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      CLICKHOUSE_DB: breadboard
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    healthcheck:
      test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  clickhouse_data:
```

---

## Local Development Workflow

### Option 1: Docker Compose (Simplest for quick testing)
```bash
# Install dependencies
uv sync

# Start ClickHouse
docker-compose up -d

# Create tables
clickhouse-client < backend/schema.sql

# Copy env config
cp .env.example .env

# Terminal 1: FastAPI backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit dashboard
streamlit run dashboard/app.py --server.port 8501
```

**Access:**
- **Dashboard:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **ClickHouse UI:** http://localhost:8123/play

### Option 2: Tilt + OrbStack (Kubernetes local dev)
```bash
# Prerequisites
# 1. OrbStack installed (provides Kubernetes)
# 2. Tilt installed: https://docs.tilt.dev/install.html

# Switch to OrbStack cluster
kubectl config use-context orbstack

# Verify cluster is running
kubectl cluster-info

# Start Tilt (builds images, deploys to K8s, watches for changes)
tilt up

# Tilt UI will open at http://localhost:10350
# Services auto-forwarded:
# - Dashboard: http://localhost:8501
# - Backend API: http://localhost:8000
# - ClickHouse: http://localhost:8123

# Press 'space' to open Tilt web UI
# Press 'q' to quit (keeps resources running)

# To tear down everything
tilt down
```

**Benefits of Tilt + OrbStack:**
- ✅ Live reload on code changes (syncs to containers)
- ✅ Kubernetes-native (matches production)
- ✅ Fast rebuilds (layer caching + live_update)
- ✅ Multi-service orchestration
- ✅ Same workflow as CI (Kind)

---

## CI/CD with GitHub Actions + Kind

### .github/workflows/test.yml
```yaml
name: Test

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Create Kind cluster
        uses: helm/kind-action@v1
        with:
          cluster_name: breadboard-test
          wait: 300s

      - name: Install Tilt
        run: |
          curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash

      - name: Load images to Kind
        run: |
          # Build images locally first
          docker build -t breadboard-backend:ci -f backend/Dockerfile .
          docker build -t breadboard-dashboard:ci -f dashboard/Dockerfile .

          # Load into Kind cluster
          kind load docker-image breadboard-backend:ci --name breadboard-test
          kind load docker-image breadboard-dashboard:ci --name breadboard-test

      - name: Deploy with kubectl
        run: |
          kubectl apply -f k8s/clickhouse.yaml
          kubectl apply -f k8s/backend.yaml
          kubectl apply -f k8s/dashboard.yaml

          # Wait for deployments to be ready
          kubectl wait --for=condition=available --timeout=300s deployment/clickhouse
          kubectl wait --for=condition=available --timeout=300s deployment/backend
          kubectl wait --for=condition=available --timeout=300s deployment/dashboard

      - name: Run integration tests
        run: |
          # Port-forward to access services
          kubectl port-forward svc/backend 8000:8000 &
          kubectl port-forward svc/dashboard 8501:8501 &
          sleep 10

          # Run tests
          pytest tests/integration/

      - name: Cleanup
        if: always()
        run: |
          kubectl delete -f k8s/ || true
```

### .github/workflows/deploy.yml (Future - Phase 2+)
```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-west-2

      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-west-2 | \
          docker login --username AWS --password-stdin <ecr-registry>

      - name: Build and push images
        run: |
          docker build -t <ecr-registry>/breadboard-backend:${{ github.sha }} -f backend/Dockerfile .
          docker push <ecr-registry>/breadboard-backend:${{ github.sha }}

          docker build -t <ecr-registry>/breadboard-dashboard:${{ github.sha }} -f dashboard/Dockerfile .
          docker push <ecr-registry>/breadboard-dashboard:${{ github.sha }}

      - name: Update EKS deployment
        run: |
          aws eks update-kubeconfig --region us-west-2 --name breadboard-prod
          kubectl set image deployment/backend backend=<ecr-registry>/breadboard-backend:${{ github.sha }}
          kubectl set image deployment/dashboard dashboard=<ecr-registry>/breadboard-dashboard:${{ github.sha }}
```

---

## User Decisions (Confirmed)

✅ **Message Buffering:** asyncio.Queue (in-memory, zero setup)
✅ **Stream Processing:** Ibis in-memory mode (unified stream/batch API)
✅ **Historical Fetch:** Every 6 hours (0,6,12,18 UTC via APScheduler)
✅ **Alerts:** In-dashboard via FastAPI WebSocket → Streamlit
✅ **ClickHouse:** Docker container (local development)
✅ **Data Retention:** Keep all data (no TTL for Phase 1)

---

## Success Criteria (Phase 1 Complete)

✅ Dashboard shows live prices updating every 1-2 seconds
✅ Alert notification appears when price drops >5%
✅ Historical data chart loads for any symbol + date range
✅ System survives 1 hour of continuous operation
✅ ClickHouse contains data from at least 2 historical fetch cycles
✅ Ibis processing handles 100+ msg/sec without lag

**Estimated Effort:** 2-3 focused days (16-24 hours)

---

~~~~## Phase 2+ Migration Path~~~~

When Phase 1 is validated and needs scaling:

### Stream Processing: Ibis → Flink
```python
# Phase 1: In-memory
con = ibis.memtable(data)

# Phase 2: Switch to Flink backend (SAME CODE)
con = ibis.flink.connect(
    host="flink-jobmanager",
    port=8081
)

# All Ibis operations stay the same!
result = con.window(...).aggregate(...)
```

### Message Queue: asyncio.Queue → Kafka
- Add Kafka container to docker-compose
- Replace `asyncio.Queue` with `aiokafka.AIOKafkaProducer`
- Consumer group for scaling

### Batch Jobs: APScheduler → Airflow
- Deploy Airflow (helm chart)
- Convert scheduler jobs to DAGs
- Add retries, dependencies, monitoring

### Alerts: WebSocket → NATS
- Add NATS JetStream container
- Publish alerts to NATS subjects
- Multiple subscribers (dashboard, email, Slack)

---

## Why This Approach?

1. **Zero infrastructure overhead** - Just ClickHouse container
2. **Single application** - Easy to debug, deploy, understand
3. **Ibis = future-proof** - Same code works with Flink later
4. **Fast iteration** - No Kafka/Airflow complexity blocking development
5. **Production-ready foundation** - ClickHouse scales to billions of rows

**Philosophy:** Make it work → Make it right → Make it fast

---

## Next Steps

### Phase 1 Implementation Checklist

**Infrastructure & Config:**
- [ ] Create `docker-compose.yml` (ClickHouse only)
- [ ] Create `Tiltfile` (Kubernetes orchestration)
- [ ] Create `.env.example` (environment template)
- [ ] Create `pyproject.toml` with all dependencies

**Kubernetes Manifests:**
- [ ] `k8s/clickhouse.yaml` (ClickHouse deployment + service)
- [ ] `k8s/backend.yaml` (Backend deployment + service)
- [ ] `k8s/dashboard.yaml` (Dashboard deployment + service)

**Backend:**
- [ ] `backend/main.py` (FastAPI app with startup tasks)
- [ ] `backend/config.py` (Settings from .env)
- [ ] `backend/websocket_client.py` (Yahoo Finance WS client)
- [ ] `backend/stream_processor.py` (Ibis in-memory processing)
- [ ] `backend/db.py` (ClickHouse client + connection pool)
- [ ] `backend/scheduler.py` (APScheduler for historical fetch)
- [ ] `backend/models.py` (Pydantic models)
- [ ] `backend/schema.sql` (ClickHouse table DDL)
- [ ] `backend/Dockerfile`

**Dashboard:**
- [ ] `dashboard/app.py` (Streamlit main page)
- [ ] `dashboard/pages/1_realtime.py` (Live monitoring)
- [ ] `dashboard/pages/2_historical.py` (Historical analysis)
- [ ] `dashboard/components/chart.py` (Chart widgets)
- [ ] `dashboard/components/alerts.py` (Alert notifications)
- [ ] `dashboard/Dockerfile`

**CI/CD:**
- [ ] `.github/workflows/test.yml` (CI with Kind)
- [ ] `.github/workflows/deploy.yml` (CD - Phase 2+)

**Tests:**
- [ ] `tests/unit/test_processor.py` (Unit tests for Ibis processor)
- [ ] `tests/integration/test_e2e.py` (End-to-end integration tests)

**Documentation:**
- [ ] Update `README.md` with setup instructions
- [ ] Add architecture diagram to README
- [ ] Document local dev workflows (Docker Compose vs Tilt)

**Validation:**
- [ ] Test Docker Compose workflow
- [ ] Test Tilt + OrbStack workflow
- [ ] Test GitHub Actions CI (Kind cluster)
- [ ] Run end-to-end integration tests
- [ ] Verify all success criteria met

---

## Estimated Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| **Day 1 AM** | Infrastructure + Backend scaffolding | 4h |
| **Day 1 PM** | Ibis processor + ClickHouse integration | 4h |
| **Day 2 AM** | Streamlit dashboard + WebSocket | 4h |
| **Day 2 PM** | Testing + debugging | 4h |
| **Day 3** | Kubernetes manifests + Tilt + CI | 4-8h |

**Total:** 20-24 hours focused work

---

## Success Criteria Validation

Before considering Phase 1 complete, verify:

✅ **Functional:**
1. Dashboard shows live prices (1-2 sec updates)
2. Alerts appear on >5% price drop
3. Historical chart loads for any symbol/date
4. APScheduler runs every 6h (verify logs)
5. ClickHouse contains data from ≥2 fetch cycles

✅ **Performance:**
6. Ibis processes 100+ msg/sec without lag
7. WebSocket latency <200ms
8. Dashboard loads in <3 seconds

✅ **Infrastructure:**
9. Docker Compose workflow works
10. Tilt + OrbStack workflow works
11. GitHub Actions CI passes (Kind)
12. System survives 1h continuous operation

✅ **Code Quality:**
13. All tests pass (unit + integration)
14. No critical linting errors
15. README.md documents all workflows
16. .env.example has all required variables

---

## Ready to Start Implementation? 🚀

**Recommended workflow:**
1. Start with Docker Compose (simplest)
2. Implement backend + basic dashboard
3. Validate core functionality
4. Add Kubernetes manifests
5. Test with Tilt
6. Add CI/CD

**First PR Goal:** Basic end-to-end flow working with Docker Compose
