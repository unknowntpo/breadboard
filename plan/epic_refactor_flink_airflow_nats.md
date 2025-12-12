# Phase 2: Refactor to Flink + Airflow + NATS

## Overview

This epic covers the migration from Phase 1 MVP (in-memory processing) to Phase 2 production-grade infrastructure with:
- **Flink** for stream processing
- **Kafka** for message queuing
- **Airflow** for batch orchestration
- **NATS JetStream** for pub/sub alerts

**Trigger:** When Phase 1 is validated and needs scaling beyond:
- 100+ msg/sec sustained throughput
- Multiple consumers needed
- Complex CEP (Complex Event Processing)
- Guaranteed delivery requirements

---

## Migration Path

### 1. Stream Processing: Ibis � Flink

**Why migrate:**
- Complex windowing (tumbling, sliding, session)
- Stateful processing (aggregations across windows)
- Exactly-once semantics
- Horizontal scaling

**Migration steps:**

```python
# Phase 1: In-memory backend
con = ibis.memtable(data)

# Phase 2: Switch to Flink backend (SAME CODE!)
con = ibis.flink.connect(
    host="flink-jobmanager",
    port=8081
)

# All Ibis operations stay identical
result = (
    con
    .window(by=ibis.window(preceding=60, following=0))
    .aggregate(
        avg_price=_.price.mean(),
        max_price=_.price.max(),
        volume=_.volume.sum()
    )
)
```

**Infrastructure changes:**
- Add Flink JobManager + TaskManager to K8s
- Update `backend/stream_processor.py` connection only
- No changes to processing logic (thanks to Ibis!)

**Deployment (using Tilt):**

**Update Tiltfile:**
```python
# Tiltfile additions for Phase 2

# Deploy Flink
k8s_yaml('k8s/flink.yaml')
k8s_resource('flink-jobmanager', port_forwards='8081:8081')  # Flink UI
k8s_resource('flink-taskmanager')
```

**K8s manifest:**
```yaml
# k8s/flink.yaml
apiVersion: v1
kind: Service
metadata:
  name: flink-jobmanager
spec:
  ports:
    - port: 8081
      name: ui
    - port: 6123
      name: rpc
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flink-jobmanager
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: jobmanager
        image: flink:1.18
        command: ["jobmanager"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flink-taskmanager
spec:
  replicas: 2  # Scale horizontally
  template:
    spec:
      containers:
      - name: taskmanager
        image: flink:1.18
        command: ["taskmanager"]
```

---

### 2. Message Queue: asyncio.Queue � Kafka

**Why migrate:**
- Persistent message buffer (survive restarts)
- Multiple consumers (scale processing)
- Replay capability (reprocess data)
- Guaranteed delivery

**Migration steps:**

**Step 1: Add Kafka (using Tilt + Strimzi Operator)**

**Update Tiltfile:**
```python
# Install Strimzi operator
local_resource('install-strimzi',
  'kubectl create -f https://strimzi.io/install/latest?namespace=default || true',
  labels=['kafka']
)

# Deploy Kafka cluster
k8s_yaml('k8s/kafka.yaml')
k8s_resource('breadboard-kafka-kafka',
  resource_deps=['install-strimzi'],
  labels=['kafka']
)
```

**K8s manifest:**
```yaml
# k8s/kafka.yaml (using Strimzi operator)
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: breadboard-kafka
spec:
  kafka:
    replicas: 3
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    storage:
      type: persistent-claim
      size: 100Gi
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 10Gi
```

**Step 2: Update Producer (backend/websocket_client.py)**
```python
# Phase 1
queue = asyncio.Queue()
await queue.put(message)

# Phase 2
from aiokafka import AIOKafkaProducer

producer = AIOKafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode()
)

await producer.send('stock-prices', value=message)
```

**Step 3: Update Consumer (backend/stream_processor.py)**
```python
# Phase 2
from aiokafka import AIOKafkaConsumer

consumer = AIOKafkaConsumer(
    'stock-prices',
    bootstrap_servers='kafka:9092',
    group_id='stream-processor',
    value_deserializer=lambda m: json.loads(m.decode())
)

async for msg in consumer:
    await process_message(msg.value)
```

---

### 3. Batch Jobs: APScheduler � Airflow

**Why migrate:**
- Complex DAG dependencies
- Retry logic with backoff
- Task monitoring + alerting
- Data lineage tracking

**Migration steps:**

**Step 1: Deploy Airflow (using Tilt + Helm)**

**Update Tiltfile:**
```python
# Install Airflow via Helm
local_resource('install-airflow',
  '''
  helm repo add apache-airflow https://airflow.apache.org
  helm upgrade --install airflow apache-airflow/airflow \
    --set executor=KubernetesExecutor \
    --create-namespace \
    --namespace airflow \
    --wait
  ''',
  labels=['airflow']
)

k8s_resource('airflow-webserver',
  port_forwards='8080:8080',  # Airflow UI
  resource_deps=['install-airflow'],
  labels=['airflow']
)
```

**Or use plain K8s manifests:**
```bash
# Generate Helm template and save to k8s/airflow.yaml
helm template airflow apache-airflow/airflow \
  --set executor=KubernetesExecutor > k8s/airflow.yaml

# Then in Tiltfile:
k8s_yaml('k8s/airflow.yaml')
k8s_resource('airflow-webserver', port_forwards='8080:8080')
```

**Step 2: Convert to DAG (dags/historical_fetch.py)**
```python
# Phase 1: APScheduler
scheduler.add_job(
    fetch_historical_data,
    CronTrigger(hour='0,6,12,18')
)

# Phase 2: Airflow DAG
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'breadboard',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'historical_fetch',
    default_args=default_args,
    schedule_interval='0 */6 * * *',  # Every 6 hours
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:

    fetch_task = PythonOperator(
        task_id='fetch_symbols',
        python_callable=fetch_historical_data,
    )

    validate_task = PythonOperator(
        task_id='validate_data',
        python_callable=validate_data,
    )

    write_task = PythonOperator(
        task_id='write_clickhouse',
        python_callable=write_to_clickhouse,
    )

    fetch_task >> validate_task >> write_task
```

**Step 3: Remove APScheduler from backend/main.py**

---

### 4. Alerts: WebSocket � NATS JetStream

**Why migrate:**
- Multiple subscribers (dashboard, email, Slack, webhooks)
- Guaranteed delivery
- Message replay
- Distributed pub/sub

**Migration steps:**

**Step 1: Deploy NATS (using Tilt + Helm)**

**Update Tiltfile:**
```python
# Install NATS via Helm
local_resource('install-nats',
  '''
  helm repo add nats https://nats-io.github.io/k8s/helm/charts/
  helm upgrade --install nats nats/nats \
    --set nats.jetstream.enabled=true \
    --set nats.jetstream.memStorage.enabled=true \
    --set nats.jetstream.memStorage.size=1Gi \
    --wait
  ''',
  labels=['nats']
)

k8s_resource('nats',
  port_forwards=['4222:4222', '8222:8222'],  # Client + Monitoring
  resource_deps=['install-nats'],
  labels=['nats']
)
```

**Or use plain K8s manifests:**
```bash
# Generate Helm template
helm template nats nats/nats \
  --set nats.jetstream.enabled=true > k8s/nats.yaml

# Then in Tiltfile:
k8s_yaml('k8s/nats.yaml')
k8s_resource('nats', port_forwards=['4222:4222', '8222:8222'])
```

**Step 2: Update Publisher (backend/stream_processor.py)**
```python
# Phase 2
import nats
from nats.js import JetStreamContext

nc = await nats.connect("nats://nats:4222")
js: JetStreamContext = nc.jetstream()

# Create stream
await js.add_stream(name="ALERTS", subjects=["alerts.*"])

# Publish alert
await js.publish(
    "alerts.price_drop",
    json.dumps({
        "symbol": "AAPL",
        "change_percent": -6.5,
        "timestamp": datetime.now().isoformat()
    }).encode()
)
```

**Step 3: Add Subscribers**

**Dashboard (dashboard/app.py)**
```python
async def subscribe_alerts():
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    sub = await js.subscribe("alerts.*", durable="dashboard")

    async for msg in sub.messages:
        alert = json.loads(msg.data.decode())
        st.warning(f"Alert: {alert['symbol']} dropped {alert['change_percent']}%")
        await msg.ack()
```

**Email notifier (new service)**
```python
# services/email_notifier.py
async def send_email_alerts():
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()

    sub = await js.subscribe("alerts.*", durable="email-service")

    async for msg in sub.messages:
        alert = json.loads(msg.data.decode())
        send_email(to=ALERT_EMAIL, subject=f"Price Alert: {alert['symbol']}", ...)
        await msg.ack()
```

---

## Infrastructure Comparison

| Component | Phase 1 (MVP) | Phase 2 (Production) |
|-----------|---------------|---------------------|
| **Stream Processing** | Ibis in-memory | Ibis + Flink |
| **Message Queue** | asyncio.Queue | Kafka (3 brokers) |
| **Batch Jobs** | APScheduler | Airflow (K8s executor) |
| **Alerts** | FastAPI WebSocket | NATS JetStream |
| **Database** | ClickHouse (1 node) | ClickHouse (3 replicas) |
| **Containers** | 1 (ClickHouse) | 10+ (Kafka, Flink, Airflow, NATS) |
| **Complexity** | Low | Medium-High |
| **Throughput** | <1K msg/sec | 10K+ msg/sec |
| **Reliability** | Best effort | Guaranteed delivery |

---

## Migration Checklist

### Pre-migration
- [ ] Phase 1 success criteria all met
- [ ] Load testing shows bottlenecks (>1K msg/sec)
- [ ] Team trained on Flink, Kafka, Airflow, NATS
- [ ] Monitoring + alerting in place

### Kafka Migration
- [ ] Deploy Kafka cluster (3 brokers)
- [ ] Create topics (stock-prices, crypto-prices)
- [ ] Update producer (websocket_client.py)
- [ ] Update consumer (stream_processor.py)
- [ ] Test message durability (restart pods)
- [ ] Monitor consumer lag

### Flink Migration
- [ ] Deploy Flink JobManager + TaskManagers
- [ ] Update Ibis connection in stream_processor.py
- [ ] Test windowing operations
- [ ] Verify state checkpointing
- [ ] Monitor Flink metrics

### Airflow Migration
- [ ] Deploy Airflow (Helm chart)
- [ ] Convert APScheduler jobs to DAGs
- [ ] Test DAG execution
- [ ] Configure alerts on failures
- [ ] Remove APScheduler from backend

### NATS Migration
- [ ] Deploy NATS with JetStream
- [ ] Create alert streams
- [ ] Update publisher in stream_processor
- [ ] Deploy subscriber services (dashboard, email)
- [ ] Test message replay
- [ ] Monitor delivery guarantees

### Validation
- [ ] End-to-end integration test
- [ ] Load test (10K msg/sec)
- [ ] Chaos engineering (kill pods)
- [ ] Verify exactly-once processing
- [ ] Check alert delivery across all channels

---

## Rollback Plan

If Phase 2 migration fails:

1. **Kafka rollback:**
   - Switch producer back to asyncio.Queue
   - Redeploy Phase 1 backend
   - Messages in Kafka retained for replay

2. **Flink rollback:**
   - Switch Ibis connection back to in-memory
   - Processing continues (data loss during migration)

3. **Airflow rollback:**
   - Re-enable APScheduler in backend/main.py
   - Airflow DAGs remain for future use

4. **NATS rollback:**
   - Revert to FastAPI WebSocket broadcasts
   - NATS subscribers gracefully shutdown

---

## Estimated Effort

| Task | Duration |
|------|----------|
| Kafka migration | 1-2 days |
| Flink migration | 2-3 days |
| Airflow migration | 1-2 days |
| NATS migration | 1 day |
| Testing + validation | 2-3 days |
| **Total** | **1.5-2 weeks** |

---

## Success Criteria (Phase 2 Complete)

 System handles 10K msg/sec sustained
 Zero message loss during pod restarts
 Airflow DAGs execute on schedule with retry logic
 Alerts delivered to multiple channels (dashboard, email, Slack)
 Flink checkpoints working (state recovery)
 Kafka consumer lag <10 seconds
 All Phase 1 functionality preserved

---

---

## Complete Phase 2 Tiltfile

```python
# Tiltfile - Phase 2 (Production Stack)
# https://docs.tilt.dev/

### Phase 1 Services (Keep) ###

# Build application images
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

# Deploy core services
k8s_yaml(['k8s/clickhouse.yml', 'k8s/backend.yml', 'k8s/dashboard.yml'])

k8s_resource('backend', port_forwards='8000:8000', labels=['core'])
k8s_resource('dashboard', port_forwards='8501:8501', labels=['core'])
k8s_resource('clickhouse', port_forwards=['9000:9000', '8123:8123'], labels=['core'])

### Phase 2 Services (New) ###

# Kafka (Strimzi Operator)
local_resource('install-strimzi',
  'kubectl create -f https://strimzi.io/install/latest?namespace=default || true',
  labels=['kafka']
)

k8s_yaml('k8s/kafka.yaml')
k8s_resource('breadboard-kafka-kafka',
  resource_deps=['install-strimzi'],
  labels=['kafka']
)

# Flink
k8s_yaml('k8s/flink.yaml')
k8s_resource('flink-jobmanager',
  port_forwards='8081:8081',  # Flink UI
  labels=['streaming']
)
k8s_resource('flink-taskmanager', labels=['streaming'])

# Airflow (Helm)
local_resource('install-airflow',
  '''
  helm repo add apache-airflow https://airflow.apache.org
  helm upgrade --install airflow apache-airflow/airflow \
    --set executor=KubernetesExecutor \
    --create-namespace \
    --namespace airflow \
    --wait
  ''',
  labels=['batch']
)

k8s_resource('airflow-webserver',
  port_forwards='8080:8080',  # Airflow UI
  resource_deps=['install-airflow'],
  labels=['batch']
)

k8s_resource('airflow-scheduler',
  resource_deps=['install-airflow'],
  labels=['batch']
)

# NATS (Helm)
local_resource('install-nats',
  '''
  helm repo add nats https://nats-io.github.io/k8s/helm/charts/
  helm upgrade --install nats nats/nats \
    --set nats.jetstream.enabled=true \
    --set nats.jetstream.memStorage.enabled=true \
    --set nats.jetstream.memStorage.size=1Gi \
    --wait
  ''',
  labels=['messaging']
)

k8s_resource('nats',
  port_forwards=['4222:4222', '8222:8222'],  # Client + Monitoring
  resource_deps=['install-nats'],
  labels=['messaging']
)

### Tilt UI Configuration ###

# Group services by function
# In Tilt UI, services will be grouped by labels:
# - core: Backend, Dashboard, ClickHouse
# - kafka: Kafka cluster
# - streaming: Flink
# - batch: Airflow
# - messaging: NATS

# Helpful commands
print("""
🚀 Phase 2 Stack Running!

Services:
  • Backend API:    http://localhost:8000
  • Dashboard:      http://localhost:8501
  • ClickHouse UI:  http://localhost:8123/play
  • Flink UI:       http://localhost:8081
  • Airflow UI:     http://localhost:8080
  • NATS Monitor:   http://localhost:8222

Press 'space' to open Tilt UI
Press 'q' to quit
""")
```

**Usage:**
```bash
# Start entire Phase 2 stack
tilt up

# Start only specific labels
tilt up core streaming  # Just backend + Flink

# Stop everything
tilt down
```

**Tilt UI Features:**
- **Live logs** for all services
- **Resource status** (green = healthy)
- **Port forwards** clickable links
- **Build times** for each image
- **Resource groups** by label (core, kafka, streaming, etc.)

---

## Why Not Phase 2 Immediately?

**Phase 1 first because:**
1. **Faster time-to-value** - Working dashboard in 2-3 days vs 2-3 weeks
2. **Lower complexity** - Single app vs 10+ services to manage
3. **Validate requirements** - Ensure architecture meets needs before scaling
4. **Team learning** - Learn Ibis API before adding Flink complexity
5. **Cost** - $50/mo (ClickHouse only) vs $500+/mo (full stack)

**Philosophy:** Make it work � Make it right � Make it fast

Phase 1 proves the concept. Phase 2 scales it.
