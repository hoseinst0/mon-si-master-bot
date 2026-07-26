# ============================================================
#  RAVENMORE ACADEMY RPG — Database (MongoDB)
# ============================================================
import asyncio
import time
from typing import Optional

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection

import config

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(
            config.MONGODB_URL,
            maxPoolSize=50,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        _db = _client["ravenmore_academy"]
    return _db


def players_col() -> Collection:
    return get_db()["players"]


def state_col() -> Collection:
    return get_db()["game_state"]


def dark_log_col() -> Collection:
    return get_db()["dark_event_log"]


# ------------------------------------------------------------
#  قفل هم‌زمانی به‌ازای هر کاربر (جلوگیری از Lost Update وقتی دو
#  اکشن هم‌زمان روی یک کاراکتر اجرا می‌شوند — مثلا خرید از بازار +
#  گرفتن پاداش کوئست هم‌زمان)
# ------------------------------------------------------------
_player_locks: dict[int, asyncio.Lock] = {}


def _get_lock(user_id: int) -> asyncio.Lock:
    lock = _player_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _player_locks[user_id] = lock
    return lock


class player_lock:
    """استفاده: async with player_lock(user_id): ... بخوان، تغییر بده، ذخیره کن"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self._lock = _get_lock(user_id)

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()


# ------------------------------------------------------------
#  ساختار پیش‌فرض کاراکتر تازه‌وارد
# ------------------------------------------------------------
def new_player_doc(user_id: int, username: str, chat_id: int) -> dict:
    return {
        "_id": user_id,
        "username": username or "",
        "chat_id": chat_id,
        "created_at": time.time(),
        "onboarding_step": "name",  # name -> trait -> wand -> wish -> done
        "name": None,
        "trait": None,
        "wand": None,
        "hidden_wish": None,
        "mood": config.START_MOOD,
        "knowledge": 0,
        "coins": 0,
        "reputation": 0,
        "chapter": 1,
        "spells": {"lumos": "مبتدی"},
        "items": {
            "چوب‌دستی شخصی": -1,   # -1 یعنی دائمی / بی‌شمار
            "کیف بی‌نهایت": -1,
            "آبنبات جادویی": 3,
            "سنگ خلسه": 1,
        },
        "quests_completed": [],
        "quests_active": {},   # quest_id -> {"step": int}
        "pending_roll": None,  # {"qid":..., "step_idx":..., "dice_value":...} وقتی سنگ خلسه پیشنهاد می‌شود
        "last_letter_seen": 0,
        "last_slept_day": 0,
        "fainted_until_day": 0,
        "is_admin": False,
        # --- ایونت‌های تاریک (فقط برای گیم‌مستر/ادمین قابل مشاهده) ---
        "last_dark_event_ts": 0,
        "active_dark_event": None,      # {"event_id":..., "sent_ts":...} تا پاسخ داده نشده
        "dark_secrets": [],             # لیست متنی رازهای تاریکی که کسب کرده (فقط ادمین می‌بیند)
        "dark_power": 0,                # شمارنده‌ی قدرت تاریک انباشته‌شده
        "forbidden_book_reads": 0,
        "forbidden_book_given": False,
        "madness": False,               # فقط ادمین می‌بیند؛ به بازیکن هیچ‌وقت مستقیم گفته نمی‌شود
        "_v": 0,
    }


def get_player(user_id: int) -> Optional[dict]:
    return players_col().find_one({"_id": user_id})


def create_player(user_id: int, username: str, chat_id: int) -> dict:
    doc = new_player_doc(user_id, username, chat_id)
    players_col().insert_one(doc)
    return doc


def save_player(doc: dict) -> dict:
    """ذخیره با کنترل نسخه‌ی خوش‌بینانه؛ باید همیشه داخل player_lock صدا زده شود."""
    old_v = doc.get("_v", 0)
    doc["_v"] = old_v + 1
    result = players_col().find_one_and_update(
        {"_id": doc["_id"], "_v": old_v},
        {"$set": {k: v for k, v in doc.items() if k not in ("_id",)}},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        # یعنی بین خواندن و نوشتن یه تغییر دیگه افتاده؛ بازم ذخیره کن که دیتا گم نشه
        doc["_v"] = old_v + 1
        players_col().replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return doc
    return result


def all_players(active_only: bool = True):
    query = {}
    return list(players_col().find(query))


def all_chat_ids() -> list[int]:
    return [p["chat_id"] for p in players_col().find({}, {"chat_id": 1}) if p.get("chat_id")]


# ------------------------------------------------------------
#  لاگ ایونت‌های تاریک — فقط ادمین/گیم‌مستر می‌بیند (utils.apply_effects
#  جزئیات مکانیکی را برمی‌گرداند، اینجا فقط ذخیره‌اش می‌کنیم)
# ------------------------------------------------------------
def log_dark_event(user_id: int, event_id: str, option_key: str, dice_value, effects: dict):
    dark_log_col().insert_one({
        "user_id": user_id,
        "event_id": event_id,
        "option_key": option_key,
        "dice_value": dice_value,
        "effects": effects,
        "ts": time.time(),
    })


def get_dark_event_log(limit: int = 15, user_id: Optional[int] = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    return list(dark_log_col().find(query).sort("ts", -1).limit(limit))


# ------------------------------------------------------------
#  وضعیت کلی بازی (تقویم آکادمی، شمارنده‌ی نامه‌ها)
# ------------------------------------------------------------
def get_state() -> dict:
    doc = state_col().find_one({"_id": "world"})
    if doc is None:
        doc = {
            "_id": "world",
            "academy_day": 1,
            "last_day_advance_ts": time.time(),
            "last_letter_day_sent": 0,
            "admins": [],
        }
        state_col().insert_one(doc)
    return doc


def save_state(doc: dict):
    state_col().replace_one({"_id": "world"}, doc, upsert=True)
