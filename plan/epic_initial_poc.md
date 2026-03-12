# Initial POC - Phase 1 Implementation Plan

## Current Progress

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
- [x] **Clean architecture** — Domain, Repository, Service, API layers
  - [x] `backend/domain/entities.py`
  - [x] `backend/domain/interfaces.py`
  - [x] `backend/repository/clickhouse_client.py`
  - [x] `backend/repository/stock_repository.py`
  - [x] `backend/services/stock_service.py`
  - [x] `backend/services/historical_service.py`
  - [x] `backend/services/alert_service.py`
  - [x] `backend/api/schemas.py`
  - [x] `backend/api/dependencies.py`
  - [x] `backend/api/routes/health.py`
  - [x] `backend/api/routes/stocks.py`
  - [x] `backend/api/routes/history.py`
  - [x] `backend/api/websocket/realtime.py`
  - [x] `backend/infrastructure/yahoo_client.py`
- [x] **Airflow migration** (Phase 1.5 - Local)
  - [x] `backend/infrastructure/airflow_tasks.py`
  - [x] `airflow/dags/historical_data_dag.py`
  - [x] `scripts/run_airflow.sh`
  - [x] Removed APScheduler from `backend/main.py`
- [x] **Airflow K8s Deployment** (Phase 1.6 - Helm)
  - [x] `airflow/Dockerfile`
  - [x] `k8s/airflow-values.yaml`
  - [x] Updated `Tiltfile`

### Frontend (Vue 3 + Vite)
- [x] `frontend/src/App.vue` (main SPA)
- [x] `frontend/src/api/history.ts` (axios client)
- [x] `frontend/src/components/SymbolTabs.vue`
- [x] `frontend/src/components/RangePicker.vue`
- [x] `frontend/src/components/StatCards.vue`
- [x] `frontend/src/components/PriceChart.vue` (lightweight-charts v5)
- [x] `frontend/src/components/OhlcvTable.vue`
- [x] **TypeScript migration** — all `.js` → `.ts`, `lang="ts"` in all SFCs
  - [x] `HistoryRecord` interface in `history.ts`
  - [x] Typed `defineProps` / `defineEmits` in all components
  - [x] `tsconfig.json` (single unified config, `moduleResolution: bundler`)
  - [x] `vite.config.ts`, `playwright.config.ts`
- [x] **Tests**
  - [x] 5 Vitest unit tests (all `.test.ts`)
  - [x] Playwright e2e spec (`historical.spec.ts`)
  - [x] GitHub Actions CI

### CI/CD
- [x] `.github/workflows/test.yml` (CI with Kind)

### System Validation
- [ ] Test Tilt + OrbStack workflow end-to-end
- [ ] Test GitHub Actions CI (Kind cluster)
- [ ] Dashboard shows live prices (1-2s updates)
- [ ] Alerts appear on >5% price drop
- [ ] Historical chart loads for any symbol/date
- [ ] System survives 1h continuous operation
- [ ] ClickHouse contains data from ≥2 fetch cycles

---

## Goal

Build minimal viable real-time stock dashboard. **Simplest tools possible → get it working → scale later.**

---

## Phase 1: MVP Stack

### Application Stack
| Component | Phase 1 Tool | Phase 2+ Migration |
|-----------|--------------|-------------------|
| **Stream Processing** | Ibis (in-memory mode) | Flink |
| **Message Queue** | asyncio.Queue | Redis Streams → Kafka |
| **Batch Jobs** | Airflow (K8s Helm) | — |
| **Database** | ClickHouse (K8s) | ClickHouse cluster |
| **Alerts** | FastAPI WebSocket | NATS JetStream |
| **API Backend** | FastAPI | FastAPI (keep) |
| **Frontend** | Vue 3 + Vite + TypeScript | — |

---

## Architecture (Phase 1)

```
┌─────────────────────────────────────────────────────────────┐
│              SINGLE FASTAPI APPLICATION                      │
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
│         │          │ Alert → WebSocket│                    │
│         │          └──────────────────┘                    │
│         ▼                                                    │
│  ┌──────────────┐                                           │
│  │ ClickHouse   │                                           │
│  └──────┬───────┘                                           │
│         ▼                                                    │
│  ┌──────────────────────────────────────┐                  │
│  │  REST API:                           │                  │
│  │  • GET /api/v1/stocks/{symbol}       │                  │
│  │  • GET /api/v1/history               │                  │
│  │  • WS  /ws/realtime                  │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────────┐
   │  Vue 3 + Vite    │
   │  TypeScript SPA  │
   │  - OHLCV chart   │
   │  - Stat cards    │
   │  - Data table    │
   └──────────────────┘

Airflow (K8s, every 6h): Fetch historical OHLCV → ClickHouse
```

---

## Phase 2+ Migration Path

| Component | Migration |
|-----------|-----------|
| Stream Processing | Ibis → Flink backend (same API) |
| Message Queue | asyncio.Queue → aiokafka |
| Alerts | WebSocket → NATS JetStream |
| Infra | Single VM → EKS cluster |

---

## Success Criteria (Phase 1 Complete)

- [ ] Dashboard shows live prices updating every 1-2 seconds
- [ ] Alert notification appears when price drops >5%
- [ ] Historical data chart loads for any symbol + date range
- [ ] System survives 1 hour of continuous operation
- [ ] ClickHouse contains data from at least 2 historical fetch cycles
- [ ] Ibis processing handles 100+ msg/sec without lag
- [ ] Docker Compose workflow works
- [ ] Tilt + OrbStack workflow works
- [ ] GitHub Actions CI passes (Kind)
- [ ] All tests pass (unit + integration)
