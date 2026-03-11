import logging
import time
import random
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

try:
    from bot.market_scanner import get_top_futures_coins, get_top_gainers, get_market_overview, get_watchlist_coins
    from bot.indicators import calculate_indicators, check_breakout
    from bot.charts import generate_chart
    from bot.ai_writer import write_top_gainers, write_market_update, write_technical_analysis, write_altcoin_watchlist, write_breaking_signal, is_on_cooldown
    from bot.telegram_sender import send_post
except ImportError:
    from market_scanner import get_top_futures_coins, get_top_gainers, get_market_overview, get_watchlist_coins
    from indicators import calculate_indicators, check_breakout
    from charts import generate_chart
    from ai_writer import write_top_gainers, write_market_update, write_technical_analysis, write_altcoin_watchlist, write_breaking_signal, is_on_cooldown
    from telegram_sender import send_post

logger = logging.getLogger(__name__)

CHART_INTERVALS = ["1h", "4h", "1d"]


def _safe_run(func, name):
    try:
        logger.info(f"Running job: {name}")
        func()
        logger.info(f"Completed job: {name}")
    except Exception as e:
        logger.error(f"Job {name} failed: {e}", exc_info=True)


def job_top_gainers():
    coins = get_top_futures_coins()
    gainers = get_top_gainers(coins)

    if len(gainers) < 3:
        gainers = get_top_gainers(coins, min_change=5.0)
    if len(gainers) < 3:
        top_sorted = sorted(coins, key=lambda x: x["change_pct"], reverse=True)
        gainers = top_sorted[:5]

    ind = None
    if gainers:
        ind = calculate_indicators(gainers[0]["symbol"], random.choice(["1h", "4h"]))

    text, featured_coin, _all = write_top_gainers(gainers, coins, indicators=ind)

    chart_path = None
    if featured_coin:
        interval = random.choice(["1h", "4h"])
        chart_path = generate_chart(featured_coin["symbol"], interval)

    send_post(text, chart_path)


def job_market_update():
    coins = get_top_futures_coins()
    overview = get_market_overview(coins)

    text, ref_coin, coins_mentioned = write_market_update(overview)

    chart_path = None
    if ref_coin:
        interval = random.choice(["4h", "1d"])
        chart_path = generate_chart(ref_coin["symbol"], interval)

    send_post(text, chart_path)


def job_technical_analysis():
    coins = get_top_futures_coins()
    candidates = sorted(coins, key=lambda x: abs(x["change_pct"]), reverse=True)[:8]
    off_cooldown = [c for c in candidates if not is_on_cooldown(c)]
    if not off_cooldown:
        logger.info("All TA candidates on cooldown, skipping this post")
        return
    random.shuffle(off_cooldown)

    for coin in off_cooldown:
        indicators = calculate_indicators(coin["symbol"], random.choice(["4h", "1h"]))
        if indicators is None:
            continue

        text = write_technical_analysis(coin, indicators)
        chart_path = generate_chart(coin["symbol"], indicators["interval"], df=indicators.get("df"))

        send_post(text, chart_path)
        break


def job_altcoin_watchlist():
    coins = get_top_futures_coins()
    watchlist = get_watchlist_coins(coins, count=random.randint(4, 6))

    indicators_list = []
    for c in watchlist:
        ind = calculate_indicators(c["symbol"], "4h")
        indicators_list.append(ind)

    text, featured_coin, _all = write_altcoin_watchlist(watchlist, indicators_list)

    chart_path = None
    if featured_coin:
        interval = random.choice(["1h", "4h"])
        chart_path = generate_chart(featured_coin["symbol"], interval)

    send_post(text, chart_path)


def job_breaking_signals():
    coins = get_top_futures_coins()
    off_cooldown = [c for c in coins if not is_on_cooldown(c)]
    if not off_cooldown:
        logger.info("All breaking signal candidates on cooldown, skipping this post")
        return
    scan_list = off_cooldown

    for coin in scan_list:
        indicators = calculate_indicators(coin["symbol"], "1h")
        if indicators is None:
            continue

        signals = check_breakout(indicators)
        if not signals:
            continue

        text = write_breaking_signal(coin, indicators, signals)
        chart_path = generate_chart(coin["symbol"], "1h", df=indicators.get("df"))

        send_post(text, chart_path)
        break


def _generate_schedule(count, start_hour, end_hour, minute_offset=0):
    if count <= 0:
        return []
    total_minutes = (end_hour - start_hour) * 60
    gap = total_minutes / count
    schedule = []
    for i in range(count):
        offset = int(i * gap) + minute_offset
        hour = start_hour + offset // 60
        minute = offset % 60
        if hour <= end_hour:
            schedule.append((hour, minute))
    return schedule


JOB_DEFS = [
    ("top_gainers", "Top Gainers", job_top_gainers, 0),
    ("market_update", "Market Update", job_market_update, 5),
    ("technical_analysis", "Technical Analysis", job_technical_analysis, 10),
    ("altcoin_watchlist", "Altcoin Watchlist", job_altcoin_watchlist, 15),
    ("breaking_signals", "Breaking Signals", job_breaking_signals, 20),
]


def create_scheduler():
    try:
        from bot.config import POSTS_PER_DAY, POST_START_HOUR, POST_END_HOUR
    except ImportError:
        from config import POSTS_PER_DAY, POST_START_HOUR, POST_END_HOUR

    scheduler = BlockingScheduler()
    total = 0

    for key, label, job_func, minute_offset in JOB_DEFS:
        count = POSTS_PER_DAY.get(key, 5)
        schedule = _generate_schedule(count, POST_START_HOUR, POST_END_HOUR, minute_offset)
        fn = job_func
        name = label
        for hour, minute in schedule:
            scheduler.add_job(
                lambda f=fn, n=name: _safe_run(f, n),
                CronTrigger(hour=hour, minute=minute),
                id=f"{key}_{hour}_{minute}",
                name=f"{label} {hour:02d}:{minute:02d}",
            )
        total += len(schedule)
        logger.info(f"  - {label}: {len(schedule)} posts")

    logger.info(f"Scheduled {total} daily posts")

    return scheduler
