-- Create database
CREATE DATABASE IF NOT EXISTS breadboard;

USE breadboard;

-- Real-time stock prices table
CREATE TABLE IF NOT EXISTS stock_prices (
    timestamp DateTime,
    symbol String,
    price Float64,
    volume UInt64,
    change_percent Float64
) ENGINE = MergeTree()
ORDER BY (symbol, timestamp)
SETTINGS index_granularity = 8192;

-- Historical OHLCV data table
CREATE TABLE IF NOT EXISTS historical_data (
    date Date,
    symbol String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64
) ENGINE = MergeTree()
ORDER BY (symbol, date)
SETTINGS index_granularity = 8192;

-- Create indexes for better query performance
-- ClickHouse doesn't have traditional indexes, but we can use projections

-- Optional: Create a materialized view for 1-minute aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_prices_1min
ENGINE = SummingMergeTree()
ORDER BY (symbol, minute_timestamp)
AS SELECT
    symbol,
    toStartOfMinute(timestamp) AS minute_timestamp,
    avg(price) AS avg_price,
    max(price) AS max_price,
    min(price) AS min_price,
    sum(volume) AS total_volume,
    count() AS tick_count
FROM stock_prices
GROUP BY symbol, minute_timestamp;

-- Optional: Create a materialized view for 5-minute aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_prices_5min
ENGINE = SummingMergeTree()
ORDER BY (symbol, interval_timestamp)
AS SELECT
    symbol,
    toStartOfFiveMinutes(timestamp) AS interval_timestamp,
    avg(price) AS avg_price,
    max(price) AS max_price,
    min(price) AS min_price,
    sum(volume) AS total_volume,
    count() AS tick_count
FROM stock_prices
GROUP BY symbol, interval_timestamp;
