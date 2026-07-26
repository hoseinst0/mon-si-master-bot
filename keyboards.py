# ============================================================
#  RAVENMORE ACADEMY RPG — Keyboards
# ============================================================
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import game_data


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 کارنامه", callback_data="menu:profile", style="primary")
    kb.button(text="📜 کوئست بعدی", callback_data="menu:quest", style="success")
    kb.button(text="🗺 کوئست‌های جانبی/مخفی", callback_data="menu:side_quests", style="primary")
    kb.button(text="🧙 جادوها", callback_data="menu:spells", style="primary")
    kb.button(text="🎒 کوله‌پشتی", callback_data="menu:inventory", style="primary")
    kb.button(text="🛒 بازار ریون‌مور", callback_data="menu:shop", style="primary")
    kb.button(text="🛏 خوابیدن", callback_data="menu:sleep", style="primary")
    kb.button(text="🗺 مکان‌ها", callback_data="menu:locations", style="primary")
    kb.adjust(2)
    return kb.as_markup()


def trait_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in game_data.TRAITS:
        kb.button(text=t, callback_data=f"onboard:trait:{t}", style="primary")
    kb.adjust(2)
    return kb.as_markup()


def wand_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for w in game_data.WANDS:
        kb.button(text=w, callback_data=f"onboard:wand:{w}", style="primary")
    kb.adjust(3)
    return kb.as_markup()


def accept_quest_keyboard(qid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ این کوئست را قبول می‌کنم", callback_data=f"quest:accept:{qid}", style="success")
    kb.button(text="⏭ فعلاً نه", callback_data="menu:close", style="danger")
    kb.adjust(1)
    return kb.as_markup()


def roll_keyboard(qid: str, step_idx: int, can_reroll: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 تاس بریز", callback_data=f"quest:roll:{qid}:{step_idx}", style="success")
    if can_reroll:
        kb.button(text="🔮 استفاده از سنگ خلسه (رول مجدد)", callback_data=f"quest:reroll:{qid}:{step_idx}", style="primary")
    kb.adjust(1)
    return kb.as_markup()


def shop_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for name, price in game_data.SHOP:
        kb.button(text=f"{name} — {price} سکه", callback_data=f"shop:buy:{name}", style="primary")
    kb.adjust(1)
    return kb.as_markup()


def side_quests_keyboard(quests) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for q in quests:
        kb.button(text=f"{q['name']} ({q['type']})", callback_data=f"quest:accept:{q['id']}", style="primary")
    kb.adjust(1)
    return kb.as_markup()


def close_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="بستن ❌", callback_data="menu:close", style="danger")
    return kb.as_markup()
