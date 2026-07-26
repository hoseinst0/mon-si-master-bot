# ============================================================
#  RAVENMORE ACADEMY RPG BOT — Entry Point
#  آکادمی ریون‌مور — ربات نقش‌آفرینی تلگرامی
# ============================================================
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import letters

# هندلرها — ترتیب ثبت مهم است:
# quest_handlers باید قبل از start_handlers ثبت شود چون تریگرهای متنیِ
# کوئست‌های مخفی نباید توسط هندلر آزادِ start_handlers قاپیده شوند.
import quest_handlers
import shop_handlers
import spell_handlers
import duel_handlers
import admin_handlers
import start_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ravenmore.bot")


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است (متغیر محیطی).")
    if not config.MONGODB_URL:
        raise RuntimeError("MONGODB_URL تنظیم نشده است (متغیر محیطی).")

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(quest_handlers.router)
    dp.include_router(shop_handlers.router)
    dp.include_router(spell_handlers.router)
    dp.include_router(duel_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(start_handlers.router)

    asyncio.create_task(letters.letter_scheduler_loop(bot))

    logger.info("Ravenmore Academy bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
