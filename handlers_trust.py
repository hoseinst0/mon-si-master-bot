"""
handlers_trust.py
نمایش لیدربورد اعتماد (Trust Score)
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db

router = Router(name="trust")


@router.callback_query(F.data == "trust_leaderboard")
async def show_leaderboard(callback: CallbackQuery):
    cursor = db.users_col.find({"banned": False}).sort("trust_score", -1).limit(10)
    top_users = [doc async for doc in cursor]

    if not top_users:
        await callback.message.answer("هنوز کاربری ثبت نشده.")
        await callback.answer()
        return

    lines = ["🏆 <b>برترین‌های اعتماد مارکت</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_users):
        prefix = medals[i] if i < 3 else f"{i+1}."
        name = u.get("username") or f"کاربر {u['_id']}"
        lines.append(f"{prefix} @{name} — امتیاز: {u.get('trust_score')}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()
