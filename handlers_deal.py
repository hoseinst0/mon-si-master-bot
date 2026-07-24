"""
handlers_deal.py
فلوی محاوره‌ای معامله:
۱. شروع‌کننده نقشش (خریدار/فروشنده) + قیمت + توضیح رو تو چت می‌گه
۲. یه لینک دیپ‌لینک برای طرف مقابل ساخته می‌شه (چون Bot API نمی‌ذاره ربات اول
   پیام بده به کسی که قبلاً /start نزده)
۳. طرف مقابل با کلیک لینک، معامله رو می‌بینه و تأیید می‌کنه
۴. هر دو طرف یه مدرک (اسکرین‌شات) می‌فرستن -> برای ادمین‌ها ارسال می‌شه
۵. با تأیید ادمین برای هر دو طرف، یوزربات یه گروه خصوصی می‌سازه و لینک عضویت
   (کلیکی) برای هر دو نفر فرستاده می‌شه
"""
import asyncio
import io
import logging

from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from states import DealFlow
from keyboards import (
    deal_role_kb, deal_confirm_kb, deal_admin_review_kb, deal_join_group_kb,
    kyc_request_kb, admin_kyc_review_kb,
)
from config import ADMIN_IDS, KYC_REQUIRED_ABOVE, RECEIPT_OCR_ENABLED

router = Router(name="deal")

ROLE_FA = {"buyer": "خریدار", "seller": "فروشنده"}


def _extract_amount_from_bytes(image_bytes: bytes):
    """
    تلاش می‌کنه با OCR مبلغ رو از عکس رسید تشخیص بده (بزرگ‌ترین عدد معقول تو متن).
    نیازمند pytesseract + Pillow (pip) و باینری سیستمی tesseract-ocr هست.
    اگه هرکدوم نصب نباشن یا هر خطای دیگه‌ای پیش بیاد، None برمی‌گردونه بدون کرش کردن ربات.
    """
    if not RECEIPT_OCR_ENABLED:
        return None
    try:
        import re
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang="fas+eng")

        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        text = text.translate({ord(d): str(i) for i, d in enumerate(persian_digits)})

        candidates = re.findall(r"\d[\d,.\s]{3,}\d", text)
        best = None
        for c in candidates:
            cleaned = re.sub(r"[^\d]", "", c)
            if not cleaned:
                continue
            value = int(cleaned)
            if 1_000 <= value <= 10_000_000_000 and (best is None or value > best):
                best = value
        return best
    except Exception:
        logging.exception("تشخیص خودکار مبلغ از رسید (OCR) ناموفق بود")
        return None


# ---------------- شروع معامله توسط شروع‌کننده ----------------
@router.callback_query(F.data == "start_new_deal")
async def start_new_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealFlow.choose_role)
    await callback.message.edit_text(
        "🤝 <b>شروع معامله جدید</b>\n\nنقش شما تو این معامله چیه؟",
        reply_markup=deal_role_kb(),
    )
    await callback.answer()


@router.callback_query(DealFlow.choose_role, F.data.in_({"deal_role_buyer", "deal_role_seller"}))
async def choose_role(callback: CallbackQuery, state: FSMContext):
    role = "buyer" if callback.data == "deal_role_buyer" else "seller"
    await state.update_data(role=role)
    await state.set_state(DealFlow.enter_price)
    await callback.message.edit_text("💵 قیمت توافقی معامله رو به تومان بفرست (فقط عدد):")
    await callback.answer()


@router.message(DealFlow.enter_price)
async def enter_price(message: Message, state: FSMContext):
    raw = message.text.strip().replace(",", "").replace("،", "")
    if not raw.isdigit():
        await message.answer("❗️ لطفاً فقط عدد بفرست، مثلاً: 500000")
        return
    price = int(raw)

    # گیت احراز هویت برای معاملات بالای سقف مشخص
    if price >= KYC_REQUIRED_ABOVE and not await db.is_kyc_verified(message.from_user.id):
        await state.clear()
        await message.answer(
            f"⚠️ برای معاملات بالای <b>{KYC_REQUIRED_ABOVE:,}</b> تومان، ابتدا باید احراز هویت بشی.\n\n"
            "روی دکمه زیر بزن تا درخواستت برای ادمین ارسال بشه. بعد از تأیید، "
            "لطفاً معامله رو دوباره از اول شروع کن.",
            reply_markup=kyc_request_kb(),
        )
        return

    is_vip_user = await db.is_vip(message.from_user.id)
    fee_info = db.calculate_middleman_fee(price, is_vip_user)

    await state.update_data(
        price=price,
        fee_amount=fee_info["fee"],
        fee_tier_label=fee_info["tier_label"],
        fee_is_vip=is_vip_user,
    )
    await state.set_state(DealFlow.enter_description)
    await message.answer(
        f"💵 قیمت معامله: <b>{price:,}</b> تومان\n"
        f"💼 حق واسط (بازه {fee_info['tier_label']}"
        f"{' — نرخ VIP' if is_vip_user else ''}): <b>{fee_info['fee']:,.0f}</b> تومان\n"
        f"➕ جمع کل قابل پرداخت: <b>{fee_info['total']:,.0f}</b> تومان\n\n"
        "📝 یه توضیح کوتاه از اکانت/کالای مورد معامله بفرست:"
    )


@router.callback_query(F.data == "kyc_request")
async def kyc_request(callback: CallbackQuery):
    await db.mark_kyc_requested(callback.from_user.id)
    username = callback.from_user.username or "بدون یوزرنیم"
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                "🪪 درخواست احراز هویت جدید\n"
                f"کاربر: {callback.from_user.id} (@{username})\n"
                "بعد از بررسی، تأیید یا رد کن:",
                reply_markup=admin_kyc_review_kb(callback.from_user.id),
            )
        except Exception:
            pass
    await callback.message.edit_text("📨 درخواست احراز هویت برای ادمین ارسال شد. منتظر بررسی باش.")
    await callback.answer()


@router.message(DealFlow.enter_description)
async def enter_description(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    deal_id = await db.create_deal(
        initiator_id=message.from_user.id,
        initiator_username=message.from_user.username,
        initiator_role=data["role"],
        price=data["price"],
        description=message.text.strip(),
        fee_amount=data.get("fee_amount"),
        fee_tier_label=data.get("fee_tier_label"),
        fee_is_vip=data.get("fee_is_vip", False),
    )
    await state.clear()

    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=deal_{deal_id}"
    other_role_fa = "فروشنده" if data["role"] == "buyer" else "خریدار"

    await message.answer(
        "✅ معامله ثبت شد.\n\n"
        f"این لینک رو برای <b>{other_role_fa}</b> بفرست تا معامله رو تأیید کنه:\n\n"
        f"{link}\n\n"
        "به محض تأیید طرف مقابل بهت خبر می‌دم."
    )


# ---------------- ورود طرف مقابل با دیپ‌لینک ----------------
async def handle_deal_start(message: Message, bot: Bot, deal_id: str):
    """از handlers_start.py وقتی payload با deal_ شروع بشه صدا زده می‌شه."""
    deal = await db.get_deal(deal_id)
    if not deal:
        await message.answer("این لینک معامله معتبر نیست یا منقضی شده.")
        return

    if deal["initiator_id"] == message.from_user.id:
        await message.answer("این لینک معامله‌ی خودته؛ نمی‌تونی طرف مقابل خودت باشی.")
        return

    if deal.get("counterparty_id") and deal["counterparty_id"] != message.from_user.id:
        await message.answer("این معامله قبلاً توسط یه نفر دیگه باز شده.")
        return

    if not deal.get("counterparty_id"):
        counterparty_role = "seller" if deal["initiator_role"] == "buyer" else "buyer"
        await db.set_deal_counterparty(
            deal_id, message.from_user.id, message.from_user.username, counterparty_role
        )
        deal = await db.get_deal(deal_id)

    role_fa = ROLE_FA[deal["counterparty_role"]]
    fee_line = f"💼 حق واسط: <b>{deal['fee_amount']:,.0f}</b> تومان\n" if deal.get("fee_amount") else ""
    await message.answer(
        "📋 <b>جزئیات معامله</b>\n\n"
        f"نقش تو تو این معامله: <b>{role_fa}</b>\n"
        f"قیمت: <b>{deal['price']:,} تومان</b>\n"
        f"{fee_line}"
        f"توضیح: {deal['description']}\n\n"
        "اگه این معامله رو قبول داری، تأیید کن:",
        reply_markup=deal_confirm_kb(deal_id),
    )


# ---------------- تأیید/رد معامله توسط هر یک از طرفین ----------------
@router.callback_query(F.data.startswith("deal_cancel_"))
async def cancel_deal(callback: CallbackQuery):
    deal_id = callback.data.replace("deal_cancel_", "", 1)
    deal = await db.get_deal(deal_id)
    if not deal:
        await callback.answer("معامله پیدا نشد.", show_alert=True)
        return

    await db.set_deal_status(deal_id, "rejected")
    await callback.message.edit_text("❌ این معامله رد شد.")
    other_id = deal["initiator_id"] if callback.from_user.id == deal["counterparty_id"] else deal["counterparty_id"]
    if other_id:
        try:
            await callback.bot.send_message(other_id, "❌ طرف مقابل معامله رو رد کرد.")
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("deal_confirm_"))
async def confirm_deal(callback: CallbackQuery, state: FSMContext):
    deal_id = callback.data.replace("deal_confirm_", "", 1)
    deal = await db.get_deal(deal_id)
    if not deal:
        await callback.answer("معامله پیدا نشد.", show_alert=True)
        return

    if callback.from_user.id == deal["counterparty_id"]:
        await db.set_deal_confirmed(deal_id, "counterparty")
    elif callback.from_user.id == deal["initiator_id"]:
        await db.set_deal_confirmed(deal_id, "initiator")
    else:
        await callback.answer("این معامله مربوط به تو نیست.", show_alert=True)
        return

    await callback.message.edit_text("✅ تأیید شد. منتظر تأیید طرف مقابل هستیم...")
    await callback.answer()

    deal = await db.get_deal(deal_id)
    if deal["initiator_confirmed"] and deal["counterparty_confirmed"]:
        await db.set_deal_status(deal_id, "awaiting_proof")
        for uid in (deal["initiator_id"], deal["counterparty_id"]):
            try:
                await callback.bot.send_message(
                    uid,
                    "🪪 هر دو طرف معامله رو تأیید کردن.\n"
                    "برای احراز، لطفاً یه عکس/اسکرین‌شات مدرک "
                    "(مالکیت اکانت یا رسید واریز/توان پرداخت) بفرست:",
                )
            except Exception:
                pass


# ---------------- دریافت مدرک (عکس) از هر طرف ----------------
# StateFilter(None): فقط وقتی کاربر تو هیچ فرم/فلوی دیگه‌ای (مثل آپلود اسکرین‌شات
# آگهی یا مدرک اختلاف) نیست - تا با اون فلوها تداخل نکنه.
@router.message(StateFilter(None), F.photo)
async def receive_proof(message: Message, bot: Bot):
    deal = await db.find_active_deal_for_user(message.from_user.id)
    if not deal or deal["status"] not in ("awaiting_proof", "awaiting_admin"):
        return  # این عکس مربوط به فلوی معامله نیست (مثلاً یه چت دیگه)

    side = "initiator" if message.from_user.id == deal["initiator_id"] else "counterparty"
    side_role = deal["initiator_role"] if side == "initiator" else deal["counterparty_role"]
    file_id = message.photo[-1].file_id

    # تلاش برای تشخیص خودکار مبلغ از عکس رسید (OCR) - بدون بلاک کردن event loop
    detected_amount = None
    try:
        buf = io.BytesIO()
        await bot.download(message.photo[-1], destination=buf)
        detected_amount = await asyncio.to_thread(_extract_amount_from_bytes, buf.getvalue())
    except Exception:
        logging.exception("دانلود عکس رسید برای OCR ناموفق بود")

    await db.set_deal_proof(deal["_id"], side, file_id, detected_amount=detected_amount)

    if detected_amount:
        expected = deal["price"] + (deal.get("fee_amount") or 0)
        tolerance = max(expected * 0.02, 1000)
        match = abs(detected_amount - expected) <= tolerance
        status_line = f"🔎 مبلغ تشخیص‌داده‌شده از رسید: <b>{detected_amount:,}</b> تومان\n"
        status_line += (
            "✅ با مبلغ معامله هم‌خوانی داره."
            if match else
            f"⚠️ با مبلغ قابل‌پرداخت ({expected:,.0f} تومان) فرق داره — لطفاً دوباره چک کن."
        )
        await message.answer(f"📨 مدرکت برای بررسی ادمین ارسال شد.\n{status_line}")
    else:
        await message.answer("📨 مدرکت برای بررسی ادمین ارسال شد. لطفاً صبر کن.")

    username = message.from_user.username or "بدون یوزرنیم"
    caption = (
        f"🔍 مدرک معامله #{deal['_id']}\n"
        f"طرف: {ROLE_FA.get(side_role, side)}\n"
        f"کاربر: {message.from_user.id} (@{username})\n"
        f"قیمت: {deal['price']:,} تومان\n"
    )
    if deal.get("fee_amount"):
        caption += f"حق واسط: {deal['fee_amount']:,.0f} تومان\n"
    if detected_amount:
        caption += f"🔎 مبلغ تشخیص‌داده‌شده از رسید (OCR): {detected_amount:,} تومان\n"
    caption += f"توضیح: {deal['description']}"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                file_id,
                caption=caption,
                reply_markup=deal_admin_review_kb(deal["_id"], side),
            )
        except Exception:
            logging.exception("ارسال مدرک به ادمین ناموفق بود")


# ---------------- تصمیم ادمین روی مدرک ----------------
@router.callback_query(F.data.startswith("deal_admin_ok_") | F.data.startswith("deal_admin_no_"))
async def admin_review_proof(callback: CallbackQuery, bot: Bot):
    approved = callback.data.startswith("deal_admin_ok_")
    prefix = "deal_admin_ok_" if approved else "deal_admin_no_"
    rest = callback.data.replace(prefix, "", 1)
    deal_id, side = rest.rsplit("_", 1)

    deal = await db.get_deal(deal_id)
    if not deal:
        await callback.answer("معامله پیدا نشد.", show_alert=True)
        return

    if not approved:
        await db.set_deal_status(deal_id, "rejected")
        await callback.message.edit_caption(
            caption=(callback.message.caption or "") + "\n\n❌ رد شد توسط ادمین"
        )
        for uid in (deal["initiator_id"], deal["counterparty_id"]):
            if uid:
                try:
                    await bot.send_message(uid, "❌ مدرک ارسالی تأیید نشد، معامله لغو شد.")
                except Exception:
                    pass
        await callback.answer("رد شد")
        return

    await db.set_deal_admin_approval(deal_id, side, True)
    await callback.message.edit_caption(
        caption=(callback.message.caption or "") + "\n\n✅ تأیید شد توسط ادمین"
    )
    await callback.answer("تأیید شد")

    deal = await db.get_deal(deal_id)
    if deal["initiator_admin_approved"] and deal["counterparty_admin_approved"]:
        await _create_and_notify_group(deal, bot)


async def _create_and_notify_group(deal: dict, bot: Bot):
    import userbot  # ایمپورت دیر برای جلوگیری از وابستگی سخت اگه telethon نصب نباشه

    bot_username = (await bot.get_me()).username
    title = f"معامله #{deal['_id']}"

    try:
        result = await userbot.create_deal_group(title, bot_username)
    except Exception:
        logging.exception("ساخت گروه معامله ناموفق بود")
        for uid in (deal["initiator_id"], deal["counterparty_id"]):
            try:
                await bot.send_message(
                    uid, "⚠️ خطا در ساخت خودکار گروه؛ ادمین به‌زودی دستی هماهنگ می‌کنه."
                )
            except Exception:
                pass
        return

    await db.set_deal_group(deal["_id"], result["chat_id"], result["invite_link"])
    await db.set_deal_status(deal["_id"], "group_created")

    kb = deal_join_group_kb(result["invite_link"])
    for uid in (deal["initiator_id"], deal["counterparty_id"]):
        try:
            await bot.send_message(
                uid,
                "🎉 هر دو طرف تأیید شدن! گروه اختصاصی معامله ساخته شد.\n"
                "برای ورود روی دکمه زیر بزن:",
                reply_markup=kb,
            )
        except Exception:
            pass
