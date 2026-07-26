# ============================================================
#  RAVENMORE ACADEMY RPG — Market Handlers (بازار ریون‌مور)
# ============================================================
from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
import game_data
import keyboards as kb
import utils

router = Router()


@router.callback_query(F.data == "menu:shop")
async def cb_shop(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return
    text = f"🛒 بازار ریون‌مور\n🪙 سکه‌های تو: {player.get('coins', 0)}\n\nموجودی این هفته:"
    await callback.message.answer(text, reply_markup=kb.shop_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("shop:buy:"))
async def cb_buy(callback: CallbackQuery):
    item_name = callback.data.split(":", 2)[2]
    price = dict(game_data.SHOP).get(item_name)
    if price is None:
        await callback.answer("این آیتم دیگر موجود نیست.", show_alert=True)
        return

    user_id = callback.from_user.id
    async with db.player_lock(user_id):
        player = db.get_player(user_id)
        if player.get("coins", 0) < price:
            await callback.answer(f"سکه کافی نداری! ({player.get('coins',0)}/{price})", show_alert=True)
            return
        utils.add_coins(player, -price)
        utils.add_item(player, item_name, 1)
        db.save_player(player)

    await callback.answer(f"✅ خریدی: {item_name}", show_alert=True)
    await callback.message.answer(f"🪄 «{item_name}» به کوله‌پشتی‌ات اضافه شد.\n🪙 سکه باقیمانده: {player['coins']}")


@router.callback_query(F.data == "menu:inventory")
async def cb_inventory(callback: CallbackQuery):
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("اول /start رو بزن.", show_alert=True)
        return
    lines = []
    for name, cnt in player.get("items", {}).items():
        if cnt == 0:
            continue
        desc = game_data.ITEMS.get(name, {}).get("desc", "")
        cnt_str = "∞" if cnt == -1 else f"×{cnt}"
        lines.append(f"• {name} {cnt_str} — {desc}")
    text = "🎒 کوله‌پشتی:\n\n" + ("\n".join(lines) if lines else "خالی است.")
    await callback.message.answer(text)
    await callback.answer()
