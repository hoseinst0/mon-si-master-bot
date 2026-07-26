# ============================================================
#  RAVENMORE ACADEMY RPG — Duel System (محوطه دوئل)
#  دوئل تمرینی و تکرارپذیر در کنار کوئست‌های اصلیِ داستانی
# ============================================================
import random
import time

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db
import utils

router = Router()

PRACTICE_OPPONENTS = ["دارکوس", "یک دانش‌آموز سال دوم", "یک دانش‌آموز سال سوم", "یکی از رقبای خانه‌ی مقابل"]
DUEL_COOLDOWN_SECONDS = 60 * 30  # نیم ساعت واقعی بین دوئل‌های تمرینی


def duel_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ درخواست دوئل تمرینی", callback_data="duel:start", style="success")
    return kb.as_markup()


@router.message(Command("duel"))
async def cmd_duel(message: Message):
    await message.answer(
        "🗡 محوطه دوئل ریون‌مور\n\n"
        "می‌توانی هر چند وقت یک‌بار برای تمرین دوئل بخواهی. "
        "بردن یعنی +۲ سکه و +۱ اعتبار؛ باختن یعنی -۱ روحیه.",
        reply_markup=duel_keyboard(),
    )


@router.callback_query(F.data == "duel:start")
async def cb_duel_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if not player or player.get("onboarding_step") != "done":
            await callback.answer("اول باید کاراکتر بسازی: /start", show_alert=True)
            return
        if player.get("mood", 0) <= 0:
            await callback.answer("روحیه‌ات صفر است، نمی‌توانی دوئل کنی!", show_alert=True)
            return

        now = time.time()
        last = player.get("last_duel_ts", 0)
        if now - last < DUEL_COOLDOWN_SECONDS:
            remain = int((DUEL_COOLDOWN_SECONDS - (now - last)) / 60) + 1
            await callback.answer(f"باید حدود {remain} دقیقه دیگر صبر کنی.", show_alert=True)
            return
        player["last_duel_ts"] = now

        opponent = random.choice(PRACTICE_OPPONENTS)
        my_roll = utils.roll_dice() + (1 if "protego" in player.get("spells", {}) else 0)
        opp_roll = random.randint(1, 6)

        if my_roll > opp_roll:
            utils.add_coins(player, 2)
            player["reputation"] = player.get("reputation", 0) + 1
            result = f"🎉 پیروز شدی! ({my_roll} در برابر {opp_roll})\n+۲ سکه، +۱ اعتبار"
        elif my_roll == opp_roll:
            result = f"🤝 مساوی شدید ({my_roll} در برابر {opp_roll})؛ داور دوئل را متوقف کرد."
        else:
            utils.add_mood(player, -1)
            result = f"💥 باختی ({my_roll} در برابر {opp_roll})\n-۱ روحیه"

        db.save_player(player)

    await callback.message.answer(f"⚔️ دوئل با {opponent}!\n\n{result}")
    await callback.answer()
