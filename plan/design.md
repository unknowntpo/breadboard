# Breadboard

Real time stock pricing dashboard.

## Architecture

### Realtime websocket data

yFinanceProvider -> Kafka -> Flink -> Clickhouse -> pricing event (eg. rise / drop)
PolygonProvider 

### Historical data

yFinanceProvider -> Airflow jobs -> Clickhouse -> Dashboard 
PolygonProvider 


## Back of Envelope Estimation

### Assumptions
- DAU: 1M users
- Symbols tracked: 2,000 (NYSE) + 500 (NASDAQ top) = 2,500 total
- Market hours: 6.5h/day (9:30-16:00 EST), 5 days/week = ~260 trading days/year
- Update frequency: 1 msg/symbol/second during market hours
- Off-market: 1 msg/symbol/min (after-hours + crypto 24/7)

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

**Market hours (peak):**
- 2,500 symbols × 1 msg/sec × 200 bytes = 500 KB/sec
- Per day: 500 KB/s × 6.5h × 3600s = 11.7 GB/day
- Per month: 11.7 GB × 22 days = 257 GB/month
- Per year: 11.7 GB × 260 days = 3 TB/year

**Off-hours (crypto/after-hours):**
- 2,500 symbols × 1 msg/min × 200 bytes = 8.3 KB/sec
- Per day (17.5h): 8.3 KB/s × 17.5h × 3600s = 523 MB/day
- Per month: 523 MB × 30 days = 15.7 GB/month

**Total real-time ingestion:**
- Daily: ~12.2 GB
- Monthly: ~273 GB
- Yearly: ~3.15 TB

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
- 12.2 GB/day × 7 = 85.4 GB
- With 3x replication: ~256 GB
- Recommended: 500 GB cluster

### ClickHouse Storage

**Real-time table (90-day retention):**
- 12.2 GB/day × 90 = 1.1 TB raw
- Compressed (3:1): ~367 GB

**Historical aggregated (5-year):**
- Minute: 40 GB
- Daily: 1 GB
- Total: ~41 GB

**Total ClickHouse: ~410 GB (recommend 1 TB cluster)**

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

**Real-time = 1 msg/10s (reduce frequency):**
- Ingress: ÷10 = 1.22 GB/day
- Storage: ÷10 = 41 GB ClickHouse
- Kafka: 100 GB cluster sufficient
- Cost savings: ~30%

