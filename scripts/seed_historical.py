#!/usr/bin/env python3
"""Seed AAPL and TSLA historical data into ClickHouse via yfinance."""

import sys
import os
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
import clickhouse_connect

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_HTTP_PORT', '8123'))
SYMBOLS = ['AAPL', 'TSLA']
PERIOD = '90d'


def main():
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database='breadboard',
    )

    for symbol in SYMBOLS:
        print(f'Fetching {symbol} ({PERIOD})...')
        df = yf.download(symbol, period=PERIOD, auto_adjust=True, progress=False)
        if df.empty:
            print(f'  No data for {symbol}, skipping.')
            continue

        df = df.reset_index()
        rows = []
        for _, row in df.iterrows():
            date = row['Date']
            if hasattr(date, 'date'):
                date = date.date()
            rows.append([
                str(date),
                symbol,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume']),
            ])

        client.insert(
            'historical_data',
            rows,
            column_names=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'],
        )
        print(f'  Inserted {len(rows)} rows for {symbol}.')

    print('Done.')


if __name__ == '__main__':
    main()
