import os
import random
import logging
import time
from datetime import datetime
from openai import OpenAI

from config import COOLDOWN_HOURS, AI_ANALYSIS_CHANCE, AI_MAX_BODY_WORDS, MIN_POST_CHARS
from templates import TOP_GAINERS, MARKET_UPDATES, TECHNICAL_ANALYSIS, ALTCOIN_WATCHLIST, BREAKING_SIGNALS

logger = logging.getLogger(__name__)

AI_PROVIDER = os.environ.get("AI_PROVIDER", "openrouter").lower()

MODELS = {
    "openrouter": "meta-llama/llama-3.3-70b-instruct",
    "gemini": "gemini-2.0-flash",
}

MODEL = MODELS.get(AI_PROVIDER, MODELS["openrouter"])
_client = None


def _get_client():
    global _client
    if _client is None:
        if AI_PROVIDER == "gemini":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not set")
                return None
            _client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key,
            )
            logger.info(f"Using Gemini AI (model: {MODEL})")
        else:
            base_url = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")
            api_key = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")
            if not base_url or not api_key:
                return None
            _client = OpenAI(base_url=base_url, api_key=api_key)
            logger.info(f"Using OpenRouter AI (model: {MODEL})")
    return _client


HUMOR_PROMPTS = [
    "You are a clean, professional crypto analyst on Binance Square. You write structured posts with clear numbers, key levels, and concise analysis. ALWAYS use $COINNAME cashtag format for ALL coin mentions. Use emojis as section markers (📈 for bullish data, ⚠️ for risks/warnings, ✅ for confirmations). Write in a calm, educational tone — never hypey.",
    "You're a respected Binance Square analyst who writes clean, data-driven posts. Every post has clear numbers (prices, percentages, support/resistance levels, RSI, EMAs) formatted concisely. ALWAYS use $COINNAME cashtag format. Use 📈 ⚠️ ✅ as line starters to structure the post visually. Educational and grounded.",
    "You are a professional market analyst on Binance Square. Your posts are clean and structured — key data up front, risk warnings clearly marked, and a plain-language explanation paragraph. ALWAYS use $COINNAME cashtag format. Use 📈 ⚠️ ✅ to mark sections. No hype, no filler.",
    "You're a trusted Binance Square creator who writes concise, well-structured analysis posts. Numbers are always clear and prominent. Use $COINNAME cashtag format for every coin. Structure with 📈 ⚠️ ✅ section markers. Calm, analytical, educational.",
]


def _format_indicator_block(indicators):
    if not indicators:
        return ""
    parts = []
    parts.append(f"RSI: {indicators.get('rsi', 'N/A')}")
    parts.append(f"EMA20: {_fmt_price(indicators['ema_20'])}" if 'ema_20' in indicators else "")
    parts.append(f"EMA50: {_fmt_price(indicators['ema_50'])}" if 'ema_50' in indicators else "")
    parts.append(f"Support S1: {_fmt_price(indicators['support_1'])}" if 'support_1' in indicators else "")
    parts.append(f"Support S2: {_fmt_price(indicators['support_2'])}" if 'support_2' in indicators else "")
    parts.append(f"Resistance R1: {_fmt_price(indicators['resistance_1'])}" if 'resistance_1' in indicators else "")
    parts.append(f"Resistance R2: {_fmt_price(indicators['resistance_2'])}" if 'resistance_2' in indicators else "")
    parts.append(f"Trend: {indicators.get('trend', 'N/A')}")
    parts.append(f"Volume: {indicators.get('volume_trend', 'N/A')}")
    return "\n".join(p for p in parts if p)


import re as _re

CTA_PATTERNS = [
    "Does the volume profile support continuation for",
    "What's your read on the current structure of",
    "How are you managing risk on",
    "Where do you see the next key level for",
    "What does this setup tell you about",
    "Is the risk/reward worth it here on",
    "What's your technical read on",
    "How do you interpret this price action on",
]


def _ensure_post_quality(text):
    if len(text) < MIN_POST_CHARS:
        padding = random.choice([
            "\n\nDYOR — always manage your risk.",
            "\n\nThis is one to watch closely over the next few sessions.",
            "\n\nVolume and momentum will tell the real story here.",
            "\n\nKeep this on your radar — the setup is developing.",
        ])
        text += padding

    last_lines = "\n".join(text.strip().split("\n")[-3:])
    has_question = "?" in last_lines
    if not has_question:
        text = text.rstrip()
        cta = random.choice(CTA_PATTERNS)
        coins_in_text = _re.findall(r'\$[A-Z]{2,10}', text)
        if coins_in_text:
            text += f"\n\n{cta} {coins_in_text[0]}?"
        else:
            text += f"\n\n{cta} this setup?"

    return text


def _add_humor(text, indicators=None):
    client = _get_client()
    if client is None:
        return _break_paragraphs(text)

    system = random.choice(HUMOR_PROMPTS)

    add_analysis = indicators is not None and random.random() < AI_ANALYSIS_CHANCE
    indicator_section = ""
    analysis_rule = ""

    if add_analysis and indicators:
        indicator_section = f"\n\nReal indicator data:\n{_format_indicator_block(indicators)}"
        analysis_rule = """Use the real indicator data. Be specific with actual numbers."""

    prompt = f"""Rewrite this crypto post for Binance Square. Follow this EXACT structure:

LINE 1 — 📈 Short summary: coin(s), price, percentage move, trend direction. 1-2 sentences max. End with ✅.

LINE 2 — ⚠️ Risk: RSI reading + what it means. 1 sentence.

LEVELS SECTION — If support/resistance or indicators exist, list them as numbered points:

Resistance Levels
1: [price]
2: [price]

Support Levels
1: [price]
2: [price]

Indicators
RSI: [value]
EMA20: [value]
EMA50: [value]

SHORT PARAGRAPH — 1-2 sentences max explaining WHY this move matters. No emoji. Keep it brief.

QUESTION — One short question for engagement.

RULES:
- Keep ALL prices and numbers EXACTLY as given
- ALWAYS use $COINNAME cashtag format (e.g. $BTC not BTC)
- Keep paragraphs SHORT — max 2 sentences each
- List support/resistance/indicators as numbered points, NOT inline text
- NO hype words (moon, rocket, gem, 100x)
- Post MUST be at least {MIN_POST_CHARS} characters
- {analysis_rule}

EXAMPLE OUTPUT:
📈 $BTC steady at $70,507, trend stable with low volume ✅

⚠️ RSI 55 — neutral momentum, minor reversal risk.

Resistance Levels
1: 73,042
2: 75,100

Support Levels
1: 68,391
2: 66,800

Indicators
RSI: 55
EMA20: 69,500
EMA50: 67,200

Buyers holding key levels after the recent rally. A volume spike would signal the next move.

What's your read on $BTC's next move?

Post to rewrite:
{text}{indicator_section}

Output ONLY the rewritten post, nothing else."""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=800,
            temperature=0.85,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        result = resp.choices[0].message.content.strip()
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if len(result) > 50:
            result = _ensure_post_quality(result)
            return result
        fallback = _break_paragraphs(text)
        return _ensure_post_quality(fallback)
    except Exception as e:
        logger.warning(f"AI humor pass failed, using plain template: {e}")
        fallback = _break_paragraphs(text)
        return _ensure_post_quality(fallback)


def _break_paragraphs(text):
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 300:
            sentences = []
            for s in stripped.replace(". ", ".\n").split("\n"):
                sentences.append(s.strip())
            chunks = []
            current = []
            for s in sentences:
                current.append(s)
                if len(current) >= 2:
                    chunks.append(" ".join(current))
                    current = []
            if current:
                chunks.append(" ".join(current))
            result.append("\n\n".join(chunks))
        else:
            result.append(line)
    return "\n".join(result)

COOLDOWN_SECONDS = COOLDOWN_HOURS * 60 * 60
_coin_last_posted = {}


def _get_coin_name(c):
    if isinstance(c, str):
        return c.replace("$", "")
    return c.get("coin", "").replace("$", "")


def is_on_cooldown(coin):
    name = _get_coin_name(coin)
    last = _coin_last_posted.get(name)
    if last is None:
        return False
    return (time.time() - last) < COOLDOWN_SECONDS


def _record_post(coin):
    name = _get_coin_name(coin)
    _coin_last_posted[name] = time.time()
    logger.info(f"Cooldown set for {name} (6h)")


def _pick_off_cooldown(coins):
    available = [c for c in coins if not is_on_cooldown(c)]
    if available:
        return random.choice(available)
    return None

PATTERN_DESCRIPTIONS = [
    "higher lows forming consistently",
    "a series of higher highs and higher lows",
    "tight consolidation near resistance",
    "a rising wedge pattern",
    "an ascending triangle formation",
    "a bullish flag developing",
    "compression with declining sell volume",
    "a clean base with volume supporting",
    "a cup and handle pattern",
    "a symmetrical triangle tightening",
    "a bull pennant forming",
    "steady accumulation at higher levels",
    "a breakout retest holding cleanly",
    "a double bottom forming at support",
    "a rounding bottom developing",
]

INDICATOR_NAMES = [
    "RSI", "MACD", "EMA crossover", "volume profile",
    "Bollinger Bands", "momentum oscillator", "OBV",
    "Stochastic RSI", "VWAP", "moving average convergence",
]

_used_tg = []
_used_mu = []
_used_ta = []
_used_aw = []
_used_bs = []


def _pick_template(pool, used):
    if len(used) >= len(pool):
        used.clear()
    remaining = [t for t in pool if t not in used]
    if not remaining:
        used.clear()
        remaining = pool[:]
    choice = random.choice(remaining)
    used.append(choice)
    return choice


def _fmt_price(price):
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:,.4f}"
    elif price >= 0.01:
        return f"{price:.4f}"
    else:
        return f"{price:.6f}"


def _compute_target(price, change_pct):
    if change_pct > 0:
        factor = 1 + random.uniform(0.03, 0.08)
    else:
        factor = 1 + random.uniform(0.02, 0.05)
    return price * factor


def _fill_template(template, coin_data, indicators=None):
    coin_name = coin_data.get("coin", "")
    price = coin_data.get("price", 0)
    change_pct = coin_data.get("change_pct", 0)

    support = indicators.get("support_1", price * 0.97) if indicators else price * 0.97
    resistance = indicators.get("resistance_1", price * 1.03) if indicators else price * 1.03
    target = _compute_target(price, change_pct)
    trend = indicators.get("trend", "bullish" if change_pct > 0 else "neutral") if indicators else ("bullish" if change_pct > 0 else "neutral")
    vol_trend = indicators.get("volume_trend", "above average") if indicators else "above average"
    interval = indicators.get("interval", "4h") if indicators else random.choice(["1h", "4h", "1d"])

    direction = "upside" if change_pct > 0 else "downside"
    rsi_val = indicators.get("rsi", 55) if indicators else 55
    indicator_name = random.choice(INDICATOR_NAMES)
    pattern_desc = random.choice(PATTERN_DESCRIPTIONS)

    replacements = {
        "{COIN}": f"${coin_name}",
        "{PRICE}": _fmt_price(price),
        "{PERCENT}": f"{abs(change_pct):.1f}",
        "{TARGET}": _fmt_price(target),
        "{SUPPORT}": _fmt_price(support),
        "{RESISTANCE}": _fmt_price(resistance),
        "{TREND}": trend,
        "{TIMEFRAME}": interval,
        "{INDICATOR}": indicator_name,
        "{PATTERN_DESCRIPTION}": pattern_desc,
        "{DIRECTION}": direction,
        "{DATE}": datetime.utcnow().strftime("%B %d"),
        "{VOLUME_DESCRIPTION}": vol_trend,
    }

    text = template
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, str(value))

    return text


GENERAL_HASHTAGS = [
    "#Altcoins", "#CryptoNews", "#CryptoTrends", "#Crypto",
    "#Trading", "#TechnicalAnalysis", "#MarketUpdate", "#Blockchain",
]


def _hashtags(coins, category="top_gainers"):
    tags = []
    for c in coins[:8]:
        coin = c if isinstance(c, str) else c.get("coin", "")
        coin = coin.replace("$", "")
        if coin:
            tags.append(f"#{coin}")
    tags += random.sample(GENERAL_HASHTAGS, random.randint(1, 2))
    seen = set()
    unique = []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)
    return " ".join(unique)


def _dollar_tags(coins):
    tags = []
    for c in coins[:8]:
        coin = c if isinstance(c, str) else c.get("coin", "")
        coin = coin.replace("$", "")
        if coin:
            tags.append(f"${coin}")
    seen = set()
    unique = []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)
    return " ".join(unique)


def _build_gainers_list(coins_for_post):
    lines = []
    for i, c in enumerate(coins_for_post, 1):
        name = c.get("coin", "")
        pct = c.get("change_pct", 0)
        price = c.get("price", 0)
        lines.append(f"{i}. ${name}: +{abs(pct):.1f}% — ${_fmt_price(price)}")
    return "\n".join(lines)


def write_top_gainers(gainers, all_coins, indicators=None):
    if not gainers:
        coins_for_post = all_coins[:5]
    else:
        coins_for_post = gainers[:]

    if not coins_for_post:
        return "Market data unavailable right now.", None, []

    off_cooldown = [c for c in coins_for_post if not is_on_cooldown(c)]
    if off_cooldown:
        coins_for_post = off_cooldown

    max_count = min(5, len(coins_for_post))
    min_count = min(3, max_count)
    count = random.randint(min_count, max_count)
    coins_for_post = coins_for_post[:count]

    featured = coins_for_post[0]
    for c in coins_for_post:
        _record_post(c)

    gainers_list = _build_gainers_list(coins_for_post)

    prompt_text = f"Today's top gainers:\n\n{gainers_list}"
    prompt_text = _add_humor(prompt_text, indicators)

    text = "🔥 Top Gainers\n\n" + prompt_text
    text += "\n\n" + _hashtags(coins_for_post, "top_gainers")
    return text, featured, coins_for_post


def write_market_update(overview):
    btc = overview.get("btc")
    eth = overview.get("eth")

    candidates = [c for c in [btc, eth] if c and not is_on_cooldown(c)]
    if not candidates:
        candidates = [c for c in [btc, eth] if c]
    if not candidates:
        candidates = [c for c in overview.get("coins", []) if not is_on_cooldown(c)]
    ref_coin = candidates[0] if candidates else (btc or eth or (overview["coins"][0] if overview["coins"] else None))
    if not ref_coin:
        return "Market data unavailable right now.", []

    _record_post(ref_coin)

    template = _pick_template(MARKET_UPDATES, _used_mu)
    text = _fill_template(template, ref_coin)
    text = _add_humor(text, None)

    coins_mentioned = [c for c in [btc, eth] if c]
    top_movers = sorted(overview["coins"], key=lambda x: abs(x["change_pct"]), reverse=True)[:3]
    coins_mentioned += top_movers

    text = "📊 Market Update\n\n" + text
    text += "\n\n" + _hashtags(coins_mentioned, "market_update")
    return text, ref_coin, coins_mentioned


def write_technical_analysis(coin, indicators):
    _record_post(coin)

    template = _pick_template(TECHNICAL_ANALYSIS, _used_ta)
    text = _fill_template(template, coin, indicators)
    text = _add_humor(text, indicators)

    text = "📈 Technical Analysis\n\n" + text
    text += "\n\n" + _hashtags([coin], "technical_analysis")
    return text


def write_altcoin_watchlist(watchlist_coins, indicators_list):
    if not watchlist_coins:
        return "No watchlist coins available.", []

    available = [(i, c) for i, c in enumerate(watchlist_coins) if not is_on_cooldown(c)]
    if not available:
        available = list(enumerate(watchlist_coins))
    idx, featured = random.choice(available)
    ind = indicators_list[idx] if idx < len(indicators_list) else None
    _record_post(featured)
    template = _pick_template(ALTCOIN_WATCHLIST, _used_aw)
    text = _fill_template(template, featured, ind)
    text = _add_humor(text, ind)

    text = "👀 Altcoin Watchlist\n\n" + text
    text += "\n\n" + _hashtags(watchlist_coins, "altcoin_watchlist")
    return text, featured, watchlist_coins


def write_breaking_signal(coin, indicators, signals):
    _record_post(coin)

    template = _pick_template(BREAKING_SIGNALS, _used_bs)
    text = _fill_template(template, coin, indicators)
    text = _add_humor(text, indicators)

    text = "⚡ Breaking Signal\n\n" + text
    text += "\n\n" + _hashtags([coin], "breaking_signals")
    return text
