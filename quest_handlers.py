# ============================================================
#  RAVENMORE ACADEMY RPG — Quest Engine Handlers
# ============================================================
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

import database as db
import game_data
import quests_data as qd
import keyboards as kb
import utils

router = Router()

# متن‌های فعال‌سازی کوئست‌های مخفی → شناسه‌ی کوئست
HIDDEN_TRIGGERS = {
    "درب پشت قفسه سوم را بررسی می‌کنم": "c1_hidden",
    "به زمزمه‌ها گوش می‌دهم": "c2_hidden",
    "چشمانم را به تاریکی عادت می‌دهم": "c3_hidden1",
    "به کلاغ‌ها گوش می‌دهم": "c3_hidden2",
}


def quest_intro_text(q: dict) -> str:
    npc = game_data.NPCS.get(q.get("npc"), {})
    loc = game_data.LOCATIONS.get(q.get("location"), "")
    header = f"📬 نامه جدید — {q['name']}\n📍 مکان: {loc}\n"
    if npc:
        header += f"👤 {npc['name']} ({npc.get('role','')})\n"
    return header + "\n" + q["letter"]


@router.callback_query(F.data == "menu:quest")
async def cb_next_quest(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return

    active = player.get("quests_active", {})
    if active:
        qid = next(iter(active.keys()))
        q = qd.get_quest(qid)
        step_idx = active[qid]["step"]
        await send_step(callback.message, player, q, step_idx)
        await callback.answer()
        return

    q = qd.next_main_quest(player)
    if q is None:
        if len(player.get("quests_completed", [])) >= len(qd.MAIN_LINE_ORDER):
            await callback.message.answer("🏆 تو تمام کوئست‌های اصلی آکادمی ریون‌مور را به پایان رساندی! داستان تو در این‌جا به اوج می‌رسد... فعلاً.")
        else:
            await callback.message.answer("فعلاً نامه‌ی جدیدی برایت نرسیده. کمی صبر کن یا سراغ کوئست‌های جانبی/مخفی برو.")
        await callback.answer()
        return

    await callback.message.answer(quest_intro_text(q), reply_markup=kb.accept_quest_keyboard(q["id"]))
    await callback.answer()


@router.callback_query(F.data == "menu:side_quests")
async def cb_side_quests(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return
    hidden = qd.available_hidden_quests(player)
    if not hidden:
        await callback.message.answer(
            "فعلاً کوئست جانبی/مخفی در دسترس نیست. برخی کوئست‌های مخفی فقط با انجام یک اکشن خاص در یک مکان خاص فعال می‌شوند — کاوش کن!"
        )
        await callback.answer()
        return
    await callback.message.answer("🗺 کوئست‌های مخفی در دسترس:", reply_markup=kb.side_quests_keyboard(hidden))
    await callback.answer()


@router.callback_query(F.data.startswith("quest:accept:"))
async def cb_accept_quest(callback: CallbackQuery):
    qid = callback.data.split(":", 2)[2]
    q = qd.get_quest(qid)
    if not q:
        await callback.answer("این کوئست پیدا نشد.", show_alert=True)
        return
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if qid in player.get("quests_completed", []) and q["type"] not in ("side",):
            await callback.answer("این کوئست را قبلاً انجام داده‌ای.", show_alert=True)
            return
        if player.get("mood", 0) <= 0:
            await callback.answer("روحیه‌ات صفر است و غش کرده‌ای! اول استراحت کن.", show_alert=True)
            return
        active = player.setdefault("quests_active", {})
        active[qid] = {"step": 0}
        db.save_player(player)
    await callback.message.edit_text(f"✅ کوئست «{q['name']}» را پذیرفتی!")
    await send_step(callback.message, player, q, 0)
    await callback.answer()


async def send_step(message: Message, player: dict, q: dict, step_idx: int):
    step = q["steps"][step_idx]
    text = f"مرحله {step_idx + 1}/{len(q['steps'])}: {step['title']}"
    await message.answer(text, reply_markup=kb.roll_keyboard(q["id"], step_idx))


@router.callback_query(F.data.startswith("quest:roll:"))
async def cb_roll(callback: CallbackQuery):
    _, _, qid, step_idx_s = callback.data.split(":")
    step_idx = int(step_idx_s)
    await do_roll(callback, qid, step_idx, forced=False)


@router.callback_query(F.data.startswith("quest:accept_roll:"))
async def cb_accept_roll(callback: CallbackQuery):
    """بازیکن نتیجه‌ی 'شکست' را بدون رول مجدد قبول می‌کند."""
    _, _, qid, step_idx_s = callback.data.split(":")
    step_idx = int(step_idx_s)
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        pending = player.get("pending_roll")
        if not player or not pending or pending.get("qid") != qid or pending.get("step_idx") != step_idx:
            await callback.answer("این تاس دیگر معتبر نیست.", show_alert=True)
            return
        player["pending_roll"] = None
        db.save_player(player)
        await _finalize_roll(callback, player, qid, step_idx, pending["dice_value"])


@router.callback_query(F.data.startswith("quest:reroll:"))
async def cb_reroll(callback: CallbackQuery):
    _, _, qid, step_idx_s = callback.data.split(":")
    step_idx = int(step_idx_s)
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        pending = player.get("pending_roll") if player else None
        if not player or not pending or pending.get("qid") != qid or pending.get("step_idx") != step_idx:
            await callback.answer("این تاس دیگر معتبر نیست.", show_alert=True)
            return
        if not utils.remove_item(player, "سنگ خلسه", 1):
            await callback.answer("سنگ خلسه‌ای نداری!", show_alert=True)
            return
        player["pending_roll"] = None
        db.save_player(player)
    await do_roll(callback, qid, step_idx, forced=True)


async def do_roll(callback: CallbackQuery, qid: str, step_idx: int, forced: bool):
    """forced=True یعنی نتیجه هرچه باشد اعمال می‌شود (چه رول اولیه بدون سنگ خلسه در دسترس،
    چه رول مجددی که با مصرف سنگ خلسه گرفته شده‌است)."""
    q = qd.get_quest(qid)
    if not q:
        await callback.answer("کوئست پیدا نشد.", show_alert=True)
        return
    user_id = callback.from_user.id

    dice_value = utils.roll_dice()
    tier = utils.dice_tier(dice_value)

    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        active = player.get("quests_active", {}).get(qid) if player else None
        # جلوگیری از دو-بار-رول هم‌زمان (دابل‌کلیک روی دکمه‌ی تاس):
        # اگر مرحله‌ی فعلیِ ذخیره‌شده با step_idx این کلیک یکی نیست، این کلیک دیگر منقضی شده.
        if not active or active.get("step") != step_idx:
            await callback.answer("این مرحله دیگر فعال نیست (شاید قبلاً روش تاس زده‌ای؟).", show_alert=True)
            return

        if not forced and tier == "fail":
            has_stone = player.get("items", {}).get("سنگ خلسه", 0) not in (0, None)
            if has_stone:
                player["pending_roll"] = {"qid": qid, "step_idx": step_idx, "dice_value": dice_value}
                db.save_player(player)
                step = q["steps"][step_idx]
                outcome = step["outcomes"][tier]
                text = (
                    f"🎲 نتیجه تاس: {dice_value} → {utils.TIER_LABEL[tier]}\n"
                    f"{outcome['text']}\n\n"
                    "سنگ خلسه داری — می‌خوای همین نتیجه رو قبول کنی یا رول مجدد بزنی؟"
                )
                await callback.message.edit_text(text, reply_markup=kb.reroll_choice_keyboard(qid, step_idx))
                await callback.answer()
                return

        await _finalize_roll(callback, player, qid, step_idx, dice_value)


async def _finalize_roll(callback: CallbackQuery, player: dict, qid: str, step_idx: int, dice_value: int):
    """اعمال قطعیِ اثر یک نتیجه‌ی تاس (باید داخل db.player_lock صدا زده شود)."""
    q = qd.get_quest(qid)
    step = q["steps"][step_idx]
    tier = utils.dice_tier(dice_value)
    outcome = step["outcomes"][tier]

    utils.add_mood(player, outcome.get("mood", 0))
    is_last_step = step_idx + 1 >= len(q["steps"])

    result_lines = [
        f"🎲 نتیجه تاس: {dice_value} → {utils.TIER_LABEL[tier]}",
        outcome["text"],
    ]
    if outcome.get("mood", 0) < 0:
        result_lines.append(f"(روحیه {outcome['mood']})")

    if is_last_step:
        reward = q.get("reward", {})
        reward_lines = []
        if reward.get("coins"):
            utils.add_coins(player, reward["coins"])
            reward_lines.append(f"+{reward['coins']} 🪙 سکه")
        if reward.get("knowledge"):
            utils.add_knowledge(player, reward["knowledge"])
            reward_lines.append(f"+{reward['knowledge']} 🧠 دانش")
        if reward.get("spell"):
            spell = game_data.SPELLS.get(reward["spell"])
            utils.learn_spell(player, reward["spell"], spell["level"] if spell else "مبتدی")
            reward_lines.append(f"🧙 جادوی جدید: {spell['name'] if spell else reward['spell']}")
        if reward.get("item"):
            utils.add_item(player, reward["item"], 1)
            reward_lines.append(f"🎒 آیتم: {reward['item']}")

        player.setdefault("quests_completed", []).append(qid)
        player.get("quests_active", {}).pop(qid, None)

        # پیشرفت فصل: اگر همه‌ی کوئست‌های اصلی فصل جاری تمام شدند، برو فصل بعد
        chapter_quests = [k for k, v in qd.QUESTS.items() if v["chapter"] == player.get("chapter", 1) and v["type"] == "main"]
        if all(k in player["quests_completed"] for k in chapter_quests) and player.get("chapter", 1) < 3:
            player["chapter"] += 1
            result_lines.append(f"\n🌗 فصل جدید آغاز شد: فصل {player['chapter']}!")

        db.save_player(player)
        result_lines.append("\n🎉 کوئست «" + q["name"] + "» با موفقیت به پایان رسید!\n" + "\n".join(reward_lines))
        await callback.message.edit_text("\n".join(result_lines))
    else:
        player["quests_active"][qid]["step"] = step_idx + 1
        db.save_player(player)
        await callback.message.edit_text("\n".join(result_lines))
        await send_step(callback.message, player, q, step_idx + 1)

    await callback.answer()


# ------------------------------------------------------------
#  فعال‌سازی کوئست‌های مخفی با گفتن جمله‌ی خاص در چت
#  (باید قبل از هندلر آزاد متنِ start_handlers ثبت شود)
# ------------------------------------------------------------
@router.message(F.text.in_(list(HIDDEN_TRIGGERS.keys())))
async def hidden_trigger(message: Message):
    qid = HIDDEN_TRIGGERS[message.text]
    q = qd.get_quest(qid)
    user_id = message.from_user.id
    player = db.get_player(user_id)
    if not player or player.get("onboarding_step") != "done":
        return
    if qid in player.get("quests_completed", []):
        await message.answer("قبلاً این راز را کشف کرده‌ای.")
        return
    if not all(p in player.get("quests_completed", []) for p in q.get("prereq", [])):
        await message.answer("چیزی همین‌جا حس می‌کنی... اما هنوز آماده نیستی.")
        return
    await message.answer("🔍 یک راز آشکار می‌شود...\n\n" + quest_intro_text(q), reply_markup=kb.accept_quest_keyboard(qid))
