import asyncio
import logging
import socket
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InputRichMessage, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9166740656:AAHIcEHPpmJK7dMKFrTIwmfy018PGfQNagk"
CHAT_ID = 1013148833  # ID пользователя, группы или канала
TIMEZONE = "Asia/Yekaterinburg"  # Часовой пояс для даты и запуска в 12:15
PROXY_URL = None  # Например "socks5://127.0.0.1:10808", если нужен прокси для Telegram

MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def get_english_date() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    return f"{now.day} {MONTHS_EN[now.month - 1]} {now.year}"


async def fetch_rates() -> str:
    timeout = aiohttp.ClientTimeout(total=10)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        btc_task = session.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        ton_task = session.get("https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT")
        usd_task = session.get("https://www.cbr-xml-daily.ru/daily_json.js")
        sp500_task = session.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=1d")

        btc_resp, ton_resp, usd_resp, sp500_resp = await asyncio.gather(
            btc_task, ton_task, usd_task, sp500_task, return_exceptions=True
        )

        try:
            btc_data = await btc_resp.json()
            btc_price = f"${float(btc_data['price']):,.2f}"
        except Exception:
            btc_price = "ошибка @caveek_ai - поддержка"

        try:
            ton_data = await ton_resp.json()
            ton_price = f"${float(ton_data['price']):,.2f}"
        except Exception:
            ton_price = "ошибка @caveek_ai - поддержка"

        try:
            usd_data = await usd_resp.json(content_type=None)
            usd_val = usd_data["Valute"]["USD"]["Value"]
            usd_price = f"{float(usd_val):.2f} ₽"
        except Exception:
            usd_price = "ошибка @caveek_ai - поддержка"

        try:
            sp_data = await sp500_resp.json()
            sp_val = sp_data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            sp500_price = f"{float(sp_val):,.2f}"
        except Exception:
            sp500_price = "ошибка @caveek_ai - поддержка"

    date_str = get_english_date()

    return (
        f"<h5>Today's currency ({date_str}):</h5>"
        f'<b>'
        f'<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji> USD: {usd_price}<br>'
        f'<tg-emoji emoji-id="5231005931550030290">💸</tg-emoji> BTC: {btc_price}<br>'
        f'<tg-emoji emoji-id="5321179414174672491">💎</tg-emoji> TON: {ton_price}<br>'
        f'<tg-emoji emoji-id="5240141292628888228">🤔</tg-emoji> S&amp;P 500: {sp500_price}'
        f'</b>'
    )


async def send_daily_report(bot: Bot):
    html_text = await fetch_rates()
    await bot.send_rich_message(
        chat_id=CHAT_ID,
        rich_message=InputRichMessage(html=html_text)
    )


async def main():
    logging.basicConfig(level=logging.INFO)

    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
    else:
        session = AiohttpSession()
        session._connector_init["family"] = socket.AF_INET

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    @dp.message(Command("now"))
    async def cmd_now(message: Message):
        html_text = await fetch_rates()
        await bot.send_rich_message(
            chat_id=message.chat.id,
            rich_message=InputRichMessage(html=html_text)
        )

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_daily_report, trigger="cron", hour=12, minute=15, args=[bot])
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
