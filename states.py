"""
states.py
تمام state های FSM ربات (فرم‌های چندمرحله‌ای)
"""
from aiogram.fsm.state import State, StatesGroup


class ListingForm(StatesGroup):
    title = State()
    rank = State()
    legendary_skins = State()
    mythic_items = State()
    battle_pass_level = State()
    price = State()
    screenshots = State()
    auction_choice = State()
    auction_duration = State()
    confirm = State()


class BuyFlow(StatesGroup):
    choose_insurance = State()
    confirm_purchase = State()


class AuctionBidFlow(StatesGroup):
    enter_amount = State()


class DisputeFlow(StatesGroup):
    enter_reason = State()
    upload_evidence = State()


class AdminResolveFlow(StatesGroup):
    enter_dispute_id = State()
    enter_decision = State()


class VerificationFlow(StatesGroup):
    upload_video = State()
    upload_screenshots = State()


class DealFlow(StatesGroup):
    """فلوی محاوره‌ای معامله: نقش -> قیمت -> توضیح -> (بعد از تأیید دو طرف) مدرک"""
    choose_role = State()
    enter_price = State()
    enter_description = State()
    enter_proof = State()


class AdminManualGroupFlow(StatesGroup):
    """وقتی ساخت خودکار گروه ناموفق بود، ادمین گروه رو دستی می‌سازه و لینکش رو اینجا وارد می‌کنه."""
    enter_link = State()
