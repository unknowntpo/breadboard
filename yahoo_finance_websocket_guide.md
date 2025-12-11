# Yahoo Finance WebSocket API Exploration Guide with `websocat`

This guide provides instructions on how to connect to and explore the Yahoo Finance WebSocket API using the `websocat` command-line tool.

## Introduction

Yahoo Finance offers an undocumented WebSocket API for real-time market data. While not officially supported, it can be accessed for exploration using tools like `websocat`. The data streamed through this API is typically encoded in Protocol Buffers (Protobuf) and then Base64-encoded.

## Prerequisites

*   **`websocat`**: A command-line client for WebSockets. If you don't have it installed, you can usually install it via your system's package manager (e.g., `brew install websocat` on macOS, `sudo apt install websocat` on Debian/Ubuntu, or from source).

## How to Connect and Subscribe

The Yahoo Finance WebSocket API requires a specific `Origin` header to accept connections and subscriptions.

1.  **Connect to the WebSocket Server:**

    Open your terminal and run the following command. This will establish a connection to the Yahoo Finance WebSocket server:

    ```bash
    websocat -H="Origin: https://finance.yahoo.com" wss://streamer.finance.yahoo.com/
    ```

    *   The `-H="Origin: https://finance.yahoo.com"` flag is crucial, as the server will likely close the connection without this header.
    *   `wss://streamer.finance.yahoo.com/` is the WebSocket endpoint.

2.  **Subscribe to a Symbol:**

    Once connected, `websocat` will wait for input. Type the following JSON message into the terminal and press Enter to subscribe to real-time data for Apple (AAPL):

    ```json
    {"subscribe": ["AAPL"]}
    ```

    You can replace `"AAPL"` with any other valid stock ticker or cryptocurrency symbol (e.g., `"GOOG"`, `"MSFT"`, `"BTC-USD"`). You can also subscribe to multiple symbols: `{"subscribe": ["AAPL", "GOOG", "MSFT"]}`.

## Understanding the Output

After subscribing, you will start receiving messages directly in your terminal. These messages will appear as long, seemingly random strings of characters, similar to this:

```
CgRBQVBMFYUrikMYwJ/jw+FmKgNOTVMwCDgERe0PYL9lACkcwNgBBA==
```

*   **Base64 Encoded:** The output you see is Base64 encoded.
*   **Protobuf Data:** Beneath the Base64 encoding, the actual data is serialized using Protocol Buffers.
    *   The example above, when partially decoded, reveals `AAPL` at its beginning, indicating it's data for that stock.
*   **Decoding:** To interpret this data meaningfully, you would need the specific `.proto` schema used by Yahoo Finance and a Protobuf decoder. Without the `.proto` file, precise decoding is challenging, but tools can sometimes infer the structure.

## One-Liner for Immediate Subscription

To send the subscription message immediately and **keep the connection open**, use this command:

```bash
(echo '{"subscribe": ["AAPL"]}'; cat) | websocat -H="Origin: https://finance.yahoo.com" wss://streamer.finance.yahoo.com/
```

**Why the `cat`?**
A simple `echo | websocat` closes the input stream immediately after sending the message, causing `websocat` to close the connection before any data is received. Adding `; cat` keeps the input stream open (waiting for your keyboard input), allowing the WebSocket to stay connected and stream data.

## Important Considerations

*   **Undocumented API:** This API is undocumented and unofficial. Yahoo may change its structure, endpoints, or data formats at any time without notice.
*   **Terms of Use:** Always refer to Yahoo's terms of use regarding data access. This method is primarily for personal exploration and educational purposes.
*   **Market Hours:** Real-time data will only stream when markets are open and active for the subscribed symbols. During off-hours, you may see fewer or no updates.