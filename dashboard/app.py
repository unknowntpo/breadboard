import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import websockets
import json
import logging
import altair as alt

from backend.config import app_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = app_config.BACKEND_URL
WS_URL = BACKEND_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/realtime"

# Page config
st.set_page_config(
    page_title="Breadboard - Stock Dashboard",
    page_icon="📊",
    layout="wide"
)

# CSS styles for blinking animation
st.markdown("""
<style>
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.blink-update {
    animation: blink 0.5s ease-in-out 3;
}
.price-up { color: #00c853; }
.price-down { color: #ff1744; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "alerts" not in st.session_state:
    st.session_state.alerts = []

if "latest_prices" not in st.session_state:
    st.session_state.latest_prices = {}

if "prev_prices" not in st.session_state:
    st.session_state.prev_prices = {}


# Sidebar
st.sidebar.title("📊 Breadboard")
st.sidebar.markdown("Real-time Stock Dashboard")

page = st.sidebar.radio("Navigation", ["📈 Real-time Monitor", "📊 Historical Analysis", "🔔 Alerts"])


def fetch_latest_price(symbol: str):
    """Fetch latest price for a symbol from API."""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/v1/stocks/{symbol}", timeout=5.0)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return None


def fetch_historical_data(symbol: str, start_date: str, end_date: str):
    """Fetch historical data from API."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/history",
            params={"symbol": symbol, "start": start_date, "end": end_date},
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return None


def fetch_recent_prices(symbol: str, limit: int = 100):
    """Fetch recent price history for a symbol."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/api/v1/stocks/{symbol}/recent",
            params={"limit": limit},
            timeout=5.0
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error fetching recent prices: {e}")
        return None


def render_price_metric(symbol: str, price: float, change_percent: float):
    """Render custom price metric with blinking animation."""
    # Detect if price updated
    prev_price = st.session_state.prev_prices.get(symbol)
    is_updating = prev_price is not None and prev_price != price
    st.session_state.prev_prices[symbol] = price

    # Color based on change
    color_class = "price-up" if change_percent >= 0 else "price-down"
    blink_class = "blink-update" if is_updating else ""
    arrow = "▲" if change_percent >= 0 else "▼"

    st.markdown(f"""
    <div style="text-align: center; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9fa;">
        <p style="margin: 0; font-size: 14px; color: #666; font-weight: 500;">{symbol}</p>
        <p style="margin: 8px 0 0 0; font-size: 24px; font-weight: bold; color: #000;">${price:.2f}</p>
        <p class="{color_class} {blink_class}" style="margin: 8px 0 0 0; font-size: 14px; font-weight: 600;">
            {arrow} {abs(change_percent):.2f}%
        </p>
    </div>
    """, unsafe_allow_html=True)


# Page: Real-time Monitor
if page == "📈 Real-time Monitor":
    st.title("📈 Real-time Stock Monitor")

    # Watchlist
    st.sidebar.markdown("### Watchlist")
    default_symbols = ["AAPL", "NVDA", "TSLA", "BTC-USD", "ETH-USD"]
    watchlist = st.sidebar.multiselect(
        "Select symbols to watch",
        ["AAPL", "BTC-USD", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "MSFT", "SPY", "QQQ", "ETH-USD", "SOL-USD", "AMD", "NFLX", "COIN"],
        default=default_symbols
    )

    # Create columns for metrics
    if watchlist:
        cols = st.columns(min(len(watchlist), 5))

        for idx, symbol in enumerate(watchlist):
            col = cols[idx % 5]

            # Fetch latest price
            price_data = fetch_latest_price(symbol)

            if price_data:
                with col:
                    change_percent = price_data.get("change_percent", 0.0)
                    price = price_data.get("price", 0.0)
                    render_price_metric(symbol, price, change_percent)

        st.markdown("---")

        # Price chart for selected symbol
        st.subheader("Price History")
        selected_symbol = st.selectbox("Select symbol for chart", watchlist)

        if selected_symbol:
            recent_data = fetch_recent_prices(selected_symbol, limit=100)

            if recent_data and recent_data.get("records"):
                df = pd.DataFrame(recent_data["records"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")

                # Dynamic Y-axis with Altair
                y_min = df["price"].min() * 0.995
                y_max = df["price"].max() * 1.005

                chart = alt.Chart(df).mark_line().encode(
                    x=alt.X('timestamp:T', title='Time'),
                    y=alt.Y('price:Q',
                            title='Price ($)',
                            scale=alt.Scale(domain=[y_min, y_max]))
                ).properties(
                    height=400,
                    title=f"{selected_symbol} Price History"
                ).interactive()

                st.altair_chart(chart, use_container_width=True)

                # Show data table
                with st.expander("View Data Table"):
                    st.dataframe(df[["timestamp", "price", "volume", "change_percent"]])

        # Auto-refresh
        st.sidebar.markdown("---")
        auto_refresh = st.sidebar.checkbox("Auto-refresh (every 5s)", value=True)

        if auto_refresh:
            import time
            time.sleep(5)
            st.rerun()


# Page: Historical Analysis
elif page == "📊 Historical Analysis":
    st.title("📊 Historical Analysis")

    # Input controls
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol = st.selectbox(
            "Symbol",
            ["AAPL", "BTC-USD", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "MSFT"]
        )

    with col2:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30)
        )

    with col3:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )

    if st.button("Fetch Data"):
        with st.spinner("Fetching historical data..."):
            data = fetch_historical_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if data and data.get("records"):
                df = pd.DataFrame(data["records"])

                st.success(f"Fetched {len(df)} trading days")

                # Summary statistics
                st.subheader("Summary Statistics")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Open", f"${df.iloc[0]['open']:.2f}")
                with col2:
                    st.metric("Close", f"${df.iloc[-1]['close']:.2f}")
                with col3:
                    st.metric("High", f"${df['high'].max():.2f}")
                with col4:
                    st.metric("Low", f"${df['low'].min():.2f}")

                # OHLC Chart
                st.subheader("Price Chart")

                # Convert date column to datetime
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")

                # Line chart for close price
                st.line_chart(df.set_index("date")["close"])

                # Data table
                st.subheader("Data Table")
                st.dataframe(df)

            else:
                st.warning("No data found for the selected date range")


# Page: Alerts
elif page == "🔔 Alerts":
    st.title("🔔 Price Alerts")

    st.markdown("### Recent Alerts")

    if st.session_state.alerts:
        for alert in reversed(st.session_state.alerts[-20:]):
            alert_type = alert.get("type", "unknown")
            symbol = alert["data"].get("symbol", "N/A")
            change_percent = alert["data"].get("change_percent", 0.0)
            price = alert["data"].get("price", 0.0)
            timestamp = alert["data"].get("timestamp", "")

            st.warning(
                f"**{symbol}** dropped {change_percent:.2f}% to ${price:.2f} at {timestamp}"
            )
    else:
        st.info("No alerts yet. Alerts will appear here when price drops >= 5%.")

    # Alert configuration
    st.markdown("---")
    st.subheader("Alert Settings")

    st.info("Current threshold: Price drop >= 5%")
    st.markdown("Alerts are automatically triggered when any symbol drops 5% or more.")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Status**")
try:
    response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
    if response.status_code == 200:
        health = response.json()
        st.sidebar.success("✅ Backend Online")
        st.sidebar.caption(f"Queue: {health.get('queue_size', 0)} msgs")
        st.sidebar.caption(f"WS Clients: {health.get('websocket_clients', 0)}")
    else:
        st.sidebar.error("❌ Backend Offline")
except Exception:
    st.sidebar.error("❌ Backend Unreachable")
