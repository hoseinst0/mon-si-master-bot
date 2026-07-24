"""
handlers_start.py
هندل /start، منوی اصلی و لینک‌های رفرال
"""
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import main_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    # اگه با دیپ‌لینک معامله اومده (deal_XXXXXXXX) -> کل کنترل رو بده به فلوی معامله
    if command.args and command.args.startswith("deal_"):
        deal_id = command.args.replace("deal_", "", 1)
        logging.info("DEBUG cmd_start: deal deep-link received, deal_id=%s from_user=%s", deal_id, message.from_user.id)
        try:
            import handlers_deal
            await db.get_or_create_user(message.from_user.id, message.from_user.username)
            await handlers_deal.handle_deal_start(message, message.bot, deal_id)
        except Exception:
            logging.exception("DEBUG cmd_start: خطا در پردازش لینک معامله deal_id=%s", deal_id)
            await message.answer(
                "⚠️ یه خطای غیرمنتظره پیش اومد. لطفاً دوباره تلاش کن یا با پشتیبانی تماس بگیر."
            )
        return

    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)

    # اگه با لینک رفرال اومده: /start REF_CODE
    if command.args and not user.get("referred_by"):
        linked = await db.link_referral(message.from_user.id, command.args.strip())
        if linked:
            await message.answer("🔗 حساب شما با یک لینک دعوت مرتبط شد. خوش اومدی!")

    text = (
        "🎮 <b>به مارکت اکانت CoD Mobile خوش اومدی</b>\n\n"
        "اینجا خرید و فروش اکانت با سیستم امانی (Escrow) و امتیاز اعتماد انجام میشه؛\n"
        "پول شما تا تأیید تحویل، امن نگه داشته میشه.\n\n"
        f"💰 موجودی فعلی شما: <b>{user.get('balance', 0)} {db.__name__ and 'Zen'}</b>\n"
        f"⭐️ امتیاز اعتماد شما: <b>{user.get('trust_score')}</b>"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 <b>منوی اصلی</b>\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "my_referral")
async def show_referral(callback: CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    bot_username = (await callback.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    await callback.message.answer(
        "🔗 <b>لینک دعوت اختصاصی شما</b>\n\n"
        f"{link}\n\n"
        "برای هر معامله موفقی که با این لینک انجام بشه، درصدی از کارمزد پلتفرم "
        "به‌صورت خودکار به کیف پول شما اضافه میشه.",
        parse_mode="HTML",
    )
    await callback.answer()
