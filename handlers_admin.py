"""
handlers_admin.py
پنل ادمین برای رسیدگی به اختلاف‌ها (Dispute Resolution)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from config import ADMIN_IDS, TRUST_SCORE_COMPLAINT_DELTA, TRUST_SCORE_SCAM_CONFIRMED_DELTA

router = Router(name="admin")


@router.callback_query(F.data.startswith("resolve_buyer_") | F.data.startswith("resolve_seller_"))
async def resolve_dispute(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("فقط ادمین‌ها دسترسی دارن.", show_alert=True)
        return

    favor_buyer = callback.data.startswith("resolve_buyer_")
    dispute_id = callback.data.split("_", 2)[2]

    dispute = await db.disputes_col.find_one({"_id": dispute_id})
    if not dispute:
        await callback.answer("پرونده پیدا نشد.", show_alert=True)
        return

    tx = await db.get_escrow(dispute["tx_id"])
    if not tx:
        await callback.answer("تراکنش مرتبط پیدا نشد.", show_alert=True)
        return

    if favor_buyer:
        # برگشت کامل پول به خریدار + جریمه اعتماد فروشنده
        await db.adjust_balance(tx["buyer_id"], tx["amount"])
        await db.update_trust_score(tx["seller_id"], TRUST_SCORE_SCAM_CONFIRMED_DELTA)
        await db.update_escrow_status(dispute["tx_id"], "refunded")
        result_text = "💸 پول به خریدار برگردونده شد و امتیاز فروشنده جریمه شد."
    else:
        # آزاد شدن پول به فروشنده + جریمه اعتماد خریدار (شکایت بی‌اساس)
        await db.adjust_balance(tx["seller_id"], tx["amount"])
        await db.update_trust_score(tx["buyer_id"], TRUST_SCORE_COMPLAINT_DELTA)
        await db.update_escrow_status(dispute["tx_id"], "released")
        result_text = "✅ پول به فروشنده آزاد شد و امتیاز خریدار (شکایت بی‌اساس) کم شد."

    await db.resolve_dispute(dispute_id, "resolved_buyer" if favor_buyer else "resolved_seller")

    await callback.message.edit_text(f"{callback.message.text}\n\n🔒 نتیجه: {result_text}")

    for uid in (tx["buyer_id"], tx["seller_id"]):
        try:
            await callback.bot.send_message(uid, f"📋 نتیجه بررسی اختلاف شما:\n{result_text}")
        except Exception:
            pass

    await callback.answer("ثبت شد.")
