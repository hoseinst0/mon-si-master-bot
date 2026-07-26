# ============================================================
#  RAVENMORE ACADEMY RPG — Dark Events Engine
#  این ایونت‌ها به‌صورت تصادفی و در زمان‌های نامنظمِ واقعی برای بازیکنانی
#  که حداقل یک کوئست را تمام کرده‌اند فعال می‌شوند. بازیکن فقط گزینه‌ها و
#  روایتِ نتیجه را می‌بیند؛ عدد تاس و مقدار دقیق اثرات هرگز به او نشان
#  داده نمی‌شود — این‌ها فقط با /darklog و /secrets برای ادمین/گیم‌مستر
#  قابل مشاهده‌اند (طبق تصمیم طراحی).
# ============================================================
import asyncio
import logging
import random
import time

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database as db
import dark_events_data as ded
import utils

router = Router()
logger = logging.getLogger("ravenmore.dark_events")

# مدتی که یک ایونتِ بی‌پاسخ معتبر می‌ماند؛ بعدش رها می‌شود تا ایونت جدید بتواند بیاید
STALE_EVENT_SECONDS = 2 * 24 * 3600


def _dark_event_keyboard(event_id: str, options: list):
    kb = InlineKeyboardBuilder()
    for opt in options:
        kb.button(text=opt["label"], callback_data=f"dark:{event_id}:{opt['key']}", style="primary")
    kb.adjust(1)
    return kb.as_markup()


def _pick_event(player: dict) -> str | None:
    candidates = []
    for eid, ev in ded.DARK_EVENTS.items():
        if eid == "forbidden_book" and player.get("forbidden_book_given"):
            continue
        candidates.append((eid, ev["weight"]))
    if not candidates:
        return None
    total = sum(w for _, w in candidates)
    r = random.uniform(0, total)
    upto = 0
    for eid, w in candidates:
        upto += w
        if r <= upto:
            return eid
    return candidates[-1][0]


async def send_dark_event(bot, player: dict):
    event_id = _pick_event(player)
    if not event_id:
        return
    ev = ded.DARK_EVENTS[event_id]
    try:
        await bot.send_message(
            player["chat_id"],
            "🌑 " + ev["text"],
            reply_markup=_dark_event_keyboard(event_id, ev["options"]),
        )
    except Exception as e:
        logger.warning(f"dark event send failed for {player['_id']}: {e}")
        return
    player["active_dark_event"] = {"event_id": event_id, "sent_ts": time.time()}
    player["last_dark_event_ts"] = time.time()
    db.save_player(player)


@router.callback_query(F.data.startswith("dark:"))
async def cb_dark_option(callback: CallbackQuery):
    _, event_id, option_key = callback.data.split(":", 2)
    user_id = callback.from_user.id

    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if not player:
            await callback.answer()
            return
        active = player.get("active_dark_event")
        if not active or active.get("event_id") != event_id:
            await callback.answer("این راز دیگر معتبر نیست...", show_alert=True)
            return

        option = ded.get_option(event_id, option_key)
        if not option:
            await callback.answer("این گزینه دیگر وجود ندارد.", show_alert=True)
            return

        player["active_dark_event"] = None  # بلافاصله ببند تا دوبار پردازش نشود

        dice_value = None
        if option.get("dice"):
            dice_value = random.randint(1, 6)
            text, effects = ded.resolve_dice_outcome(option, dice_value)
        else:
            text, effects = option["text"], option.get("effects", {})

        applied = utils.apply_effects(player, effects)
        db.save_player(player)
        db.log_dark_event(user_id, event_id, option_key, dice_value, applied)

    await callback.message.edit_text("🌑 " + text + "\n\n(اثری از این اتفاق در وجودت باقی ماند...)")
    await callback.answer()

    if applied.get("madness_triggered"):
        try:
            await callback.bot.send_message(
                config.OWNER_ID,
                f"⚠️ بازیکن {player.get('name') or user_id} ({user_id}) به‌خاطر خواندن مکرر کتاب ممنوعه دچار جنون شد.",
            )
        except Exception:
            pass


async def dark_events_scheduler_loop(bot):
    """این تسک باید یک‌بار با asyncio.create_task در استارتاپ ربات اجرا شود."""
    while True:
        try:
            now = time.time()
            for p in db.all_players():
                if p.get("onboarding_step") != "done":
                    continue
                if not p.get("quests_completed"):
                    continue  # قبل از تمام کردن اولین کوئست، ایونت تاریک نیاید
                if p.get("mood", 0) <= 0:
                    continue

                active = p.get("active_dark_event")
                if active:
                    if now - active.get("sent_ts", 0) < STALE_EVENT_SECONDS:
                        continue
                    p["active_dark_event"] = None

                cooldown = config.DARK_EVENT_MIN_COOLDOWN_HOURS * 3600
                if now - p.get("last_dark_event_ts", 0) < cooldown:
                    continue

                if random.random() < config.DARK_EVENT_TRIGGER_CHANCE:
                    async with db.player_lock(p["_id"]):
                        fresh = db.get_player(p["_id"])
                        if fresh and not fresh.get("active_dark_event"):
                            await send_dark_event(bot, fresh)
        except Exception as e:
            logger.exception(f"dark events scheduler error: {e}")
        await asyncio.sleep(config.DARK_EVENT_CHECK_INTERVAL_SECONDS)
