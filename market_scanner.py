import requests
import logging
from config import TOP_COINS_LIMIT, MIN_GAIN_PERCENT

logger = logging.getLogger(__name__)

TICKER_URL = "https://data-api.binance.vision/api/v3/ticker/24hr"


def get_top_futures_coins(limit=None):
    if limit is None:
        limit = TOP_COINS_LIMIT
    try:
        resp = requests.get(TICKER_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        STABLECOINS = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDPUSDT", "FDUSDUSDT", "DAIUSDT", "EURUSDT", "USD1USDT", "PAXGUSDT", "WBTCUSDT", "WBETHUSDT", "STETHUSDT"}
        usdt_pairs = [
            t for t in data
            if t["symbol"].endswith("USDT")
            and not t["symbol"].endswith("DOMUSDT")
            and "_" not in t["symbol"]
            and t["symbol"] not in STABLECOINS
        ]

        usdt_pairs.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
        top = usdt_pairs[:limit]

        coins = []
        for rank, t in enumerate(top, 1):
            symbol = t["symbol"]
            coin_name = symbol.replace("USDT", "")
            coins.append({
                "symbol": symbol,
                "coin": coin_name,
                "price": float(t.get("lastPrice", 0)),
                "change_pct": float(t.get("priceChangePercent", 0)),
                "volume": float(t.get("quoteVolume", 0)),
                "high_24h": float(t.get("highPrice", 0)),
                "low_24h": float(t.get("lowPrice", 0)),
                "rank": rank,
            })

        return coins
    except Exception as e:
        logger.error(f"Failed to fetch futures tickers: {e}")
        return []


def get_top_gainers(coins=None, min_change=None):
    if min_change is None:
        min_change = MIN_GAIN_PERCENT
    if coins is None:
        coins = get_top_futures_coins()

    gainers = [c for c in coins if c["change_pct"] >= min_change]
    gainers.sort(key=lambda x: x["change_pct"], reverse=True)
    return gainers


def get_market_overview(coins=None):
    if coins is None:
        coins = get_top_futures_coins()

    btc = next((c for c in coins if c["coin"] == "BTC"), None)
    eth = next((c for c in coins if c["coin"] == "ETH"), None)

    bullish = sum(1 for c in coins if c["change_pct"] > 0)
    bearish = sum(1 for c in coins if c["change_pct"] < 0)

    return {
        "btc": btc,
        "eth": eth,
        "coins": coins,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "total": len(coins),
    }


def get_watchlist_coins(coins=None, count=5):
    if coins is None:
        coins = get_top_futures_coins()

    sorted_coins = sorted(coins, key=lambda x: abs(x["change_pct"]), reverse=True)
    return sorted_coins[:count]
