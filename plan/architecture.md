# Current Architecture (2026-03-14)

## System Overview

Real-time stock dashboard. Backend streams live prices from Yahoo Finance, stores OHLCV in ClickHouse, serves a Vue 3 SPA. Airflow fetches historical data every 6h.

```
                    ┌──────────────────────────────────────────┐
                    │          FastAPI Backend (K8s)           │
                    │                                          │
Yahoo Finance WS ──►│  asyncio.Queue (10K)                    │
                    │       │                                  │
                    │       ▼                                  │
                    │  StreamProcessor                         │
                    │  (batch=100 | timeout=1s)               │
                    │       │                ├─ alert >5% drop │
                    │       ▼                ▼                 │
                    │  ClickHouseRepo   WebSocket broadcast    │
                    └──────────┬───────────────────────────────┘
                               │
                    ┌──────────▼───────────┐   ┌──────────────────┐
                    │  ClickHouse (K8s)    │◄──│  Airflow (K8s)   │
                    │  - stock_prices      │   │  DAG: 0,6,12,18h │
                    │  - historical_data   │   │  fetch OHLCV      │
                    │  - stock_alerts      │   └──────────────────┘
                    └──────────┬───────────┘
                               │ GET /api/v1/history
                    ┌──────────▼───────────┐
                    │  Vue 3 + TS SPA      │
                    │  (nginx, K8s)        │
                    │  - PriceChart        │
                    │  - OhlcvTable        │
                    │  - StatCards         │
                    └──────────────────────┘
```

---

## Component Breakdown

### Backend (`backend/`)

| Layer | Files | Responsibility |
|-------|-------|----------------|
| API | `api/routes/{health,stocks,history}.py` | REST endpoints |
| API | `api/websocket/realtime.py` | WS broadcast manager |
| Service | `services/{stock,historical,alert}_service.py` | Business logic |
| Repository | `repository/stock_repository.py` | ClickHouse CRUD |
| Repository | `repository/clickhouse_client.py` | DB connection |
| Domain | `domain/entities.py` | Pydantic models |
| Domain | `domain/interfaces.py` | Repository ABCs |
| Infra | `infrastructure/yahoo_client.py` | Yahoo WS feed |
| Infra | `infrastructure/airflow_tasks.py` | Airflow callable |
| Core | `processor.py` | Async batch processor |
| Core | `main.py` | FastAPI app + lifespan |

**Endpoints:**
- `GET /health`
- `GET /api/v1/stocks/{symbol}`
- `GET /api/v1/stocks/recent`
- `GET /api/v1/history?symbol=&start=&end=`
- `WS  /ws/realtime`

### Frontend (`frontend/`)

| File | Role |
|------|------|
| `src/App.vue` | Root — orchestrates fetch + state |
| `src/api/history.ts` | `fetchHistory()` + `HistoryRecord` interface |
| `src/components/SymbolTabs.vue` | Symbol switcher |
| `src/components/RangePicker.vue` | Date range selector |
| `src/components/PriceChart.vue` | lightweight-charts v5 candlestick |
| `src/components/StatCards.vue` | OHLCV stat display |
| `src/components/OhlcvTable.vue` | Sortable data table |

Tests: 5 Vitest unit + 1 Playwright e2e.

### Infrastructure (K8s)

| Manifest | What it deploys |
|----------|-----------------|
| `k8s/namespace.yml` | `breadboard` namespace |
| `k8s/clickhouse.yml` | ClickHouse + Service |
| `k8s/clickhouse-init.yml` | Schema init Job |
| `k8s/backend.yml` | FastAPI app + Service (port 8000) |
| `k8s/frontend.yml` | Vue SPA nginx + Service (port 80) |
| `k8s/airflow.yml` | Airflow standalone + Service (port 8080) |

### CI/CD

| Workflow | Trigger | Steps |
|----------|---------|-------|
| `.github/workflows/test.yml` | push/PR to master | Kind cluster → tilt ci → health check |
| `.github/workflows/frontend.yml` | frontend/** changes | pnpm install → unit tests → build → Playwright |

---

## Known Issues & Gaps

### Critical (blocking CI/production)

- [ ] **Image name mismatch**: Tiltfile builds `breadboard-app`, `backend.yml` references `breadboard-backend` — CI will fail
- [ ] **No persistent volume for ClickHouse**: pod restart loses all data
- [ ] **Airflow DAG import path**: `airflow_tasks.py` module path may fail inside Airflow container context

### Important (functionality gaps)

- [ ] **Frontend has no API proxy in dev**: `vite.config.ts` proxies `/api → localhost:8000` but frontend K8s manifest has no backend URL injection (needs env var or nginx proxy pass)
- [ ] **No real-time data in frontend SPA**: SPA only calls `/api/v1/history` (historical). WebSocket at `/ws/realtime` is unused by frontend
- [ ] **ClickHouse no-auth**: default user with no password; credentials hardcoded in manifests
- [ ] **Airflow standalone**: not production-grade; no DAG state persistence across restarts

### Code quality

- [ ] **`main.py` FIXMEs**: StreamProcessor and YahooWebSocketClient initialized in lifespan (should be injected via DI)
- [ ] **Global DI state**: `api/dependencies.py` uses module-level singletons, not async-context-aware
- [ ] **No backend unit tests**: services and repositories have zero test coverage
- [ ] **`backend/db.py`**: legacy file, should be deleted
- [ ] **`k8s/app.yml`**: legacy manifest (unified backend+dashboard), superseded — should be deleted

### Observability

- [ ] **No structured logging**: only `basicConfig`; no request IDs, no log levels per module
- [ ] **No metrics**: no Prometheus endpoint, no latency tracking
- [ ] **No error alerting**: Airflow task failures are silent to the team

---

## Suggested Next Steps

Pick the area you want to tackle:

### A — Fix CI (unblock automated testing)
1. Fix image name mismatch: align Tiltfile `docker_build` name with `backend.yml` image ref
2. Verify `tilt ci` passes end-to-end on Kind

### B — Add ClickHouse persistence
1. Add `PersistentVolumeClaim` for ClickHouse data dir
2. Update `clickhouse.yml` to mount the PVC

### C — Wire WebSocket to frontend SPA
1. Add WS composable in Vue (`useRealtime.ts`) connecting to `/ws/realtime`
2. Push live prices into StatCards in real time

### D — Backend test coverage
1. Unit tests for `StockService`, `AlertService`, `StreamProcessor`
2. Integration test: spin up ClickHouse (testcontainers or real), hit repository methods

### E — Secure credentials
1. Move ClickHouse password + Airflow credentials to K8s Secrets
2. Reference secrets in deployment manifests via `valueFrom.secretKeyRef`

### F — Structured logging
1. Replace `basicConfig` with `structlog` or `loguru`
2. Add request middleware for trace IDs
