# Binance Square Content Bot

## Project Overview
A Python-based Telegram bot that automatically scans Binance crypto market data and posts formatted content to Telegram channels. It runs on a scheduler, generating posts across multiple categories throughout the day.

## Architecture

### Pure Python Backend (no frontend)
- `main.py` — Entry point: validates env, runs startup test, starts scheduler
- `scheduler.py` — APScheduler-based job runner; posts 8 times/day across categories
- `market_scanner.py` — Fetches top futures coins, gainers, and watchlist from Binance API
- `indicators.py` — Calculates RSI, trend, and breakout signals from OHLCV data
- `charts.py` — Generates candlestick charts using mplfinance/matplotlib
- `ai_writer.py` — Uses Gemini or OpenRouter LLM to write post content
- `telegram_sender.py` — Sends text + chart images to Telegram via Bot API
- `templates.py` — Post templates for all content categories
- `config.py` — Schedule config: posts per day, hours, cooldowns

### Post Categories
- Top Gainers (2/day)
- Market Update (1/day)
- Technical Analysis (2/day)
- Altcoin Watchlist (1/day)
- Breaking Signals (2/day)

## Dependencies
Managed via `requirements.txt`:
- APScheduler, requests, pandas, numpy, matplotlib, mplfinance, openai, python-dotenv

## Environment Variables Required
| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Target channel/chat ID |
| `AI_PROVIDER` | No | "gemini" (default) or "openrouter" |
| `GEMINI_API_KEY` | If gemini | Google AI Studio key |
| `AI_INTEGRATIONS_OPENROUTER_BASE_URL` | If openrouter | OpenRouter base URL |
| `AI_INTEGRATIONS_OPENROUTER_API_KEY` | If openrouter | OpenRouter key |

## Workflow
- **Start application**: `python main.py` (console output, no port)
- On start: runs a single startup test post, then enters scheduler loop
- Scheduler posts between 08:00–20:00 UTC daily

## Notes
- No web frontend — this is a headless bot service
- Charts are saved as PNG files in `/charts/` directory
- Cooldown system prevents posting the same coin too frequently
