"""
handlers_vip_antiscam.py
اشتراک VIP (کارمزد کمتر + لیست پین‌شده) و ابزار آنتی-اسکم فینگرپرینتینگ برای ادمین
"""
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_IDS, VIP_FEE_PERCENT

router = Router(name="vip_antiscam")

VIP_PLANS = {
    "vip_1m": {"label": "۱ ماهه", "days": 30, "price": 150000},
    "vip_3m": {"label": "۳ ماهه", "days": 90, "price": 400000},
}


@router.callback_query(F.data == "vip_menu")
async def vip_menu(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    for key, plan in VIP_PLANS.items():
        kb.button(text=f"{plan['label']} - {plan['price']:,}", callback_data=f"buy_{key}")
    kb.adjust(1)
    await callback.message.answer(
        f"👑 <b>اشتراک VIP</b>\n\n"
        f"مزایا: کارمزد پلتفرم از {VIP_FEE_PERCENT}٪ (به‌جای نرخ عادی)، "
        "پین شدن آگهی‌ها در بالای لیست، بج ویژه کنار اسمت.\n\n"
        "یکی از پلن‌ها رو انتخاب کن:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_vip_"))
async def buy_vip(callback: CallbackQuery):
    plan_key = callback.data.split("buy_", 1)[1]
    plan = VIP_PLANS.get(plan_key)
    if not plan:
        await callback.answer("پلن نامعتبر.", show_alert=True)
        return
    if not await db.has_sufficient_balance(callback.from_user.id, plan["price"]):
        await callback.message.answer("❌ موجودی کافی نیست.")
        await callback.answer()
        return

    await db.adjust_balance(callback.from_user.id, -plan["price"])
    expires_at = time.time() + plan["days"] * 86400
    await db.users_col.update_one(
        {"_id": callback.from_user.id},
        {"$set": {"vip_tier": plan_key, "vip_expires_at": expires_at}},
    )
    await callback.message.answer(f"🎉 اشتراک VIP {plan['label']} فعال شد!")
    await callback.answer()


# ---------------- ANTI-SCAM (فقط ادمین) ----------------
@router.message(Command("ban_fingerprint"))
async def ban_fingerprint_cmd(message: Message):
    """
    استفاده: /ban_fingerprint USER_ID FINGERPRINT دلیل...
    مثال: /ban_fingerprint 123456789 devhash_abc123 کلاهبرداری تایید شده
    این فینگرپرینت (که می‌تونه ترکیب device_id / IP / الگوی متنی آگهی باشه که
    از سمت وب‌اپ یا لاگ سرور جمع‌آوری شده) برای همیشه فلگ میشه؛ اگه بعداً
    یه آیدی جدید با همون الگو ثبت‌نام کنه، به ادمین هشدار داده میشه.
    """
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("فرمت درست: /ban_fingerprint USER_ID FINGERPRINT دلیل")
        return
    _, user_id_str, fingerprint, reason = parts
    await db.record_ban_fingerprint(int(user_id_str), fingerprint, reason)
    await message.answer(f"✅ کاربر {user_id_str} و فینگرپرینت مرتبط مسدود شد.")


async def check_fingerprint_on_registration(user_id: int, fingerprint: str, bot) -> bool:
    """
    این تابع رو موقع ثبت‌نام یا ثبت آگهی جدید صدا بزن. اگه فینگرپرینت
    قبلاً فلگ شده باشه، به همه ادمین‌ها هشدار میده و True برمی‌گردونه.
    """
    flagged = await db.is_fingerprint_flagged(fingerprint)
    if flagged:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ کاربر جدید {user_id} با فینگرپرینت مشکوک (قبلاً بلاک‌شده) ثبت‌نام کرد!",
                )
            except Exception:
                pass
    return flagged
