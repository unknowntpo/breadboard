import json
import base64
import sys
from typing import Optional, Dict, Any, List
from websockets.sync.client import connect
from yfinance.pricing_pb2 import PricingData
from google.protobuf.json_format import MessageToDict
import yfinance as yf


def decode_message(base64_message: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_bytes: bytes = base64.b64decode(base64_message)
        pricing_data: PricingData = PricingData()
        pricing_data.ParseFromString(decoded_bytes)
        return MessageToDict(pricing_data, preserving_proto_field_name=True)
    except Exception:
        return None


def get_historical_data(symbol: str, period: str = "1y", start: Optional[str] = None, end: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch historical candlestick data for a symbol.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        period: Period string (e.g., '1y', '6mo', '3mo', '1mo') - ignored if start/end provided
        start: Start date in YYYY-MM-DD format (optional, overrides period)
        end: End date in YYYY-MM-DD format (optional, overrides period)

    Returns:
        Dict with symbol, records, and record_count, or None if fetch fails
    """
    try:
        ticker: yf.Ticker = yf.Ticker(symbol)

        # Use start/end dates if provided, otherwise use period
        if start or end:
            hist = ticker.history(start=start, end=end)
        else:
            hist = ticker.history(period=period)

        # Convert to serializable format
        data_records: List[Dict[str, Any]] = []
        for date, row in hist.iterrows():
            record: Dict[str, Any] = {
                "date": str(date.strftime("%Y-%m-%d")),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            }
            data_records.append(record)

        result: Dict[str, Any] = {
            "symbol": symbol,
            "records": data_records,
            "record_count": len(data_records),
            "date_range": {
                "start": start,
                "end": end,
                "period": period if not (start or end) else None
            }
        }
        return result
    except Exception:
        return None


def print_data_head(data: Optional[Dict[str, Any]], num_rows: int = 5) -> None:
    """Print first N rows of historical data."""
    if not data:
        print("  No data to display")
        return

    records: List[Dict[str, Any]] = data.get("records", [])
    symbol: str = data.get("symbol", "Unknown")
    date_range: Dict[str, Any] = data.get("date_range", {})

    # Show date range if available
    range_str: str = ""
    if date_range.get("start") or date_range.get("end"):
        range_str = f" ({date_range.get('start', '?')} to {date_range.get('end', '?')})"
    elif date_range.get("period"):
        range_str = f" ({date_range.get('period')})"

    print(f"\n  Sample data for {symbol}{range_str} (first {min(num_rows, len(records))} rows):")
    print(f"  {'-'*70}")
    print(f"  {'Date':<12} | {'Open':<10} | {'High':<10} | {'Low':<10} | {'Close':<10} | {'Volume':<12}")
    print(f"  {'-'*70}")

    for record in records[:num_rows]:
        date_val: str = record.get("date", "N/A")
        open_val: float = record.get("open", 0.0)
        high_val: float = record.get("high", 0.0)
        low_val: float = record.get("low", 0.0)
        close_val: float = record.get("close", 0.0)
        volume_val: int = record.get("volume", 0)

        print(f"  {date_val:<12} | {open_val:<10.2f} | {high_val:<10.2f} | {low_val:<10.2f} | {close_val:<10.2f} | {volume_val:<12}")


def query_candlestick(symbol: str, start: str, end: str) -> None:
    """
    Query and display candlestick data for a specific date range.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
    """
    print(f"\nFetching candlestick data for {symbol} from {start} to {end}...")
    data: Optional[Dict[str, Any]] = get_historical_data(symbol, start=start, end=end)

    if data:
        records: List[Dict[str, Any]] = data.get("records", [])
        print(f"\nFound {len(records)} trading days\n")

        print(f"  {'Date':<12} | {'Open':<10} | {'High':<10} | {'Low':<10} | {'Close':<10} | {'Volume':<12} | {'Change %':<8}")
        print(f"  {'-'*95}")

        prev_close: Optional[float] = None
        for record in records:
            date_val: str = record.get("date", "N/A")
            open_val: float = record.get("open", 0.0)
            high_val: float = record.get("high", 0.0)
            low_val: float = record.get("low", 0.0)
            close_val: float = record.get("close", 0.0)
            volume_val: int = record.get("volume", 0)

            # Calculate daily change percentage
            change_pct: float = 0.0
            if prev_close:
                change_pct = ((close_val - prev_close) / prev_close) * 100
            prev_close = close_val

            print(f"  {date_val:<12} | {open_val:<10.2f} | {high_val:<10.2f} | {low_val:<10.2f} | {close_val:<10.2f} | {volume_val:<12} | {change_pct:>7.2f}%")

        # Summary statistics
        closes: List[float] = [r.get("close", 0.0) for r in records]
        highs: List[float] = [r.get("high", 0.0) for r in records]
        lows: List[float] = [r.get("low", 0.0) for r in records]

        if closes:
            print(f"\n  {'-'*95}")
            print(f"  Summary: Open={records[0].get('open', 0.0):.2f}, High={max(highs):.2f}, Low={min(lows):.2f}, Close={closes[-1]:.2f}")
            print(f"  Change: {((closes[-1] - records[0].get('open', 0.0)) / records[0].get('open', 0.0) * 100):.2f}%\n")
    else:
        print(f"Failed to fetch data for {symbol}")


def calculate_data_size(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate serialized data size in bytes and human-readable format."""
    json_str: str = json.dumps(data, default=str)
    size_bytes: int = len(json_str.encode('utf-8'))

    # Convert to human-readable format
    if size_bytes < 1024:
        size_str: str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.2f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

    result: Dict[str, Any] = {
        "size_bytes": size_bytes,
        "size_readable": size_str,
        "json_str_length": len(json_str)
    }
    return result


def estimate_storage(symbols: List[str], period: str = "1y") -> None:
    """Fetch historical data and estimate storage requirements."""
    print(f"\n{'='*80}")
    print(f"Historical Data Analysis - Back of Envelope Estimation")
    print(f"{'='*80}\n")

    total_size_bytes: int = 0
    symbol_sizes: List[Dict[str, Any]] = []

    for symbol in symbols:
        print(f"Fetching historical data for {symbol}...")
        data: Optional[Dict[str, Any]] = get_historical_data(symbol, period)

        if data:
            size_info: Dict[str, Any] = calculate_data_size(data)
            total_size_bytes += size_info["size_bytes"]

            symbol_sizes.append({
                "symbol": symbol,
                "records": data["record_count"],
                "size": size_info["size_readable"],
                "size_bytes": size_info["size_bytes"]
            })

            print(f"  {symbol}: {data['record_count']} records, {size_info['size_readable']}")
            print_data_head(data, num_rows=3)
        else:
            print(f"  {symbol}: Failed to fetch data")

    # Estimation calculations
    print(f"\n{'-'*80}")
    print("Per-Symbol Storage (1 year daily data):")
    print(f"{'-'*80}")
    for item in symbol_sizes:
        print(f"  {item['symbol']:<10} | {item['records']:<6} records | {item['size']:<12}")

    avg_size: float = total_size_bytes / len(symbol_sizes) if symbol_sizes else 0

    print(f"\n{'-'*80}")
    print("Storage Estimation:")
    print(f"{'-'*80}")
    print(f"  Average size per symbol (1 year): {avg_size / 1024:.2f} KB")
    print(f"  Total symbols (NYSE ~2000): {2000 * avg_size / (1024*1024):.2f} MB per year")
    print(f"  5-year historical: {2000 * avg_size * 5 / (1024*1024*1024):.2f} GB")
    print(f"\n  Hourly updates (assuming 1 msg/symbol): {2000 * 0.2 / 1024:.2f} MB/hour")
    print(f"  Daily updates: {2000 * 0.2 * 24 / (1024*1024):.2f} GB/day")
    print(f"  Yearly updates: {2000 * 0.2 * 24 * 365 / (1024*1024*1024):.2f} GB/year")
    print(f"{'='*80}\n")


def monitor_market_data(symbols: List[str]) -> None:
    # Yahoo Finance WebSocket Endpoint (Version 1)
    # Note: Version 2 (wss://streamer.finance.yahoo.com/?version=2) seems to require stricter auth/cookies
    # and sends data wrapped in JSON, whereas V1 sends raw Base64 strings.
    url: str = "wss://streamer.finance.yahoo.com/"

    # Origin header is required for the connection to be accepted
    headers: Dict[str, str] = {"Origin": "https://finance.yahoo.com"}

    print(f"Connecting to {url}...")
    try:
        with connect(url, additional_headers=headers) as websocket:
            print("Connected successfully.")

            # Subscribe to the requested symbols
            subscribe_message: str = json.dumps({"subscribe": symbols})
            print(f"Subscribing to: {', '.join(symbols)}")
            websocket.send(subscribe_message)

            print("\nListening for real-time data... (Press Ctrl+C to stop)")
            print("-" * 60)
            print(f"{'Symbol':<10} | {'Price':<10} | {'Time':<15} | {'Change %':<10}")
            print("-" * 60)

            while True:
                try:
                    message: str = websocket.recv()

                    # Try to decode the message
                    # V1 sends raw Base64 string
                    data: Optional[Dict[str, Any]] = decode_message(message)

                    # data is like this:
                    # {
                    #     'id': 'NVDA',
                    #     'price': 179.99,
                    #     'time': '1765438790000',
                    #     'exchange': 'NMS',
                    #     'quote_type': 8,
                    #     'market_hours': 4,
                    #     'change_percent': -2.0622447,
                    #     'change': -3.7899933,
                    #     'price_hint': '2',
                    # }

                    if data:
                        symbol: str = data.get("id", "Unknown")
                        price: float = data.get("price", 0.0)
                        timestamp: str = data.get("time", "N/A")
                        change_percent: float = data.get("change_percent", 0.0)

                        # Simple formatting
                        print(
                            f"{symbol:<10} | {price:<10.2f} | {timestamp:<15} | {change_percent:<10.2f}%"
                        )

                except Exception as e:
                    print(f"Error processing message: {e}")

    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"\nConnection Error: {e}")


if __name__ == "__main__":
    # Example symbols to track
    # You can add regular stocks (AAPL, MSFT) or Crypto (BTC-USD, ETH-USD)
    SYMBOLS_TO_TRACK: List[str] = [
        "AAPL", "BTC-USD", "NVDA", "TSLA", "META",
        "AMZN", "GOOGL", "MSFT", "SPY", "QQQ",
        "ETH-USD", "SOL-USD", "AMD", "NFLX", "COIN",
        "EURUSD=X", "GC=F"  # Forex and Gold Futures
    ]

    if len(sys.argv) > 1:
        cmd: str = sys.argv[1]

        if cmd == "--estimate":
            estimate_storage(SYMBOLS_TO_TRACK)
        elif cmd == "--candle" and len(sys.argv) >= 5:
            # Usage: python script.py --candle AAPL 2024-01-01 2024-01-31
            symbol: str = sys.argv[2]
            start_date: str = sys.argv[3]
            end_date: str = sys.argv[4]
            query_candlestick(symbol, start_date, end_date)
        elif cmd == "--help" or cmd == "-h":
            print("Usage:")
            print("  python yahoo_websocket_client.py                           # Real-time WebSocket monitoring")
            print("  python yahoo_websocket_client.py --estimate                # Historical data size estimation")
            print("  python yahoo_websocket_client.py --candle SYMBOL START END # Candlestick data for date range")
            print("\nExamples:")
            print("  python yahoo_websocket_client.py --candle AAPL 2024-01-01 2024-01-31")
            print("  python yahoo_websocket_client.py --candle NVDA 2023-01-01 2023-12-31")
        else:
            print(f"Unknown option: {cmd}")
            print("Run with --help for usage information")
    else:
        monitor_market_data(SYMBOLS_TO_TRACK)
