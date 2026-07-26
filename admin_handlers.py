# ============================================================
#  RAVENMORE ACADEMY RPG — Admin Panel
#  مالک ربات (OWNER_ID) همیشه ادمین است. ادمین‌ها می‌توانند بازی هم بکنند —
#  این دستورات فقط قابلیت اضافه هستند و مانع بازی‌کردن عادی نمی‌شوند.
# ============================================================
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import config
import database as db
import game_data
import letters
import utils

router = Router()


def _is_admin(user_id: int) -> bool:
    if user_id == config.OWNER_ID:
        return True
    state = db.get_state()
    return user_id in state.get("admins", [])


async def _require_admin(message: Message) -> bool:
    if not _is_admin(message.from_user.id):
        await message.answer("⛔️ این دستور فقط برای ادمین‌های آکادمی است.")
        return False
    return True


@router.message(Command("admin"))
async def cmd_admin_help(message: Message):
    if not await _require_admin(message):
        return
    await message.answer(
        "🛠 پنل ادمین آکادمی ریون‌مور\n\n"
        "/give_coin <user_id> <n>\n"
        "/give_knowledge <user_id> <n>\n"
        "/give_item <user_id> <نام آیتم> <n>\n"
        "/give_spell <user_id> <spell_id>\n"
        "/set_mood <user_id> <n>\n"
        "/reset_player <user_id>\n"
        "/players — لیست تعداد بازیکنان\n"
        "/broadcast <متن>\n"
        "/advance_day — یک روز آکادمی را جلو بینداز (تست نامه‌ها)\n"
        "/make_admin <user_id>\n"
        "/remove_admin <user_id>\n"
        "/whoami — دیدن آیدی عددی خودت"
    )


@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    await message.answer(f"آیدی عددی تو: {message.from_user.id}")


def _parse_target(message: Message, min_parts: int):
    parts = message.text.split(maxsplit=min_parts - 1)
    if len(parts) < min_parts:
        return None
    return parts


@router.message(Command("give_coin"))
async def cmd_give_coin(message: Message):
    if not await _require_admin(message):
        return
    parts = _parse_target(message, 3)
    if not parts:
        await message.answer("فرمت: /give_coin <user_id> <n>")
        return
    try:
        uid, n = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("عدد نامعتبر.")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        utils.add_coins(player, n)
        db.save_player(player)
    await message.answer(f"✅ {n} سکه به {uid} داده شد.")


@router.message(Command("give_knowledge"))
async def cmd_give_knowledge(message: Message):
    if not await _require_admin(message):
        return
    parts = _parse_target(message, 3)
    if not parts:
        await message.answer("فرمت: /give_knowledge <user_id> <n>")
        return
    try:
        uid, n = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("عدد نامعتبر.")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        utils.add_knowledge(player, n)
        db.save_player(player)
    await message.answer(f"✅ {n} دانش به {uid} داده شد.")


@router.message(Command("give_item"))
async def cmd_give_item(message: Message):
    if not await _require_admin(message):
        return
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("فرمت: /give_item <user_id> <نام آیتم بدون فاصله_با_زیرخط> <n>\nمثال: /give_item 12345 سنگ_روح 1")
        return
    try:
        uid = int(parts[1])
        n = int(parts[-1])
        item_name = " ".join(parts[2:-1]).replace("_", " ")
    except ValueError:
        await message.answer("فرمت نادرست.")
        return
    if item_name not in game_data.ITEMS:
        await message.answer(f"آیتم «{item_name}» شناخته‌شده نیست.\nآیتم‌های معتبر: {', '.join(game_data.ITEMS.keys())}")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        utils.add_item(player, item_name, n)
        db.save_player(player)
    await message.answer(f"✅ {n}× {item_name} به {uid} داده شد.")


@router.message(Command("give_spell"))
async def cmd_give_spell(message: Message):
    if not await _require_admin(message):
        return
    parts = _parse_target(message, 3)
    if not parts:
        await message.answer(f"فرمت: /give_spell <user_id> <spell_id>\nspell_id های معتبر: {', '.join(game_data.SPELLS.keys())}")
        return
    uid_s, spell_id = parts[1], parts[2]
    if spell_id not in game_data.SPELLS:
        await message.answer("spell_id نامعتبر است.")
        return
    try:
        uid = int(uid_s)
    except ValueError:
        await message.answer("آیدی نامعتبر.")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        utils.learn_spell(player, spell_id, game_data.SPELLS[spell_id]["level"])
        db.save_player(player)
    await message.answer(f"✅ جادوی {game_data.SPELLS[spell_id]['name']} به {uid} آموزش داده شد.")


@router.message(Command("set_mood"))
async def cmd_set_mood(message: Message):
    if not await _require_admin(message):
        return
    parts = _parse_target(message, 3)
    if not parts:
        await message.answer("فرمت: /set_mood <user_id> <0-10>")
        return
    try:
        uid, n = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("عدد نامعتبر.")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        player["mood"] = max(0, min(config.MAX_MOOD, n))
        db.save_player(player)
    await message.answer(f"✅ روحیه {uid} روی {n} تنظیم شد.")


@router.message(Command("reset_player"))
async def cmd_reset_player(message: Message):
    if not await _require_admin(message):
        return
    parts = _parse_target(message, 2)
    if not parts:
        await message.answer("فرمت: /reset_player <user_id>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("آیدی نامعتبر.")
        return
    async with db.player_lock(uid):
        player = db.get_player(uid)
        if not player:
            await message.answer("بازیکن پیدا نشد.")
            return
        new_doc = db.new_player_doc(uid, player.get("username", ""), player.get("chat_id"))
        new_doc["_v"] = player.get("_v", 0)
        db.save_player(new_doc)
    await message.answer(f"♻️ کاراکتر {uid} ریست شد.")


@router.message(Command("players"))
async def cmd_players(message: Message):
    if not await _require_admin(message):
        return
    all_p = db.all_players()
    done = [p for p in all_p if p.get("onboarding_step") == "done"]
    await message.answer(f"👥 کل کاربران: {len(all_p)}\n🎓 کاراکتر کامل‌شده: {len(done)}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not await _require_admin(message):
        return
    text = message.text.partition(" ")[2]
    if not text:
        await message.answer("فرمت: /broadcast <متن>")
        return
    count = 0
    for chat_id in db.all_chat_ids():
        try:
            await message.bot.send_message(chat_id, f"📢 اعلامیه آکادمی:\n\n{text}")
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ برای {count} نفر ارسال شد.")


@router.message(Command("advance_day"))
async def cmd_advance_day(message: Message):
    if not await _require_admin(message):
        return
    await letters._advance_day_and_notify(message.bot)
    state = db.get_state()
    await message.answer(f"📅 روز آکادمی به {state['academy_day']} رسید و نامه/اطلاعیه ارسال شد.")


@router.message(Command("make_admin"))
async def cmd_make_admin(message: Message):
    if message.from_user.id != config.OWNER_ID:
        await message.answer("⛔️ فقط مالک ربات می‌تواند ادمین اضافه کند.")
        return
    parts = _parse_target(message, 2)
    if not parts:
        await message.answer("فرمت: /make_admin <user_id>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("آیدی نامعتبر.")
        return
    state = db.get_state()
    admins = set(state.get("admins", []))
    admins.add(uid)
    state["admins"] = list(admins)
    db.save_state(state)
    await message.answer(f"✅ {uid} ادمین شد.")


@router.message(Command("remove_admin"))
async def cmd_remove_admin(message: Message):
    if message.from_user.id != config.OWNER_ID:
        await message.answer("⛔️ فقط مالک ربات می‌تواند ادمین حذف کند.")
        return
    parts = _parse_target(message, 2)
    if not parts:
        await message.answer("فرمت: /remove_admin <user_id>")
        return
    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("آیدی نامعتبر.")
        return
    state = db.get_state()
    admins = set(state.get("admins", []))
    admins.discard(uid)
    state["admins"] = list(admins)
    db.save_state(state)
    await message.answer(f"✅ {uid} از ادمینی حذف شد.")
