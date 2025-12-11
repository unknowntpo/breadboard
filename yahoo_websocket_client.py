import json
import base64
import time
from websockets.sync.client import connect
from yfinance.pricing_pb2 import PricingData
from google.protobuf.json_format import MessageToDict


def decode_message(base64_message):
    try:
        decoded_bytes = base64.b64decode(base64_message)
        pricing_data = PricingData()
        pricing_data.ParseFromString(decoded_bytes)
        return MessageToDict(pricing_data, preserving_proto_field_name=True)
    except Exception as e:
        return None


def monitor_market_data(symbols: list[str]):
    # Yahoo Finance WebSocket Endpoint (Version 1)
    # Note: Version 2 (wss://streamer.finance.yahoo.com/?version=2) seems to require stricter auth/cookies
    # and sends data wrapped in JSON, whereas V1 sends raw Base64 strings.
    url = "wss://streamer.finance.yahoo.com/"

    # Origin header is required for the connection to be accepted
    headers = {"Origin": "https://finance.yahoo.com"}

    print(f"Connecting to {url}...")
    try:
        with connect(url, additional_headers=headers) as websocket:
            print("Connected successfully.")

            # Subscribe to the requested symbols
            subscribe_message = json.dumps({"subscribe": symbols})
            print(f"Subscribing to: {', '.join(symbols)}")
            websocket.send(subscribe_message)

            print("\nListening for real-time data... (Press Ctrl+C to stop)")
            print("-" * 60)
            print(f"{'Symbol':<10} | {'Price':<10} | {'Time':<15} | {'Change %':<10}")
            print("-" * 60)

            while True:
                try:
                    message = websocket.recv()

                    # Try to decode the message
                    # V1 sends raw Base64 string
                    data = decode_message(message)

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
                        symbol = data.get("id", "Unknown")
                        price = data.get("price", 0.0)
                        timestamp = data.get("time", "N/A")
                        change_percent = data.get("change_percent", 0.0)

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
    SYMBOLS_TO_TRACK: list[str] = ["AAPL", "BTC-USD", "NVDA", "TSLA", "META", "2330.TW"]

    monitor_market_data(SYMBOLS_TO_TRACK)
