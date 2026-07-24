"""
database.py
لایه دسترسی به MongoDB (با motor - نسخه async)
تمام کالکشن‌ها و عملیات اتمیک (read-modify-write امن) اینجا تعریف شدن.
"""
import time
import random
import string
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME, TRUST_SCORE_START

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
listings_col = db["listings"]
escrow_col = db["escrow_transactions"]
disputes_col = db["disputes"]
fingerprints_col = db["banned_fingerprints"]
referrals_col = db["referrals"]
bids_col = db["auction_bids"]
deals_col = db["deals"]


def _gen_code(length=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---------------- USERS ----------------
async def get_or_create_user(user_id: int, username: str = None):
    user = await users_col.find_one({"_id": user_id})
    if user:
        return user
    ref_code = _gen_code()
    new_user = {
        "_id": user_id,
        "username": username,
        "balance": 0,
        "trust_score": TRUST_SCORE_START,
        "vip_tier": None,
        "vip_expires_at": None,
        "referral_code": ref_code,
        "referred_by": None,
        "total_sales": 0,
        "total_purchases": 0,
        "banned": False,
        "created_at": time.time(),
    }
    await users_col.insert_one(new_user)
    return new_user


async def update_trust_score(user_id: int, delta: int):
    await users_col.update_one({"_id": user_id}, {"$inc": {"trust_score": delta}})
    user = await users_col.find_one({"_id": user_id})
    return user["trust_score"] if user else None


async def is_vip(user_id: int) -> bool:
    user = await users_col.find_one({"_id": user_id})
    if not user or not user.get("vip_tier"):
        return False
    if user.get("vip_expires_at") and user["vip_expires_at"] < time.time():
        return False
    return True


async def adjust_balance(user_id: int, amount: float):
    """مقدار مثبت = افزایش موجودی، مقدار منفی = کاهش. عملیات اتمیک است."""
    result = await users_col.find_one_and_update(
        {"_id": user_id},
        {"$inc": {"balance": amount}},
        return_document=True,
    )
    return result


async def has_sufficient_balance(user_id: int, amount: float) -> bool:
    user = await users_col.find_one({"_id": user_id})
    return bool(user and user.get("balance", 0) >= amount)


# ---------------- LISTINGS ----------------
async def create_listing(seller_id: int, data: dict) -> str:
    listing_id = _gen_code(8)
    doc = {
        "_id": listing_id,
        "seller_id": seller_id,
        "title": data.get("title"),
        "rank": data.get("rank"),
        "legendary_skins": data.get("legendary_skins", 0),
        "mythic_items": data.get("mythic_items", 0),
        "battle_pass_level": data.get("battle_pass_level", 0),
        "price": data.get("price"),
        "account_score": data.get("account_score", 0),
        "verified": data.get("verified", False),
        "screenshots": data.get("screenshots", []),
        "status": "active",   # active | pending | sold | removed
        "is_auction": data.get("is_auction", False),
        "auction_end_at": data.get("auction_end_at"),
        "current_bid": data.get("price") if data.get("is_auction") else None,
        "current_bidder": None,
        "created_at": time.time(),
    }
    await listings_col.insert_one(doc)
    return listing_id


async def get_listing(listing_id: str):
    return await listings_col.find_one({"_id": listing_id})


async def search_listings(filters: dict, limit: int = 10):
    query = {"status": "active"}
    if filters.get("rank"):
        query["rank"] = filters["rank"]
    if filters.get("max_price"):
        query["price"] = {"$lte": filters["max_price"]}
    if filters.get("verified_only"):
        query["verified"] = True
    cursor = listings_col.find(query).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def set_listing_status(listing_id: str, status: str):
    await listings_col.update_one({"_id": listing_id}, {"$set": {"status": status}})


async def place_bid_atomic(listing_id: str, bidder_id: int, amount: float) -> bool:
    """
    ثبت اتمیک پیشنهاد مزایده. فقط وقتی موفقه که پیشنهاد جدید واقعا از
    current_bid بالاتر باشه؛ جلوگیری از race condition دو پیشنهاد همزمان.
    """
    result = await listings_col.find_one_and_update(
        {"_id": listing_id, "is_auction": True, "current_bid": {"$lt": amount}},
        {"$set": {"current_bid": amount, "current_bidder": bidder_id}},
        return_document=True,
    )
    if result:
        await bids_col.insert_one({
            "listing_id": listing_id,
            "bidder_id": bidder_id,
            "amount": amount,
            "created_at": time.time(),
        })
        return True
    return False


# ---------------- ESCROW / VAULT ----------------
async def create_escrow(listing_id: str, buyer_id: int, seller_id: int,
                         amount: float, countdown_end: float, insured: bool = False) -> str:
    tx_id = _gen_code(10)
    doc = {
        "_id": tx_id,
        "listing_id": listing_id,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "amount": amount,
        "status": "locked",  # locked | released | refunded | disputed
        "insured": insured,
        "countdown_end": countdown_end,
        "delivered_at": None,
        "created_at": time.time(),
    }
    await escrow_col.insert_one(doc)
    return tx_id


async def get_escrow(tx_id: str):
    return await escrow_col.find_one({"_id": tx_id})


async def update_escrow_status(tx_id: str, status: str, **extra):
    update = {"status": status}
    update.update(extra)
    await escrow_col.update_one({"_id": tx_id}, {"$set": update})


# ---------------- DISPUTES ----------------
async def open_dispute(tx_id: str, opener_id: int, reason: str) -> str:
    dispute_id = _gen_code(8)
    doc = {
        "_id": dispute_id,
        "tx_id": tx_id,
        "opener_id": opener_id,
        "reason": reason,
        "buyer_evidence": [],
        "seller_evidence": [],
        "status": "open",  # open | resolved_buyer | resolved_seller
        "created_at": time.time(),
    }
    await disputes_col.insert_one(doc)
    await escrow_col.update_one({"_id": tx_id}, {"$set": {"status": "disputed"}})
    return dispute_id


async def add_dispute_evidence(dispute_id: str, side: str, file_id: str):
    field = "buyer_evidence" if side == "buyer" else "seller_evidence"
    await disputes_col.update_one({"_id": dispute_id}, {"$push": {field: file_id}})


async def resolve_dispute(dispute_id: str, resolution: str):
    await disputes_col.update_one({"_id": dispute_id}, {"$set": {"status": resolution}})


# ---------------- ANTI-SCAM FINGERPRINTING ----------------
async def record_ban_fingerprint(user_id: int, device_fingerprint: str, reason: str):
    await fingerprints_col.insert_one({
        "user_id": user_id,
        "fingerprint": device_fingerprint,
        "reason": reason,
        "created_at": time.time(),
    })
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": True}})


async def is_fingerprint_flagged(device_fingerprint: str) -> bool:
    doc = await fingerprints_col.find_one({"fingerprint": device_fingerprint})
    return doc is not None


# ---------------- REFERRAL ----------------
async def link_referral(new_user_id: int, referrer_code: str) -> bool:
    referrer = await users_col.find_one({"referral_code": referrer_code})
    if not referrer or referrer["_id"] == new_user_id:
        return False
    await users_col.update_one({"_id": new_user_id}, {"$set": {"referred_by": referrer["_id"]}})
    return True


async def pay_referral_commission(user_id: int, commission_amount: float):
    user = await users_col.find_one({"_id": user_id})
    if user and user.get("referred_by"):
        await adjust_balance(user["referred_by"], commission_amount)
        await referrals_col.insert_one({
            "referrer_id": user["referred_by"],
            "from_user": user_id,
            "amount": commission_amount,
            "created_at": time.time(),
        })


# ---------------- آمار / پنل مدیریتی (استفاده مشترک پنل داخل ربات و پنل وب) ----------------
async def get_dashboard_stats() -> dict:
    """آمار کلی برای داشبورد؛ هم پنل تلگرام و هم پنل وب از این استفاده می‌کنن."""
    total_users = await users_col.count_documents({})
    banned_users = await users_col.count_documents({"banned": True})
    vip_users = await users_col.count_documents({"vip_tier": {"$ne": None}})

    total_listings = await listings_col.count_documents({})
    active_listings = await listings_col.count_documents({"status": "active"})
    sold_listings = await listings_col.count_documents({"status": "sold"})
    auction_listings = await listings_col.count_documents({"is_auction": True, "status": "active"})

    locked_tx = await escrow_col.count_documents({"status": "locked"})
    released_tx = await escrow_col.count_documents({"status": "released"})
    disputed_tx = await escrow_col.count_documents({"status": "disputed"})
    refunded_tx = await escrow_col.count_documents({"status": "refunded"})

    open_disputes = await disputes_col.count_documents({"status": "open"})

    volume_pipeline = [
        {"$match": {"status": "released"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    volume_result = [doc async for doc in escrow_col.aggregate(volume_pipeline)]
    total_volume = volume_result[0]["total"] if volume_result else 0

    return {
        "total_users": total_users,
        "banned_users": banned_users,
        "vip_users": vip_users,
        "total_listings": total_listings,
        "active_listings": active_listings,
        "sold_listings": sold_listings,
        "auction_listings": auction_listings,
        "locked_tx": locked_tx,
        "released_tx": released_tx,
        "disputed_tx": disputed_tx,
        "refunded_tx": refunded_tx,
        "open_disputes": open_disputes,
        "total_volume": total_volume,
    }


async def search_user(query: str):
    """جستجوی کاربر با آیدی عددی یا بخشی از یوزرنیم."""
    if query.isdigit():
        return await users_col.find_one({"_id": int(query)})
    return await users_col.find_one({"username": {"$regex": query, "$options": "i"}})


async def set_user_banned(user_id: int, banned: bool):
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": banned}})


async def set_user_balance(user_id: int, new_balance: float):
    await users_col.update_one({"_id": user_id}, {"$set": {"balance": new_balance}})


async def get_recent_transactions(limit: int = 15):
    cursor = escrow_col.find({}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_recent_listings(limit: int = 15, status: str = None):
    query = {"status": status} if status else {}
    cursor = listings_col.find(query).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_open_disputes(limit: int = 15):
    cursor = disputes_col.find({"status": "open"}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def get_all_active_user_ids():
    cursor = users_col.find({"banned": False}, {"_id": 1})
    return [doc["_id"] async for doc in cursor]


async def force_remove_listing(listing_id: str):
    await listings_col.update_one({"_id": listing_id}, {"$set": {"status": "removed"}})


# ---------------- DEALS (فلوی محاوره‌ای معامله - جایگزین پنل آگهی) ----------------
async def create_deal(initiator_id: int, initiator_username: str, initiator_role: str,
                       price: int, description: str) -> str:
    deal_id = _gen_code(8)
    doc = {
        "_id": deal_id,
        "initiator_id": initiator_id,
        "initiator_username": initiator_username,
        "initiator_role": initiator_role,  # "buyer" | "seller"
        "counterparty_id": None,
        "counterparty_username": None,
        "counterparty_role": None,
        "price": price,
        "description": description,
        "initiator_confirmed": False,
        "counterparty_confirmed": False,
        "initiator_proof": None,
        "counterparty_proof": None,
        "initiator_admin_approved": False,
        "counterparty_admin_approved": False,
        "status": "awaiting_counterparty",
        "chat_id": None,
        "invite_link": None,
        "created_at": time.time(),
    }
    await deals_col.insert_one(doc)
    return deal_id


async def get_deal(deal_id: str):
    return await deals_col.find_one({"_id": deal_id})


async def set_deal_counterparty(deal_id: str, user_id: int, username: str, role: str):
    await deals_col.update_one(
        {"_id": deal_id},
        {"$set": {
            "counterparty_id": user_id,
            "counterparty_username": username,
            "counterparty_role": role,
            "status": "awaiting_confirmation",
        }},
    )


async def set_deal_confirmed(deal_id: str, side: str):
    field = "initiator_confirmed" if side == "initiator" else "counterparty_confirmed"
    await deals_col.update_one({"_id": deal_id}, {"$set": {field: True}})


async def set_deal_proof(deal_id: str, side: str, file_id: str):
    field = "initiator_proof" if side == "initiator" else "counterparty_proof"
    await deals_col.update_one(
        {"_id": deal_id},
        {"$set": {field: file_id, "status": "awaiting_admin"}},
    )


async def set_deal_admin_approval(deal_id: str, side: str, approved: bool):
    field = "initiator_admin_approved" if side == "initiator" else "counterparty_admin_approved"
    await deals_col.update_one({"_id": deal_id}, {"$set": {field: approved}})


async def set_deal_status(deal_id: str, status: str):
    await deals_col.update_one({"_id": deal_id}, {"$set": {"status": status}})


async def set_deal_group(deal_id: str, chat_id: int, invite_link: str):
    await deals_col.update_one(
        {"_id": deal_id},
        {"$set": {"chat_id": chat_id, "invite_link": invite_link}},
    )


async def find_active_deal_for_user(user_id: int):
    """آخرین معامله‌ی هنوز بازِ کاربر (برای پیدا کردن معامله وقتی مدرک می‌فرسته)."""
    cursor = deals_col.find({
        "$or": [{"initiator_id": user_id}, {"counterparty_id": user_id}],
        "status": {"$nin": ["rejected", "group_created"]},
    }).sort("created_at", -1).limit(1)
    docs = [doc async for doc in cursor]
    return docs[0] if docs else None
