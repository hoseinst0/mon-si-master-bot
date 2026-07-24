"""
handlers_admin_panel.py
پنل مدیریت خفن داخل خود ربات: آمار زنده، مدیریت کاربران، مدیریت آگهی‌ها،
پیام همگانی (Broadcast)، مشاهده اختلافات باز و تراکنش‌های اخیر.
فقط برای ADMIN_IDS قابل دسترسیه.
"""
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
from config import ADMIN_IDS, BROADCAST_DELAY_SECONDS, RECENT_ITEMS_LIMIT

router = Router(name="admin_panel")


class AdminPanelFlow(StatesGroup):
    search_user = State()
    set_balance_amount = State()
    broadcast_message = State()
    remove_listing_id = State()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 آمار زنده", callback_data="ap_stats")
    kb.button(text="👥 جستجوی کاربر", callback_data="ap_search_user")
    kb.button(text="📦 آخرین آگهی‌ها", callback_data="ap_listings")
    kb.button(text="💬 اختلافات باز", callback_data="ap_disputes")
    kb.button(text="💳 تراکنش‌های اخیر", callback_data="ap_transactions")
    kb.button(text="📢 پیام همگانی", callback_data="ap_broadcast")
    kb.adjust(2)
    return kb.as_markup()


@router.message(Command("admin"))
async def open_admin_panel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>پنل مدیریت مارکت اکانت CoD Mobile</b>\n\nیکی از بخش‌ها رو انتخاب کن:",
        reply_markup=admin_panel_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ap_back")
async def ap_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.message.edit_text(
        "🛠 <b>پنل مدیریت مارکت اکانت CoD Mobile</b>\n\nیکی از بخش‌ها رو انتخاب کن:",
        reply_markup=admin_panel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


def _back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ بازگشت به پنل", callback_data="ap_back")
    return kb.as_markup()


# ---------------- آمار زنده ----------------
@router.callback_query(F.data == "ap_stats")
async def ap_stats(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    s = await db.get_dashboard_stats()
    text = (
        "📊 <b>آمار زنده مارکت</b>\n\n"
        f"👥 کاربران: {s['total_users']} (بن‌شده: {s['banned_users']} | VIP: {s['vip_users']})\n\n"
        f"📦 آگهی‌ها: {s['total_listings']} کل\n"
        f"   ├ فعال: {s['active_listings']}\n"
        f"   ├ فروخته‌شده: {s['sold_listings']}\n"
        f"   └ مزایده فعال: {s['auction_listings']}\n\n"
        f"🔒 تراکنش‌ها:\n"
        f"   ├ در حال قفل (Vault): {s['locked_tx']}\n"
        f"   ├ آزادشده: {s['released_tx']}\n"
        f"   ├ در حال اختلاف: {s['disputed_tx']}\n"
        f"   └ ریفاندشده: {s['refunded_tx']}\n\n"
        f"⚠️ اختلافات باز: {s['open_disputes']}\n\n"
        f"💰 حجم کل معاملات موفق: <b>{s['total_volume']:,.0f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_back_kb(), parse_mode="HTML")
    await callback.answer()


# ---------------- جستجوی کاربر ----------------
@router.callback_query(F.data == "ap_search_user")
async def ap_search_user_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminPanelFlow.search_user)
    await callback.message.answer("🔍 آیدی عددی یا بخشی از یوزرنیم کاربر رو بفرست:")
    await callback.answer()


@router.message(AdminPanelFlow.search_user)
async def ap_search_user_result(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    user = await db.search_user(message.text.strip())
    if not user:
        await message.answer("کاربری پیدا نشد.")
        await state.clear()
        return

    kb = InlineKeyboardBuilder()
    if user.get("banned"):
        kb.button(text="✅ آنبن کن", callback_data=f"ap_unban_{user['_id']}")
    else:
        kb.button(text="🚫 بن کن", callback_data=f"ap_ban_{user['_id']}")
    kb.button(text="💰 تغییر موجودی", callback_data=f"ap_setbal_{user['_id']}")
    kb.adjust(1)

    await message.answer(
        f"👤 <b>پروفایل کاربر</b>\n\n"
        f"آیدی: <code>{user['_id']}</code>\n"
        f"یوزرنیم: @{user.get('username') or '-'}\n"
        f"موجودی: {user.get('balance', 0):,.0f}\n"
        f"امتیاز اعتماد: {user.get('trust_score')}\n"
        f"VIP: {user.get('vip_tier') or 'ندارد'}\n"
        f"وضعیت: {'🚫 بن‌شده' if user.get('banned') else '✅ فعال'}\n"
        f"تعداد فروش موفق: {user.get('total_sales', 0)}\n"
        f"تعداد خرید موفق: {user.get('total_purchases', 0)}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data.startswith("ap_ban_") | F.data.startswith("ap_unban_"))
async def ap_toggle_ban(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    banning = callback.data.startswith("ap_ban_")
    user_id = int(callback.data.split("_")[-1])
    await db.set_user_banned(user_id, banning)
    await callback.message.answer(f"{'🚫 کاربر بن شد.' if banning else '✅ کاربر آنبن شد.'}")
    try:
        await callback.bot.send_message(
            user_id,
            "🚫 حساب شما توسط مدیریت مسدود شد." if banning else "✅ حساب شما دوباره فعال شد.",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ap_setbal_"))
async def ap_set_balance_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    user_id = int(callback.data.split("ap_setbal_", 1)[1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminPanelFlow.set_balance_amount)
    await callback.message.answer("💰 مقدار جدید موجودی رو به عدد بفرست:")
    await callback.answer()


@router.message(AdminPanelFlow.set_balance_amount)
async def ap_set_balance_apply(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    if not message.text.replace(".", "", 1).isdigit():
        await message.answer("لطفاً فقط عدد بفرست.")
        return
    data = await state.get_data()
    await db.set_user_balance(data["target_user_id"], float(message.text))
    await message.answer("✅ موجودی به‌روزرسانی شد.")
    await state.clear()


# ---------------- آخرین آگهی‌ها ----------------
@router.callback_query(F.data == "ap_listings")
async def ap_listings(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    listings = await db.get_recent_listings(RECENT_ITEMS_LIMIT)
    if not listings:
        await callback.message.answer("آگهی‌ای ثبت نشده.")
        await callback.answer()
        return
    for l in listings:
        kb = InlineKeyboardBuilder()
        if l["status"] == "active":
            kb.button(text="🗑 حذف آگهی", callback_data=f"ap_removelisting_{l['_id']}")
        await callback.message.answer(
            f"🆔 <code>{l['_id']}</code> | {l['title']}\n"
            f"وضعیت: {l['status']} | قیمت: {l.get('price'):,}\n"
            f"فروشنده: <code>{l['seller_id']}</code>",
            reply_markup=kb.as_markup() if l["status"] == "active" else None,
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ap_removelisting_"))
async def ap_remove_listing(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    listing_id = callback.data.split("ap_removelisting_", 1)[1]
    await db.force_remove_listing(listing_id)
    await callback.message.answer(f"🗑 آگهی {listing_id} حذف شد.")
    await callback.answer()


# ---------------- اختلافات باز ----------------
@router.callback_query(F.data == "ap_disputes")
async def ap_disputes(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    disputes = await db.get_open_disputes(RECENT_ITEMS_LIMIT)
    if not disputes:
        await callback.message.answer("✅ هیچ اختلاف بازی وجود نداره.")
        await callback.answer()
        return
    from keyboards import admin_dispute_kb
    for d in disputes:
        await callback.message.answer(
            f"⚠️ کد اختلاف: <code>{d['_id']}</code>\n"
            f"تراکنش: <code>{d['tx_id']}</code>\n"
            f"دلیل: {d['reason']}",
            reply_markup=admin_dispute_kb(d["_id"]),
            parse_mode="HTML",
        )
    await callback.answer()


# ---------------- تراکنش‌های اخیر ----------------
@router.callback_query(F.data == "ap_transactions")
async def ap_transactions(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    txs = await db.get_recent_transactions(RECENT_ITEMS_LIMIT)
    if not txs:
        await callback.message.answer("تراکنشی ثبت نشده.")
        await callback.answer()
        return
    lines = ["💳 <b>آخرین تراکنش‌ها</b>\n"]
    status_emoji = {"locked": "🔒", "released": "✅", "disputed": "⚠️", "refunded": "↩️"}
    for tx in txs:
        lines.append(
            f"{status_emoji.get(tx['status'], '•')} <code>{tx['_id']}</code> — "
            f"{tx['amount']:,.0f} ({tx['status']})"
        )
    await callback.message.answer("\n".join(lines), reply_markup=_back_kb(), parse_mode="HTML")
    await callback.answer()


# ---------------- پیام همگانی ----------------
@router.callback_query(F.data == "ap_broadcast")
async def ap_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminPanelFlow.broadcast_message)
    await callback.message.answer("📢 متن پیام همگانی رو بفرست (برای همه کاربرای غیربن‌شده ارسال میشه):")
    await callback.answer()


@router.message(AdminPanelFlow.broadcast_message)
async def ap_broadcast_send(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    user_ids = await db.get_all_active_user_ids()
    sent, failed = 0, 0
    status_msg = await message.answer(f"📤 در حال ارسال به {len(user_ids)} کاربر...")
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)
    await status_msg.edit_text(f"✅ ارسال تموم شد. موفق: {sent} | ناموفق: {failed}")
    await state.clear()
