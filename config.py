MIN_GAIN_PERCENT = 10.0

TOP_COINS_LIMIT = 20

COOLDOWN_HOURS = 6

# Total posts per day by category (max 8 to stay within Binance Square limits)
# 5 short posts + 3 articles = 8 total allowed per day
POSTS_PER_DAY = {
    "top_gainers": 2,        # 🔥 Top Gainers
    "market_update": 1,      # 📊 Market Update
    "technical_analysis": 2, # 📈 Technical Analysis
    "altcoin_watchlist": 1,  # 👀 Altcoin Watchlist
    "breaking_signals": 2,  # ⚡ Breaking Signal
}

# Posting window (UTC hours)
POST_START_HOUR = 8
POST_END_HOUR = 20

AI_ANALYSIS_CHANCE = 1.0

AI_MAX_BODY_WORDS = 150

MIN_POST_CHARS = 100
