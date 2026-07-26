# ============================================================
#  RAVENMORE ACADEMY RPG — Spells & Sleep Handlers
# ============================================================
import time

from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
import game_data
import utils

router = Router()


@router.callback_query(F.data == "menu:spells")
async def cb_spells(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return

    known = player.get("spells", {})
    lines = ["🧙 درخت جادوهای ریون‌مور\n"]
    for cat in game_data.SPELL_CATEGORIES:
        cat_spells = [(sid, s) for sid, s in game_data.SPELLS.items() if s["cat"] == cat]
        if not cat_spells:
            continue
        lines.append(f"\n— {cat} —")
        for sid, s in cat_spells:
            if sid in known:
                lines.append(f"  ✅ {s['name']} ({known[sid]}) — {s['effect']}")
            else:
                lines.append(f"  🔒 {s['name']} ({s['level']}) — {s['effect']}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "menu:sleep")
async def cb_sleep(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        state = db.get_state()
        today = state.get("academy_day", 1)
        if player.get("last_slept_day") == today:
            await callback.answer("امشب قبلاً خوابیدی!", show_alert=True)
            return
        player["last_slept_day"] = today
        utils.add_mood(player, 2)
        db.save_player(player)
    await callback.message.answer(f"🛏 خوابیدی و کمی روحیه‌ات بهتر شد. روحیه فعلی: {utils.format_mood(player['mood'])}")
    await callback.answer()
