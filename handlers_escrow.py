"""
handlers_escrow.py
فرآیند خرید: انتخاب بیمه -> قفل شدن پول در Vault -> نمایش شمارش معکوس عمومی
-> تأیید تحویل توسط خریدار -> آزادسازی پول به فروشنده + پرداخت کمیسیون رفرال
"""
import time
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from states import DisputeFlow
from keyboards import insurance_choice_kb, escrow_actions_kb, admin_dispute_kb
from config import (
    PLATFORM_FEE_PERCENT, VIP_FEE_PERCENT, INSURANCE_FEE_PERCENT,
    ESCROW_DEFAULT_MINUTES, PUBLIC_ESCROW_CHANNEL_ID, REFERRAL_COMMISSION_PERCENT,
    ADMIN_IDS,
)

router = Router(name="escrow")


@router.callback_query(F.data.startswith("buy_"))
async def start_buy(callback: CallbackQuery):
    listing_id = callback.data.split("buy_", 1)[1]
    listing = await db.get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await callback.answer("این آگهی دیگه در دسترس نیست.", show_alert=True)
        return
    if listing["seller_id"] == callback.from_user.id:
        await callback.answer("نمی‌تونی اکانت خودتو بخری!", show_alert=True)
        return

    await callback.message.answer(
        f"💰 قیمت این اکانت: <b>{listing['price']:,}</b>\n\n"
        f"🛡 با پرداخت {INSURANCE_FEE_PERCENT}٪ اضافه، تا {24} ساعت بعد از تحویل "
        "در صورت بروز مشکل (تغییر پسورد و غیره) کل مبلغ برمی‌گرده. مایلی بیمه کنی؟",
        reply_markup=insurance_choice_kb(listing_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("insure_yes_") | F.data.startswith("insure_no_"))
async def choose_insurance(callback: CallbackQuery):
    insured = callback.data.startswith("insure_yes_")
    listing_id = callback.data.split("_", 2)[2]
    listing = await db.get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await callback.answer("این آگهی دیگه در دسترس نیست.", show_alert=True)
        return

    base_price = listing["price"]
    total = base_price * (1 + INSURANCE_FEE_PERCENT / 100) if insured else base_price

    if not await db.has_sufficient_balance(callback.from_user.id, total):
        await callback.message.answer(
            f"❌ موجودی کافی نیست. مبلغ لازم: {total:,.0f}. لطفاً ابتدا کیف پولتو شارژ کن."
        )
        await callback.answer()
        return

    # کسر از موجودی خریدار و قفل کردن در Vault
    await db.adjust_balance(callback.from_user.id, -total)
    await db.set_listing_status(listing_id, "pending")

    countdown_end = time.time() + ESCROW_DEFAULT_MINUTES * 60
    tx_id = await db.create_escrow(
        listing_id, callback.from_user.id, listing["seller_id"], total, countdown_end, insured
    )

    await callback.message.answer(
        f"🔒 <b>پول شما در کیف امانی (Vault) قفل شد.</b>\n\n"
        f"کد پیگیری معامله: <code>{tx_id}</code>\n"
        f"فروشنده باید تا {ESCROW_DEFAULT_MINUTES} دقیقه دیگه اکانت رو تحویل بده.\n"
        "وقتی اطلاعات ورود اکانت رو از فروشنده گرفتی و بررسی کردی، دکمه تأیید رو بزن.",
        reply_markup=escrow_actions_kb(tx_id, for_buyer=True),
        parse_mode="HTML",
    )

    # اطلاع به فروشنده
    try:
        await callback.bot.send_message(
            listing["seller_id"],
            f"🛎 خریدار برای آگهی «{listing['title']}» پول رو قفل کرد.\n"
            f"کد معامله: <code>{tx_id}</code>\n"
            "لطفاً اطلاعات ورود اکانت رو مستقیم برای خریدار ارسال کن.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # پیام شفافیت عمومی در چنل (در صورت تنظیم بودن)
    if PUBLIC_ESCROW_CHANNEL_ID:
        try:
            await callback.bot.send_message(
                PUBLIC_ESCROW_CHANNEL_ID,
                f"⏳ یک معامله جدید شروع شد و در حال انتقاله (کد: {tx_id[:4]}***). "
                f"مهلت: {ESCROW_DEFAULT_MINUTES} دقیقه.",
            )
        except Exception:
            pass

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delivery_"))
async def confirm_delivery(callback: CallbackQuery):
    tx_id = callback.data.split("confirm_delivery_", 1)[1]
    tx = await db.get_escrow(tx_id)
    if not tx or tx["status"] != "locked":
        await callback.answer("این تراکنش قابل تأیید نیست.", show_alert=True)
        return
    if tx["buyer_id"] != callback.from_user.id:
        await callback.answer("فقط خریدار می‌تونه این معامله رو تأیید کنه.", show_alert=True)
        return

    is_vip_seller = await db.is_vip(tx["seller_id"])
    fee_percent = VIP_FEE_PERCENT if is_vip_seller else PLATFORM_FEE_PERCENT
    fee_amount = tx["amount"] * fee_percent / 100
    seller_gets = tx["amount"] - fee_amount

    await db.adjust_balance(tx["seller_id"], seller_gets)
    await db.update_escrow_status(tx_id, "released", delivered_at=time.time())
    await db.set_listing_status(tx["listing_id"], "sold")

    # آپدیت trust score هر دو طرف
    from config import TRUST_SCORE_SUCCESS_DELTA
    await db.update_trust_score(tx["seller_id"], TRUST_SCORE_SUCCESS_DELTA)
    await db.update_trust_score(tx["buyer_id"], TRUST_SCORE_SUCCESS_DELTA)

    # کمیسیون رفرال از کارمزد پلتفرم
    referral_commission = fee_amount * REFERRAL_COMMISSION_PERCENT / 100
    await db.pay_referral_commission(tx["seller_id"], referral_commission)

    await callback.message.answer(
        "✅ <b>معامله با موفقیت تکمیل شد!</b>\n"
        f"مبلغ به فروشنده واریز شد (پس از کسر {fee_percent}٪ کارمزد).\n"
        "امتیاز اعتماد هر دو طرف افزایش یافت. ممنون بابت استفاده از مارکت 🎮",
        parse_mode="HTML",
    )
    try:
        await callback.bot.send_message(
            tx["seller_id"],
            f"💸 مبلغ {seller_gets:,.0f} به کیف پول شما واریز شد. معامله {tx_id} تکمیل شد.",
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("dispute_"))
async def start_dispute(callback: CallbackQuery, state: FSMContext):
    tx_id = callback.data.split("dispute_", 1)[1]
    tx = await db.get_escrow(tx_id)
    if not tx or tx["status"] not in ("locked",):
        await callback.answer("امکان باز کردن اختلاف برای این تراکنش نیست.", show_alert=True)
        return
    await state.update_data(tx_id=tx_id)
    await state.set_state(DisputeFlow.enter_reason)
    await callback.message.answer("⚠️ مشکل رو دقیق توضیح بده (متن کوتاه):")
    await callback.answer()


@router.message(DisputeFlow.enter_reason)
async def dispute_reason(message: Message, state: FSMContext):
    data = await state.update_data(reason=message.text)
    dispute_id = await db.open_dispute(data["tx_id"], message.from_user.id, data["reason"])
    await state.update_data(dispute_id=dispute_id)
    await state.set_state(DisputeFlow.upload_evidence)
    await message.answer(
        "📎 حالا مدارک (اسکرین‌شات چت، خطا و غیره) رو بفرست. وقتی تموم شد بنویس «تمام»."
    )


@router.message(DisputeFlow.upload_evidence, F.photo | F.document)
async def dispute_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    tx = await db.get_escrow(data["tx_id"])
    side = "buyer" if message.from_user.id == tx["buyer_id"] else "seller"
    await db.add_dispute_evidence(data["dispute_id"], side, file_id)
    await message.answer("✅ مدرک دریافت شد. مورد دیگه‌ای هست؟ یا بنویس «تمام».")


@router.message(DisputeFlow.upload_evidence, F.text == "تمام")
async def dispute_done(message: Message, state: FSMContext):
    data = await state.get_data()
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"🚨 اختلاف جدید ثبت شد.\n"
                f"کد اختلاف: <code>{data['dispute_id']}</code>\n"
                f"کد تراکنش: <code>{data['tx_id']}</code>\n"
                f"دلیل: {data['reason']}",
                reply_markup=admin_dispute_kb(data["dispute_id"]),
                parse_mode="HTML",
            )
        except Exception:
            pass
    await message.answer("📨 پرونده اختلاف برای تیم پشتیبانی ارسال شد. منتظر بررسی باش.")
    await state.clear()
