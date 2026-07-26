# ============================================================
#  RAVENMORE ACADEMY RPG — Utilities
# ============================================================
import random

import config
import game_data


def roll_dice() -> int:
    return random.randint(1, 6)


def dice_tier(value: int) -> str:
    if value <= 2:
        return "fail"
    if value <= 4:
        return "partial"
    return "success"


TIER_LABEL = {"fail": "❌ شکست", "partial": "🟡 موفقیت جزئی", "success": "✅ موفقیت کامل"}


def add_mood(player: dict, amount: int):
    player["mood"] = max(0, min(config.MAX_MOOD, player.get("mood", config.START_MOOD) + amount))


def add_coins(player: dict, amount: int):
    player["coins"] = max(0, player.get("coins", 0) + amount)


def add_knowledge(player: dict, amount: int):
    player["knowledge"] = max(0, player.get("knowledge", 0) + amount)
    check_knowledge_unlock(player)


def check_knowledge_unlock(player: dict):
    """هر ۵ دانش یک 'اسلات' جادوی عمومی آزاد می‌کند (جدا از جادوهای کوئستی)."""
    slots_earned = player["knowledge"] // 5
    player["knowledge_slots"] = slots_earned


def add_item(player: dict, item_name: str, amount: int = 1):
    items = player.setdefault("items", {})
    if items.get(item_name, 0) == -1:
        return  # دائمی، نیازی به افزایش نیست
    items[item_name] = items.get(item_name, 0) + amount


def remove_item(player: dict, item_name: str, amount: int = 1) -> bool:
    items = player.setdefault("items", {})
    have = items.get(item_name, 0)
    if have == -1:
        return True
    if have < amount:
        return False
    items[item_name] = have - amount
    return True


def learn_spell(player: dict, spell_id: str, level: str = "مبتدی"):
    spells = player.setdefault("spells", {})
    if spell_id not in spells:
        spells[spell_id] = level


def format_mood(mood: int) -> str:
    hearts = "❤️" * (mood // 2) + ("💔" if mood % 2 else "")
    return f"{hearts} {mood}/{config.MAX_MOOD}"


def format_profile(player: dict) -> str:
    spell_lines = "\n".join(
        f"  • {game_data.SPELLS[sid]['name']} ({lvl})"
        for sid, lvl in player.get("spells", {}).items()
        if sid in game_data.SPELLS
    ) or "  (هیچ)"
    item_lines = "\n".join(
        f"  • {name} ×{('∞' if cnt == -1 else cnt)}"
        for name, cnt in player.get("items", {}).items()
        if cnt != 0
    ) or "  (خالی)"

    return (
        f"📋 کارنامه شخصی\n\n"
        f"👤 نام: {player.get('name') or '—'}\n"
        f"✨ ویژگی: {player.get('trait') or '—'}\n"
        f"🪄 چوب‌دستی: {player.get('wand') or '—'}\n"
        f"🎯 آرزوی پنهان: {player.get('hidden_wish') or '—'}\n\n"
        f"❤️ روحیه: {format_mood(player.get('mood', config.START_MOOD))}\n"
        f"🧠 دانش جادویی: {player.get('knowledge', 0)}\n"
        f"🪙 سکه: {player.get('coins', 0)}\n"
        f"🏆 اعتبار: {player.get('reputation', 0)}\n"
        f"📖 فصل: {player.get('chapter', 1)}/3\n\n"
        f"🧙 جادوهای باز شده:\n{spell_lines}\n\n"
        f"🎒 آیتم‌ها:\n{item_lines}\n\n"
        f"📜 کوئست‌های انجام‌شده: {len(player.get('quests_completed', []))}"
    )


def apply_effects(player: dict, effects: dict) -> dict:
    """اثرات یک گزینه‌ی ایونت تاریک را روی player اعمال می‌کند.
    خروجی: همان دیکشنری effects (برای لاگ ادمین) به‌علاوه‌ی هرگونه فلگ محاسبه‌شده (مثل madness)."""
    result = dict(effects)
    if "mood" in effects:
        add_mood(player, effects["mood"])
    if "knowledge" in effects:
        add_knowledge(player, effects["knowledge"])
    if "reputation" in effects:
        player["reputation"] = player.get("reputation", 0) + effects["reputation"]
    if "coins" in effects:
        add_coins(player, effects["coins"])
    if "item" in effects:
        name, qty = effects["item"]
        add_item(player, name, qty)
    if "dark_power" in effects:
        player["dark_power"] = player.get("dark_power", 0) + effects["dark_power"]
    if "dark_secret" in effects:
        player.setdefault("dark_secrets", []).append(effects["dark_secret"])
    if effects.get("forbidden_book_given"):
        player["forbidden_book_given"] = True
    if effects.get("forbidden_book_read"):
        player["forbidden_book_reads"] = player.get("forbidden_book_reads", 0) + 1
        if player["forbidden_book_reads"] >= 6 and not player.get("madness"):
            player["madness"] = True
            player.setdefault("dark_secrets", []).append("جنون گرفت (۶ بار کتاب ممنوعه را خواند)")
            add_mood(player, -4)
            result["madness_triggered"] = True
    return result


def is_admin(player: dict, user_id: int) -> bool:
    return user_id == config.OWNER_ID or bool(player and player.get("is_admin"))
