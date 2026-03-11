import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

bot_dir = Path(__file__).resolve().parent
load_dotenv(bot_dir / ".env")
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot")

from market_scanner import get_top_futures_coins, get_top_gainers, get_market_overview
from indicators import calculate_indicators
from charts import generate_chart
from ai_writer import write_top_gainers
from telegram_sender import send_post
from scheduler import create_scheduler


def check_env():
    missing = []
    for var in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Set them in your environment or .env file")
        sys.exit(1)

    provider = os.environ.get("AI_PROVIDER", "openrouter").lower()
    provider_info = {
        "gemini":    ("GEMINI_API_KEY",  "Gemini (gemini-2.0-flash)"),
        "openai":    ("OPENAI_API_KEY",  "OpenAI (gpt-4o-mini)"),
        "groq":      ("GROQ_API_KEY",    "Groq (llama-3.3-70b-versatile)"),
        "openrouter":("AI_INTEGRATIONS_OPENROUTER_API_KEY", "OpenRouter (llama-3.3-70b)"),
    }
    if provider in provider_info:
        key_name, label = provider_info[provider]
        if not os.environ.get(key_name):
            logger.warning(f"AI_PROVIDER={provider} but {key_name} not set — AI rewriting will be skipped")
        else:
            logger.info(f"AI Provider: {label}")
    else:
        logger.warning(f"Unknown AI_PROVIDER={provider}, AI rewriting will be skipped")

    logger.info("All environment variables OK")


def run_startup_test():
    logger.info("=" * 50)
    logger.info("STARTUP TEST: Generating sample post...")
    logger.info("=" * 50)

    coins = get_top_futures_coins()
    if not coins:
        logger.error("Failed to fetch market data from Binance")
        sys.exit(1)

    logger.info(f"Fetched {len(coins)} top futures coins")
    for c in coins[:5]:
        logger.info(f"  {c['rank']}. {c['coin']}: ${c['price']:,.4f} ({'+' if c['change_pct'] > 0 else ''}{c['change_pct']:.1f}%)")

    gainers = get_top_gainers(coins)
    logger.info(f"Found {len(gainers)} coins above +10%")

    indicators = None
    chart_path = None
    if coins:
        test_coin = coins[0]
        indicators = calculate_indicators(test_coin["symbol"], "4h")
        if indicators:
            logger.info(f"Indicators for {test_coin['coin']}: RSI={indicators['rsi']}, Trend={indicators['trend']}")

        chart_path = generate_chart(test_coin["symbol"], "4h")
        if chart_path:
            logger.info(f"Chart generated: {chart_path}")

    gainer_ind = None
    if gainers:
        gainer_ind = calculate_indicators(gainers[0]["symbol"], "4h")
    elif coins:
        gainer_ind = indicators

    text, featured_coin, _all = write_top_gainers(gainers, coins, indicators=gainer_ind)

    if featured_coin:
        chart_path = generate_chart(featured_coin["symbol"], "4h")
        if chart_path:
            logger.info(f"Chart generated for {featured_coin['coin']}: {chart_path}")

    logger.info(f"Generated post ({len(text)} chars):")
    logger.info("-" * 40)
    logger.info(text)
    logger.info("-" * 40)

    success = send_post(text, chart_path if featured_coin else None)
    if success:
        logger.info("Startup test post sent to Telegram!")
    else:
        logger.warning("Failed to send startup test post. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")

    logger.info("=" * 50)
    logger.info("STARTUP TEST COMPLETE")
    logger.info("=" * 50)


def main():
    logger.info("Binance Square Content Bot Starting...")
    check_env()

    run_startup_test()

    scheduler = create_scheduler()

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
