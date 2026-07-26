# ============================================================
#  RAVENMORE ACADEMY RPG — Letter / Calendar Scheduler
#  هر HOURS_PER_ACADEMY_DAY ساعتِ واقعی = ۱ روز آکادمی.
#  هر LETTER_INTERVAL_DAYS روزِ آکادمی، یک نامه‌ی عمومی برای همه ارسال می‌شود.
#  (هر بازیکن با زدن «📜 کوئست بعدی» کوئست شخصی‌سازی‌شده‌ی خودش را می‌بیند —
#   چون بازیکن‌ها ممکن است با سرعت‌های متفاوت پیش بروند)
# ============================================================
import asyncio
import logging
import time

import config
import database as db

logger = logging.getLogger("ravenmore.letters")

CHECK_INTERVAL_SECONDS = 15 * 60  # هر ۱۵ دقیقه وضعیت تقویم را چک کن

LETTER_TEXT = (
    "🐦‍⬛ یک کلاغ سیاه نامه‌ای روی طاقچه‌ی پنجره‌ات گذاشته...\n\n"
    "نامه‌ی جدیدی از آکادمی رسیده! برای دیدن کوئست بعدی‌ات، از منو «📜 کوئست بعدی» را بزن."
)

NIGHT_TEXT = (
    "🌙 شب شده. اگر امشب نخوابی، فردا روحیه‌ات کم می‌شود. برای خوابیدن از منو «🛏 خوابیدن» را بزن."
)


async def _advance_day_and_notify(bot):
    state = db.get_state()
    state["academy_day"] = state.get("academy_day", 1) + 1
    state["last_day_advance_ts"] = time.time()
    day = state["academy_day"]

    chat_ids = db.all_chat_ids()

    # اعمال جریمه‌ی نخوابیدن برای شب قبل
    for p in db.all_players():
        if p.get("onboarding_step") != "done":
            continue
        if p.get("last_slept_day", 0) < day - 1:
            async with db.player_lock(p["_id"]):
                pl = db.get_player(p["_id"])
                if pl and pl.get("last_slept_day", 0) < day - 1 and pl.get("mood", 0) > 0:
                    pl["mood"] = max(0, pl["mood"] - 1)
                    db.save_player(pl)

    is_letter_day = day % config.LETTER_INTERVAL_DAYS == 1
    if is_letter_day:
        state["last_letter_day_sent"] = day
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, LETTER_TEXT)
            except Exception as e:
                logger.warning(f"letter send failed for {chat_id}: {e}")
    else:
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, NIGHT_TEXT)
            except Exception as e:
                logger.warning(f"night text send failed for {chat_id}: {e}")

    db.save_state(state)
    logger.info(f"Academy day advanced to {day} (letter_day={is_letter_day})")


async def letter_scheduler_loop(bot):
    """این تسک باید یک‌بار با asyncio.create_task در استارتاپ ربات اجرا شود."""
    while True:
        try:
            state = db.get_state()
            elapsed_hours = (time.time() - state.get("last_day_advance_ts", time.time())) / 3600
            if elapsed_hours >= config.HOURS_PER_ACADEMY_DAY:
                await _advance_day_and_notify(bot)
        except Exception as e:
            logger.exception(f"letter scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
