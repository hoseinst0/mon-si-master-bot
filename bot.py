"""
bot.py
نقطه ورود اصلی ربات. تمام روترها اینجا رجیستر میشن.
اجرا: python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import handlers_start
import handlers_listing
import handlers_escrow
import handlers_trust
import handlers_auction
import handlers_vip_antiscam
import handlers_admin
from handlers_auction import close_expired_auctions

logging.basicConfig(level=logging.INFO)


async def periodic_auction_checker(bot: Bot):
    """هر ۶۰ ثانیه چک می‌کنه مزایده‌های تموم‌شده رو ببنده."""
    while True:
        try:
            await close_expired_auctions(bot)
        except Exception as e:
            logging.exception("خطا در بررسی مزایده‌ها: %s", e)
        await asyncio.sleep(60)


async def periodic_escrow_timeout_checker(bot: Bot):
    """
    هر ۶۰ ثانیه چک می‌کنه که آیا کسی مهلت تحویل‌ش تموم شده و هنوز
    فروشنده اکانت رو تحویل نداده -> پول به خریدار برمی‌گرده.
    """
    import time
    import database as db
    while True:
        try:
            now = time.time()
            cursor = db.escrow_col.find({"status": "locked", "countdown_end": {"$lte": now}})
            async for tx in cursor:
                await db.adjust_balance(tx["buyer_id"], tx["amount"])
                await db.update_escrow_status(tx["_id"], "refunded")
                await db.set_listing_status(tx["listing_id"], "active")
                try:
                    await bot.send_message(
                        tx["buyer_id"],
                        f"⏰ مهلت تحویل فروشنده تموم شد. مبلغ {tx['amount']:,.0f} به کیف پولت برگشت.",
                    )
                    await bot.send_message(
                        tx["seller_id"],
                        "⏰ مهلت تحویل اکانت تموم شد و معامله لغو شد.",
                    )
                except Exception:
                    pass
        except Exception as e:
            logging.exception("خطا در بررسی مهلت escrow: %s", e)
        await asyncio.sleep(60)


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(handlers_start.router)
    dp.include_router(handlers_listing.router)
    dp.include_router(handlers_escrow.router)
    dp.include_router(handlers_trust.router)
    dp.include_router(handlers_auction.router)
    dp.include_router(handlers_vip_antiscam.router)
    dp.include_router(handlers_admin.router)

    asyncio.create_task(periodic_auction_checker(bot))
    asyncio.create_task(periodic_escrow_timeout_checker(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
