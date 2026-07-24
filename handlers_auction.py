"""
handlers_auction.py
سیستم مزایده برای اکانت‌های نایاب: ثبت پیشنهاد قیمت اتمیک + جلوگیری از race condition
"""
import time
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from states import AuctionBidFlow
from config import AUCTION_MIN_BID_INCREMENT_PERCENT

router = Router(name="auction")


@router.callback_query(F.data.startswith("bid_"))
async def start_bid(callback: CallbackQuery, state: FSMContext):
    listing_id = callback.data.split("bid_", 1)[1]
    listing = await db.get_listing(listing_id)
    if not listing or listing["status"] != "active" or not listing.get("is_auction"):
        await callback.answer("این مزایده دیگه فعال نیست.", show_alert=True)
        return
    if listing.get("auction_end_at") and listing["auction_end_at"] < time.time():
        await callback.answer("زمان این مزایده تموم شده.", show_alert=True)
        return
    if listing["seller_id"] == callback.from_user.id:
        await callback.answer("نمی‌تونی رو اکانت خودت پیشنهاد بدی!", show_alert=True)
        return

    min_next_bid = listing["current_bid"] * (1 + AUCTION_MIN_BID_INCREMENT_PERCENT / 100)
    await state.update_data(listing_id=listing_id, min_next_bid=min_next_bid)
    await state.set_state(AuctionBidFlow.enter_amount)
    await callback.message.answer(
        f"💰 پیشنهاد فعلی: {listing['current_bid']:,}\n"
        f"حداقل پیشنهاد قابل قبول: {min_next_bid:,.0f}\n\n"
        "مبلغ پیشنهادیت رو بفرست:"
    )
    await callback.answer()


@router.message(AuctionBidFlow.enter_amount)
async def submit_bid(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    amount = int(message.text)
    data = await state.get_data()

    if amount < data["min_next_bid"]:
        await message.answer(f"پیشنهاد باید حداقل {data['min_next_bid']:,.0f} باشه.")
        return

    if not await db.has_sufficient_balance(message.from_user.id, amount):
        await message.answer("❌ موجودی کیف پولت برای این پیشنهاد کافی نیست.")
        return

    success = await db.place_bid_atomic(data["listing_id"], message.from_user.id, amount)
    if not success:
        await message.answer("⚠️ یکی دیگه همین الان پیشنهاد بالاتری ثبت کرد! دوباره امتحان کن.")
        await state.clear()
        return

    listing = await db.get_listing(data["listing_id"])
    await message.answer(f"✅ پیشنهاد {amount:,} با موفقیت ثبت شد. فعلاً بالاترین پیشنهاد شمایید!")
    try:
        await message.bot.send_message(
            listing["seller_id"],
            f"📢 پیشنهاد جدید {amount:,} برای «{listing['title']}» ثبت شد.",
        )
    except Exception:
        pass
    await state.clear()


async def close_expired_auctions(bot):
    """
    این تابع باید به‌صورت دوره‌ای (مثلاً هر ۱ دقیقه) از یک scheduler صدا زده بشه
    تا مزایده‌های تموم‌شده رو ببنده و برنده رو مشخص کنه.
    """
    now = time.time()
    cursor = db.listings_col.find({
        "is_auction": True, "status": "active", "auction_end_at": {"$lte": now}
    })
    async for listing in cursor:
        await db.set_listing_status(listing["_id"], "pending")
        if listing.get("current_bidder"):
            try:
                await bot.send_message(
                    listing["current_bidder"],
                    f"🏆 تبریک! شما برنده مزایده «{listing['title']}» شدید با پیشنهاد "
                    f"{listing['current_bid']:,}. برای تسویه به بخش خرید مراجعه کن.",
                )
                await bot.send_message(
                    listing["seller_id"],
                    f"🔔 مزایده «{listing['title']}» تموم شد و یه برنده داره.",
                )
            except Exception:
                pass
        else:
            await db.set_listing_status(listing["_id"], "active")  # هیچ پیشنهادی نیومد، دوباره فعال بمونه
