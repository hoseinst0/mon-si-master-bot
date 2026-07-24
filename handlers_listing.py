"""
handlers_listing.py
ثبت آگهی فروش (شامل Account Health Check برای ساخت کارت پروفایل امتیازدار)
و جستجو/فیلتر هوشمند لیستینگ‌ها
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from states import ListingForm
from keyboards import rank_select_kb, yes_no_kb, listing_actions_kb, filter_menu_kb, listing_confirm_kb
from config import ACCOUNT_RANKS, TRUST_SCORE_MIN_TO_SELL, AUCTION_MIN_DURATION_MINUTES, AUCTION_MAX_DURATION_MINUTES
import time

router = Router(name="listing")


def calculate_account_score(rank: str, legendary_skins: int, mythic_items: int, battle_pass_level: int) -> int:
    """
    محاسبه امتیاز اکانت بر اساس اطلاعات ثبت‌شده توسط فروشنده.
    این امتیاز روی کارت پروفایل نمایش داده میشه و به خریدار کمک می‌کنه
    ارزش واقعی اکانت رو سریع بفهمه.
    """
    rank_weight = (ACCOUNT_RANKS.index(rank) + 1) * 10 if rank in ACCOUNT_RANKS else 0
    score = rank_weight + (legendary_skins * 3) + (mythic_items * 8) + (battle_pass_level // 10)
    return min(score, 999)


def suggest_price(account_score: int) -> tuple[int, int]:
    """پیشنهاد رنج قیمت بر اساس امتیاز اکانت (Smart Listing)."""
    base = account_score * 1000  # واحد فرضی: تومان یا Zen، قابل تنظیم
    return int(base * 0.85), int(base * 1.15)


# ---------------- شروع ثبت آگهی ----------------
@router.callback_query(F.data == "new_listing")
async def start_listing(callback: CallbackQuery, state: FSMContext):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    if user["trust_score"] < TRUST_SCORE_MIN_TO_SELL:
        await callback.message.answer(
            "⛔️ امتیاز اعتماد شما پایین‌تر از حد مجاز برای فروشه. "
            "لطفاً ابتدا با پشتیبانی تماس بگیر."
        )
        await callback.answer()
        return
    await state.set_state(ListingForm.title)
    await callback.message.answer("📝 یک عنوان کوتاه برای آگهی بفرست (مثال: اکانت Mythic فول اسکین):")
    await callback.answer()


@router.message(ListingForm.title)
async def listing_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(ListingForm.rank)
    await message.answer("🎖 رنک بازی اکانت رو انتخاب کن:", reply_markup=rank_select_kb())


@router.callback_query(ListingForm.rank, F.data.startswith("rank_"))
async def listing_rank(callback: CallbackQuery, state: FSMContext):
    rank = callback.data.split("rank_", 1)[1]
    await state.update_data(rank=rank)
    await state.set_state(ListingForm.legendary_skins)
    await callback.message.answer("✨ تعداد اسکین‌های Legendary اکانت رو به عدد بفرست:")
    await callback.answer()


@router.message(ListingForm.legendary_skins)
async def listing_legendary(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    await state.update_data(legendary_skins=int(message.text))
    await state.set_state(ListingForm.mythic_items)
    await message.answer("🔥 تعداد آیتم‌های Mythic رو بفرست:")


@router.message(ListingForm.mythic_items)
async def listing_mythic(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    await state.update_data(mythic_items=int(message.text))
    await state.set_state(ListingForm.battle_pass_level)
    await message.answer("📈 بالاترین سطح Battle Pass که رد کردی رو بفرست:")


@router.message(ListingForm.battle_pass_level)
async def listing_bp(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    data = await state.update_data(battle_pass_level=int(message.text))

    score = calculate_account_score(
        data["rank"], data["legendary_skins"], data["mythic_items"], data["battle_pass_level"]
    )
    low, high = suggest_price(score)
    await state.update_data(account_score=score)

    await state.set_state(ListingForm.price)
    await message.answer(
        f"📊 <b>امتیاز اکانت شما: {score}/999</b>\n"
        f"💡 رنج قیمت پیشنهادی بر اساس آمار اکانت‌های مشابه: "
        f"<b>{low:,} تا {high:,}</b>\n\n"
        "حالا قیمت نهایی مدنظرت رو به عدد بفرست:",
        parse_mode="HTML",
    )


@router.message(ListingForm.price)
async def listing_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(ListingForm.screenshots)
    await message.answer(
        "📸 حالا حداقل ۱ اسکرین‌شات یا ویدیو کوتاه از پروفایل اکانت بفرست "
        "(برای دریافت بج ✅ تأیید‌شده). وقتی تموم شد بنویس «تمام»."
    )


@router.message(ListingForm.screenshots, F.photo | F.video)
async def listing_collect_media(message: Message, state: FSMContext):
    data = await state.get_data()
    shots = data.get("screenshots", [])
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    shots.append(file_id)
    await state.update_data(screenshots=shots)
    await message.answer(f"✅ دریافت شد ({len(shots)} فایل). فایل بیشتری داری یا بنویس «تمام».")


@router.message(ListingForm.screenshots, F.text == "تمام")
async def listing_media_done(message: Message, state: FSMContext):
    data = await state.get_data()
    verified = len(data.get("screenshots", [])) > 0
    await state.update_data(verified=verified)
    await state.set_state(ListingForm.auction_choice)
    await message.answer(
        "🏛 آیا می‌خوای این اکانت به‌صورت مزایده (Auction) گذاشته بشه؟",
        reply_markup=yes_no_kb("auction_yes", "auction_no"),
    )


@router.callback_query(ListingForm.auction_choice, F.data == "auction_no")
async def listing_no_auction(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_auction=False)
    await show_listing_confirmation(callback.message, state)
    await callback.answer()


@router.callback_query(ListingForm.auction_choice, F.data == "auction_yes")
async def listing_yes_auction(callback: CallbackQuery, state: FSMContext):
    await state.update_data(is_auction=True)
    await state.set_state(ListingForm.auction_duration)
    await callback.message.answer(
        f"⏱ مدت مزایده رو به دقیقه بفرست (بین {AUCTION_MIN_DURATION_MINUTES} تا {AUCTION_MAX_DURATION_MINUTES}):"
    )
    await callback.answer()


@router.message(ListingForm.auction_duration)
async def listing_auction_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    minutes = int(message.text)
    if not (AUCTION_MIN_DURATION_MINUTES <= minutes <= AUCTION_MAX_DURATION_MINUTES):
        await message.answer(
            f"مدت باید بین {AUCTION_MIN_DURATION_MINUTES} تا {AUCTION_MAX_DURATION_MINUTES} دقیقه باشه."
        )
        return
    await state.update_data(auction_end_at=time.time() + minutes * 60)
    await show_listing_confirmation(message, state)


async def show_listing_confirmation(message: Message, state: FSMContext):
    """قبل از ثبت نهایی، خلاصهٔ کامل آگهی رو نشون میده و منتظر تأیید فروشنده می‌مونه."""
    data = await state.get_data()
    await state.set_state(ListingForm.confirm)

    mode = "🏛 مزایده‌ای" if data.get("is_auction") else "💵 قیمت ثابت"
    media_count = len(data.get("screenshots", []))
    media_label = f"✅ {media_count} فایل ({'تأیید‌شده' if media_count else 'بدون رسانه'})"

    summary = (
        "📋 <b>پیش‌نمایش آگهی — لطفاً قبل از ثبت نهایی بررسی کن:</b>\n\n"
        f"📝 عنوان: {data.get('title')}\n"
        f"🎖 رنک: {data.get('rank')}\n"
        f"✨ اسکین Legendary: {data.get('legendary_skins')}\n"
        f"🔥 آیتم Mythic: {data.get('mythic_items')}\n"
        f"📈 سطح Battle Pass: {data.get('battle_pass_level')}\n"
        f"📊 امتیاز اکانت: {data.get('account_score')}/999\n"
        f"💰 قیمت: {data.get('price'):,}\n"
        f"📸 مدیا: {media_label}\n"
        f"⚙️ نوع فروش: {mode}\n\n"
        "همه چیز درسته؟"
    )
    await message.answer(summary, reply_markup=listing_confirm_kb(), parse_mode="HTML")


@router.callback_query(ListingForm.confirm, F.data == "listing_confirm_yes")
async def listing_confirm_yes(callback: CallbackQuery, state: FSMContext):
    await finalize_listing(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(ListingForm.confirm, F.data == "listing_confirm_no")
async def listing_confirm_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ آگهی لغو شد. هر وقت خواستی از منو دوباره شروع کن.")
    await callback.answer()


async def finalize_listing(message: Message, state: FSMContext, seller_id: int):
    data = await state.get_data()
    listing_id = await db.create_listing(seller_id, data)
    badge = "✅ تأیید شده" if data.get("verified") else "⚠️ تأیید نشده"
    mode = "🏛 مزایده‌ای" if data.get("is_auction") else "💵 قیمت ثابت"
    await message.answer(
        f"🎉 <b>آگهی با موفقیت ثبت شد!</b>\n\n"
        f"🆔 کد آگهی: <code>{listing_id}</code>\n"
        f"📊 امتیاز اکانت: {data.get('account_score')}\n"
        f"{badge} | {mode}\n"
        f"💰 قیمت: {data.get('price'):,}\n\n"
        "آگهی شما در بخش جستجو برای خریدارها قابل مشاهده‌ست.",
        parse_mode="HTML",
    )
    await state.clear()


# ---------------- جستجو / فیلتر ----------------
@router.callback_query(F.data == "browse_listings")
async def browse_listings(callback: CallbackQuery):
    await callback.message.answer("🔎 چطور می‌خوای جستجو کنی؟", reply_markup=filter_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "filter_all")
async def filter_all(callback: CallbackQuery):
    results = await db.search_listings({})
    await render_listings(callback.message, results)
    await callback.answer()


@router.callback_query(F.data == "filter_verified")
async def filter_verified(callback: CallbackQuery):
    results = await db.search_listings({"verified_only": True})
    await render_listings(callback.message, results)
    await callback.answer()


@router.callback_query(F.data == "filter_rank")
async def filter_rank_prompt(callback: CallbackQuery):
    await callback.message.answer("🎖 رنک مدنظرت رو انتخاب کن:", reply_markup=rank_select_kb())
    await callback.answer()


async def render_listings(message: Message, results: list):
    if not results:
        await message.answer("چیزی با این فیلتر پیدا نشد.")
        return
    for listing in results:
        badge = "✅" if listing.get("verified") else "⚠️"
        mode = "🏛 مزایده" if listing.get("is_auction") else "💵 ثابت"
        price_label = f"پیشنهاد فعلی: {listing.get('current_bid'):,}" if listing.get("is_auction") else f"قیمت: {listing.get('price'):,}"
        text = (
            f"{badge} <b>{listing['title']}</b>\n"
            f"رنک: {listing['rank']} | امتیاز: {listing.get('account_score')} | {mode}\n"
            f"{price_label}"
        )
        await message.answer(
            text,
            reply_markup=listing_actions_kb(listing["_id"], listing.get("is_auction", False)),
            parse_mode="HTML",
        )
