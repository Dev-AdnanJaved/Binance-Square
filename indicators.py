import requests
import pandas as pd
import ta
import logging

logger = logging.getLogger(__name__)

KLINES_URL = "https://data-api.binance.vision/api/v3/klines"


def fetch_klines(symbol, interval="1h", limit=100):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        resp = requests.get(KLINES_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
            df[col] = df[col].astype(float)

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("open_time", inplace=True)

        return df
    except Exception as e:
        logger.error(f"Failed to fetch klines for {symbol} {interval}: {e}")
        return None


def calculate_indicators(symbol, interval="4h"):
    df = fetch_klines(symbol, interval, limit=100)
    if df is None or df.empty:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    rsi_indicator = ta.momentum.RSIIndicator(close, window=14)
    rsi = rsi_indicator.rsi().iloc[-1]

    ema_20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema_50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]

    current_price = close.iloc[-1]

    prev_high = high.iloc[-2]
    prev_low = low.iloc[-2]
    prev_close = close.iloc[-2]
    pivot = (prev_high + prev_low + prev_close) / 3
    support_1 = 2 * pivot - prev_high
    resistance_1 = 2 * pivot - prev_low
    support_2 = pivot - (prev_high - prev_low)
    resistance_2 = pivot + (prev_high - prev_low)

    recent_vol = volume.iloc[-5:].mean()
    older_vol = volume.iloc[-10:-5].mean()
    volume_trend = "rising" if recent_vol > older_vol * 1.1 else "falling" if recent_vol < older_vol * 0.9 else "stable"

    trend = "bullish" if current_price > ema_20 > ema_50 else "bearish" if current_price < ema_20 < ema_50 else "neutral"

    return {
        "symbol": symbol,
        "interval": interval,
        "price": round(current_price, 4),
        "rsi": round(rsi, 1),
        "ema_20": round(ema_20, 4),
        "ema_50": round(ema_50, 4),
        "pivot": round(pivot, 4),
        "support_1": round(support_1, 4),
        "resistance_1": round(resistance_1, 4),
        "support_2": round(support_2, 4),
        "resistance_2": round(resistance_2, 4),
        "volume_trend": volume_trend,
        "trend": trend,
        "df": df,
    }


def check_breakout(indicators):
    if indicators is None:
        return None

    signals = []

    if indicators["rsi"] > 70:
        signals.append({
            "type": "rsi_overbought",
            "message": f"RSI at {indicators['rsi']} — overbought territory",
        })

    if indicators["price"] > indicators["resistance_1"]:
        signals.append({
            "type": "breakout",
            "message": f"Price broke above R1 resistance at ${indicators['resistance_1']:.4f}",
        })

    if indicators["price"] < indicators["support_1"]:
        signals.append({
            "type": "breakdown",
            "message": f"Price dropped below S1 support at ${indicators['support_1']:.4f}",
        })

    if indicators["volume_trend"] == "rising" and indicators["trend"] == "bullish":
        signals.append({
            "type": "momentum",
            "message": "Rising volume with bullish trend — strong momentum",
        })

    return signals
