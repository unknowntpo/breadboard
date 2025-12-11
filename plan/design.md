# Breadboard

Real time stock pricing dashboard.

## Architecture

### Realtime websocket data

yFinanceProvider -> Kafka -> Flink -> Clickhouse -> pricing event (eg. rise / drop)
PolygonProvider 

### Historical data

yFinanceProvider -> Airflow jobs -> Clickhouse -> Dashboard 
PolygonProvider 
