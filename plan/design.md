# Breadboard

Real time stock pricing dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                                 │
└─────────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐         ┌──────────────┐
   │  yFinance    │         │  Polygon.io  │
   │  WebSocket   │         │  WebSocket   │
   └──────┬───────┘         └──────┬───────┘
          │                        │
          └────────┬───────────────┘
                   │ Real-time pricing stream
                   │ Peak: 2.5K msg/sec (0.5 MB/sec)
                   │ Avg:  42 msg/sec (8.4 KB/sec)
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REAL-TIME STREAMING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌──────────────┐
          │    Kafka     │  ◄── Message buffer (7-day retention)
          │  (3 brokers) │      500 GB cluster
          └──────┬───────┘
                 │ Topics: stock-prices, crypto-prices
                 │
                 ▼
          ┌──────────────┐
          │    Flink     │  ◄── Stream processing
          │ (2 workers)  │      - Windowing (1min, 5min aggregates)
          └──────┬───────┘      - Anomaly detection
                 │              - Pricing alerts (rise/drop %)
                 │
                 ├─────────────────┬──────────────────┐
                 ▼                 ▼
        ┌────────────────┐  ┌──────────────┐
        │  ClickHouse    │  │     NATS     │  ◄── Pub/sub messaging
        │ (3 replicas)   │  │ (JetStream)  │      Alert events
        └────────────────┘  └──────┬───────┘
         - Real-time table          │
           (90-day retention)       │
         - Minute aggregates        │
                                    ▼
                          ┌──────────────────┐
                          │ Notification Svc │
                          │  (subscribes to  │
                          │  NATS subjects)  │
                          └──────────────────┘
                           Email/Webhook/Push

┌─────────────────────────────────────────────────────────────────────────────┐
│                      BATCH PROCESSING PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐         ┌──────────────┐
   │  yFinance    │         │  Polygon.io  │
   │  REST API    │         │  REST API    │
   └──────┬───────┘         └──────┬───────┘
          │                        │
          └────────┬───────────────┘
                   │ Daily OHLCV fetch
                   ▼
          ┌──────────────┐
          │   Airflow    │  ◄── DAG scheduler (daily/weekly jobs)
          │  (1 worker)  │      - Backfill historical
          └──────┬───────┘      - Daily aggregation
                 │              - Data quality checks
                 ▼
          ┌──────────────┐
          │  ClickHouse  │  ◄── Historical storage
          │              │      - Daily OHLCV (5-year)
          └──────────────┘      - Minute candles (compressed)

┌─────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                   │
└─────────────────────────────────────────────────────────────────────────────┘

          ┌──────────────────────────────────┐
          │        FastAPI Backend           │
          │  (Python 3.11+, async/await)     │
          ├──────────────────────────────────┤
          │  Endpoints:                      │
          │  • GET  /api/v1/stocks/{symbol}  │
          │  • GET  /api/v1/history          │
          │  • GET  /api/v1/alerts           │
          │  • WS   /ws/realtime             │ ◄── WebSocket for live updates
          └────────┬─────────────────────────┘
                   │
                   │ Queries ClickHouse
                   │ Publishes to WebSocket clients
                   │
          ┌────────▼─────────────────────────┐
          │     ClickHouse Client Pool       │
          │    (connection pooling)          │
          └────────┬─────────────────────────┘
                   │
                   ▼
          ┌──────────────┐
          │  ClickHouse  │
          └──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                                     │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌───────────────────────────────────────┐
     │      Streamlit Dashboard              │
     │   (Python-based web interface)        │
     ├───────────────────────────────────────┤
     │  Pages:                               │
     │  • 📊 Real-time Monitor               │ ◄── Live charts (WebSocket)
     │  • 📈 Historical Analysis             │ ◄── Date range queries
     │  • 🔔 Alerts & Notifications          │
     │  • ⚙️  Settings & Watchlist           │
     └─────────┬─────────────────────────────┘
               │
               │ REST API calls
               │ WebSocket connection
               ▼
        [ FastAPI Backend ]

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW SUMMARY                                    │
└─────────────────────────────────────────────────────────────────────────────┘

1. Real-time path (latency: <100ms):
   Provider → Kafka → Flink → ClickHouse → FastAPI → Streamlit

2. Historical path (daily batch):
   Provider → Airflow → ClickHouse → FastAPI → Streamlit

3. Alert path:
   Flink → NATS (JetStream) → Notification Service → Email/Webhook/Push

4. User interaction:
   Streamlit → FastAPI → ClickHouse → FastAPI → Streamlit
``` 


## Back of Envelope Estimation

### Assumptions
- DAU: 1M users
- Symbols tracked: 2,000 (NYSE) + 500 (NASDAQ top) = 2,500 total
- Trading hours (stocks, weekdays):
  - Pre-market: 4:00-9:30 AM EST = 5.5h (lower volume)
  - Regular market: 9:30-16:00 EST = 6.5h (high volume)
  - After-hours: 16:00-20:00 EST = 4h (lower volume)
  - Total: 16h/day, 5 days/week = ~260 trading days/year
- Update frequency:
  - Regular market: 1 msg/symbol/second
  - Pre/after hours: 1 msg/symbol/10 seconds
  - Off-market (crypto 24/7): 1 msg/symbol/min

### WebSocket Data (Real-time)

**Message size:**
```json
{
    "id": "NVDA",
    "price": 179.99,
    "time": "1765438790000",
    "exchange": "NMS",
    "quote_type": 8,
    "market_hours": 4,
    "change_percent": -2.0622447,
    "change": -3.7899933,
    "price_hint": "2"
}
```
Avg msg size: ~200 bytes (0.2 KB)

**Regular market hours:**
- 2,500 symbols × 1 msg/sec × 200 bytes = 500 KB/sec
- Per day: 500 KB/s × 6.5h × 3600s = 11.7 GB/day
- Per year: 11.7 GB × 260 days = 3 TB/year

**Pre-market + After-hours (stocks):**
- 2,500 symbols × 0.1 msg/sec × 200 bytes = 50 KB/sec
- Per day: 50 KB/s × 9.5h × 3600s = 1.71 GB/day
- Per year: 1.71 GB × 260 days = 445 GB/year

**Off-market (crypto 24/7, weekends):**
- 2,500 symbols × 1 msg/min × 200 bytes = 8.3 KB/sec
- Stocks off (8h/day × 260 days): 8.3 KB/s × 8h × 3600s × 260 = 62 GB/year
- Weekends (48h × 52 weeks): 8.3 KB/s × 48h × 3600s × 52 = 75 GB/year
- Subtotal: 137 GB/year

**Total real-time ingestion:**
- Per trading day: 11.7 + 1.71 = 13.4 GB
- Per year: 3,000 + 445 + 137 = 3.58 TB/year
- Per month (avg): ~300 GB

### Historical Data Storage

**Daily OHLCV (Open, High, Low, Close, Volume):**
- Per symbol: ~100 bytes/day (5 floats + metadata)
- 2,500 symbols × 100 bytes × 260 days = 65 MB/year
- 5-year historical: 325 MB (raw)
- With indexing + metadata: ~1 GB

**Minute-level data (Clickhouse):**
- Market hours: 6.5h × 60 min = 390 candles/day/symbol
- 2,500 symbols × 390 × 100 bytes = 97.5 MB/day
- Per year: 97.5 MB × 260 = 25.35 GB/year
- 5-year: ~127 GB (compressed ~40 GB with ClickHouse)

### Kafka Buffer

**Retention: 7 days**
- 13.4 GB/day × 7 = 94 GB
- With 3x replication: ~282 GB
- Recommended: 500 GB cluster

### ClickHouse Storage

**Real-time table (90-day retention):**
- 13.4 GB/day × 90 = 1.2 TB raw
- Compressed (3:1): ~400 GB

**Historical aggregated (5-year):**
- Minute: 40 GB
- Daily: 1 GB
- Total: ~41 GB

**Total ClickHouse: ~441 GB (recommend 1 TB cluster)**

### Network Bandwidth

**Ingress (from providers):**
- Peak: 500 KB/s = 4 Mbps
- Off-peak: 8.3 KB/s = 66 Kbps
- Recommend: 10 Mbps sustained, 50 Mbps burst

**Egress (to users):**
- 1M DAU, avg 10 min session, 100 symbols tracked/user
- 100 symbols × 1 msg/s × 200 bytes = 20 KB/s/user
- Peak concurrent: 1M × 0.1 (10% concurrent) = 100K users
- 100K × 20 KB/s = 2 GB/s = 16 Gbps
- With CDN/compression (3:1): ~5.3 Gbps
- Recommend: 10 Gbps link

### QPS/Throughput

**Write QPS:**
- Peak: 2,500 msg/s (market hours)
- Off-peak: 42 msg/s
- Kafka: easily handles 100K+ msg/s
- ClickHouse: handles 50K+ inserts/s

**Read QPS (Dashboard queries):**
- 1M DAU × 10 queries/session / 86400s = ~116 QPS
- Peak (market open/close): 5x = 580 QPS
- ClickHouse: handles 10K+ SELECT/s

### Cost Estimate (AWS)

**Compute:**
- Kafka: 3x m5.large = $210/mo
- Flink: 2x m5.xlarge = $280/mo
- ClickHouse: 3x m5.2xlarge = $840/mo
- Airflow: 1x t3.medium = $30/mo
- Subtotal: ~$1,360/mo

**Storage:**
- Kafka (500 GB EBS): $50/mo
- ClickHouse (1 TB EBS): $100/mo
- S3 (historical backup): $23/mo
- Subtotal: ~$173/mo

**Network:**
- Data transfer out (5 TB/mo): $450/mo

**Total: ~$2,000/mo = $24K/year**

### Scaling Considerations

**10M DAU:**
- Egress: 10x = 53 Gbps (need CDN)
- Read QPS: 10x = 5,800 QPS (shard ClickHouse)
- Cost: ~$8K/mo

**Optimize update frequency (1 msg/10s everywhere):**
- Ingress: ÷10 = 1.34 GB/day
- Storage: ÷10 = 44 GB ClickHouse
- Kafka: 100 GB cluster sufficient
- Cost savings: ~30%

**Note:** Pre-market/after-hours already at 1/10 freq vs regular market

