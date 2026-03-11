import os
import asyncio
import logging
from telegram import Bot

logger = logging.getLogger(__name__)

_bot = None


def _get_bot():
    global _bot
    if _bot is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
        _bot = Bot(token=token)
    return _bot


def _get_chat_id():
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID not set")
    return chat_id


async def _send_message_async(text, image_path=None):
    bot = _get_bot()
    chat_id = _get_chat_id()

    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text[:1024],
                    parse_mode=None,
                )
            if len(text) > 1024:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text[1024:],
                )
            try:
                os.remove(image_path)
                logger.info(f"Deleted chart: {image_path}")
            except Exception as e:
                logger.warning(f"Could not delete chart {image_path}: {e}")
            logger.info(f"Sent post with chart to Telegram")
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
            )
            logger.info(f"Sent text post to Telegram")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_post(text, image_path=None):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _send_message_async(text, image_path))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_send_message_async(text, image_path))
    except RuntimeError:
        return asyncio.run(_send_message_async(text, image_path))
