import os
import random
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")
import logging

logger = logging.getLogger(__name__)

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

TRADINGVIEW_PRO = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    marketcolors=mpf.make_marketcolors(
        up="#26a69a", down="#ef5350",
        edge="inherit", wick="inherit",
        volume={"up": "#26a69a80", "down": "#ef535080"},
    ),
    figcolor="#131722", facecolor="#131722",
    edgecolor="#2a2e39", gridcolor="#2a2e39",
    gridstyle="-", y_on_right=True,
    rc={
        "font.size": 9,
        "axes.labelcolor": "#d1d4dc",
        "xtick.color": "#787b86",
        "ytick.color": "#787b86",
    },
)

LIGHT_CLASSIC = mpf.make_mpf_style(
    base_mpf_style="yahoo",
    marketcolors=mpf.make_marketcolors(
        up="#22ab94", down="#f23645",
        edge="inherit", wick="inherit",
        volume={"up": "#22ab9480", "down": "#f2364580"},
    ),
    figcolor="#ffffff", facecolor="#ffffff",
    edgecolor="#e0e3eb", gridcolor="#e0e3eb",
    gridstyle="-", y_on_right=True,
    rc={
        "font.size": 9,
        "axes.labelcolor": "#131722",
        "xtick.color": "#787b86",
        "ytick.color": "#787b86",
    },
)

STYLE_CONFIGS = {
    "tradingview_pro": {
        "style": TRADINGVIEW_PRO,
        "ema_colors": ("#2962ff", "#ff6d00"),
        "rsi_color": "#ab47bc",
        "rsi_hi": "#ff5252",
        "rsi_lo": "#69f0ae",
    },
    "light_classic": {
        "style": LIGHT_CLASSIC,
        "ema_colors": ("#2962ff", "#ff6d00"),
        "rsi_color": "#7b1fa2",
        "rsi_hi": "#f23645",
        "rsi_lo": "#22ab94",
    },
}

STYLE_NAMES = list(STYLE_CONFIGS.keys())


def generate_chart(symbol, interval, df=None, indicators=None):
    from indicators import fetch_klines

    if df is None:
        df = fetch_klines(symbol, interval, limit=80)

    if df is None or df.empty:
        logger.error(f"No data to generate chart for {symbol} {interval}")
        return None

    coin_name = symbol.replace("USDT", "")
    interval_label = {"1h": "1H", "4h": "4H", "1d": "1D"}.get(interval, interval)

    chosen = random.choice(STYLE_NAMES)
    cfg = STYLE_CONFIGS[chosen]
    logger.info(f"Using chart style: {chosen}")

    addplots = []

    try:
        import ta as ta_lib
        close = df["close"]

        ema20_color, ema50_color = cfg["ema_colors"]
        ema_20 = ta_lib.trend.EMAIndicator(close, window=20).ema_indicator()
        ema_50 = ta_lib.trend.EMAIndicator(close, window=50).ema_indicator()
        addplots.append(mpf.make_addplot(ema_20, color=ema20_color, width=1.2, label="EMA 20"))
        addplots.append(mpf.make_addplot(ema_50, color=ema50_color, width=1.2, label="EMA 50"))

        rsi = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
        addplots.append(mpf.make_addplot(rsi, panel=2, color=cfg["rsi_color"], width=1.0, ylabel="RSI"))
        rsi_70 = [70] * len(rsi)
        rsi_30 = [30] * len(rsi)
        addplots.append(mpf.make_addplot(rsi_70, panel=2, color=cfg["rsi_hi"], width=0.5, linestyle="--"))
        addplots.append(mpf.make_addplot(rsi_30, panel=2, color=cfg["rsi_lo"], width=0.5, linestyle="--"))
    except Exception as e:
        logger.warning(f"Could not add indicators to chart: {e}")

    filename = f"{coin_name}_{interval}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    try:
        mpf.plot(
            df,
            type="candle",
            style=cfg["style"],
            title=f"\n{coin_name}/USDT {interval_label} Chart",
            volume=True,
            addplot=addplots if addplots else None,
            savefig=dict(fname=filepath, dpi=150, bbox_inches="tight"),
            figsize=(12, 8),
            panel_ratios=(6, 2, 2) if addplots else (6, 2),
        )
        logger.info(f"Chart saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to generate chart for {symbol}: {e}")
        return None
