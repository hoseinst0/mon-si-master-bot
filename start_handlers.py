# ============================================================
#  RAVENMORE ACADEMY RPG — Start / Onboarding Handlers
#  همه، از جمله ادمین و مالک ربات، از همین مسیر کاراکتر می‌سازند و بازی می‌کنند.
# ============================================================
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb
import utils

router = Router()

WELCOME = (
    "🏰 به آکادمی ریون‌مور خوش آمدی!\n\n"
    "هزار سال است این دیوارها شاهد یادگیری، خیانت و رازهای تاریک بوده‌اند. "
    "چیزی در زیرزمین‌های کهن خفته... و تو، دانش‌آموز تازه‌وارد، باید هم جادو یاد بگیری "
    "و هم پرده از رازی برداری که خودِ آکادمی می‌خواهد پنهانش کند.\n\n"
    "بیا اول یک اسم برای کاراکترت انتخاب کن. اسمت چیست؟"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if player is None:
            player = db.create_player(user_id, message.from_user.username or message.from_user.first_name, message.chat.id)
            await message.answer(WELCOME)
            return

    if player.get("onboarding_step") != "done":
        await resume_onboarding(message, player)
        return

    await message.answer(
        f"دوباره خوش اومدی، {player.get('name')}! 🪄",
        reply_markup=kb.main_menu(),
    )


async def resume_onboarding(message: Message, player: dict):
    step = player.get("onboarding_step", "name")
    if step == "name":
        await message.answer("اسمت چیست؟")
    elif step == "trait":
        await message.answer("ویژگی کاراکترت را انتخاب کن:", reply_markup=kb.trait_keyboard())
    elif step == "wand":
        await message.answer("چوب‌دستی‌ات از چه جنسی است؟", reply_markup=kb.wand_keyboard())
    elif step == "wish":
        await message.answer("آرزوی پنهانت در آکادمی چیست؟ (یک جمله بنویس)")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_free_text(message: Message):
    """در حالت onboarding، پیام‌های آزاد (اسم / آرزو) اینجا مدیریت می‌شوند.
    توی گروه، فقط وقتی که واقعاً منتظر یک ورودی متنی (اسم/آرزو) هستیم پاسخ می‌دهیم؛
    وگرنه ربات به هر پیام رد و بدل شده بین اعضای گروه واکنش نشان می‌داد (باگ اسپم)."""
    is_group = message.chat.type in ("group", "supergroup")
    user_id = message.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if player is None:
            return
        step = player.get("onboarding_step")
        if step == "name":
            player["name"] = message.text.strip()[:32]
            player["onboarding_step"] = "trait"
            db.save_player(player)
            await message.answer(f"اسم قشنگیه، {player['name']}! حالا ویژگی‌ات را انتخاب کن:", reply_markup=kb.trait_keyboard())
            return
        if step == "wish":
            player["hidden_wish"] = message.text.strip()[:200]
            player["onboarding_step"] = "done"
            db.save_player(player)
            await message.answer(
                "🎉 کاراکترت ساخته شد! به تالار ورودی آکادمی ریون‌مور رسیدی.\n\n"
                "استاد آلدریج نگاهی به تو می‌اندازد: «ریون‌مور به تو نگاه می‌کند، دانش‌آموز. "
                "مواظب باش چه چیزی را به آن نشان می‌دهی.»\n\n"
                "برای دیدن اولین نامه‌ات از منو «📜 کوئست بعدی» را بزن.",
                reply_markup=kb.main_menu(),
            )
            return

    if is_group:
        return  # توی گروه به پیام‌های آزاد دیگه (بین اعضا) واکنشی نشون نده

    # اگر onboarding تمام شده و پیام آزاد بود (فقط در چت خصوصی)، راهنمایی کن
    if player and player.get("onboarding_step") == "done":
        await message.answer("برای دیدن گزینه‌ها /menu را بزن یا از دکمه‌های زیر استفاده کن:", reply_markup=kb.main_menu())


@router.callback_query(F.data.startswith("onboard:trait:"))
async def cb_trait(callback: CallbackQuery):
    trait = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        player["trait"] = trait
        player["onboarding_step"] = "wand"
        db.save_player(player)
    await callback.message.edit_text(f"ویژگی «{trait}» ثبت شد.\n\nحالا چوب‌دستی‌ات را انتخاب کن:", reply_markup=kb.wand_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("onboard:wand:"))
async def cb_wand(callback: CallbackQuery):
    wand = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        player["wand"] = wand
        player["onboarding_step"] = "wish"
        db.save_player(player)
    await callback.message.edit_text(f"چوب‌دستی از جنس «{wand}» انتخاب شد.\n\nحالا آرزوی پنهانت را در آکادمی بنویس:")
    await callback.answer()


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("منوی آکادمی ریون‌مور:", reply_markup=kb.main_menu())


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return
    await callback.message.answer(utils.format_profile(player))
    await callback.answer()


@router.callback_query(F.data == "menu:close")
async def cb_close(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "menu:locations")
async def cb_locations(callback: CallbackQuery):
    import game_data
    text = "🏰 مکان‌های آکادمی:\n\n" + "\n".join(f"• {v}" for v in game_data.LOCATIONS.values())
    await callback.message.answer(text)
    await callback.answer()
