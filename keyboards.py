"""
keyboards.py
تمام کیبوردهای inline ربات
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ACCOUNT_RANKS


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🤝 شروع معامله جدید", callback_data="start_new_deal")
    kb.button(text="📢 آگهی اکانت", callback_data="new_listing")
    kb.button(text="🏆 لیدربورد اعتماد", callback_data="trust_leaderboard")
    kb.button(text="👑 اشتراک VIP", callback_data="vip_menu")
    kb.button(text="🔗 لینک رفرال من", callback_data="my_referral")
    kb.button(text="🆘 پشتیبانی / اختلاف", callback_data="support_menu")
    kb.adjust(1, 1, 2, 2)
    return kb.as_markup()


def listing_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ ثبت نهایی", callback_data="listing_confirm_yes")
    kb.button(text="❌ لغو آگهی", callback_data="listing_confirm_no")
    kb.adjust(2)
    return kb.as_markup()


def deal_role_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 خریدارم", callback_data="deal_role_buyer")
    kb.button(text="💰 فروشنده‌ام", callback_data="deal_role_seller")
    kb.adjust(2)
    return kb.as_markup()


def deal_confirm_kb(deal_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تأیید می‌کنم", callback_data=f"deal_confirm_{deal_id}")
    kb.button(text="❌ رد می‌کنم", callback_data=f"deal_cancel_{deal_id}")
    kb.adjust(2)
    return kb.as_markup()


def deal_admin_review_kb(deal_id: str, side: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تأیید مدرک", callback_data=f"deal_admin_ok_{deal_id}_{side}")
    kb.button(text="❌ رد مدرک", callback_data=f"deal_admin_no_{deal_id}_{side}")
    kb.adjust(2)
    return kb.as_markup()


def deal_join_group_kb(invite_link: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 ورود به گروه معامله", url=invite_link)
    kb.adjust(1)
    return kb.as_markup()


def rank_select_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for rank in ACCOUNT_RANKS:
        kb.button(text=rank, callback_data=f"rank_{rank}")
    kb.adjust(2)
    return kb.as_markup()


def yes_no_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ بله", callback_data=yes_cb)
    kb.button(text="❌ خیر", callback_data=no_cb)
    kb.adjust(2)
    return kb.as_markup()


def listing_actions_kb(listing_id: str, is_auction: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if is_auction:
        kb.button(text="💰 ثبت پیشنهاد قیمت", callback_data=f"bid_{listing_id}")
    else:
        kb.button(text="🛍 خرید این اکانت", callback_data=f"buy_{listing_id}")
    kb.button(text="🔍 جزئیات بیشتر", callback_data=f"details_{listing_id}")
    kb.adjust(1)
    return kb.as_markup()


def insurance_choice_kb(tx_ref: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛡 با بیمه معامله", callback_data=f"insure_yes_{tx_ref}")
    kb.button(text="🚫 بدون بیمه", callback_data=f"insure_no_{tx_ref}")
    kb.adjust(1)
    return kb.as_markup()


def escrow_actions_kb(tx_id: str, for_buyer: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if for_buyer:
        kb.button(text="✅ تحویل گرفتم، تأیید نهایی", callback_data=f"confirm_delivery_{tx_id}")
        kb.button(text="⚠️ مشکل دارم / اختلاف", callback_data=f"dispute_{tx_id}")
    kb.adjust(1)
    return kb.as_markup()


def admin_dispute_kb(dispute_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👍 به نفع خریدار", callback_data=f"resolve_buyer_{dispute_id}")
    kb.button(text="👎 به نفع فروشنده", callback_data=f"resolve_seller_{dispute_id}")
    kb.adjust(1)
    return kb.as_markup()


def kyc_request_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🪪 درخواست احراز هویت", callback_data="kyc_request")
    kb.adjust(1)
    return kb.as_markup()


def admin_kyc_review_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ تأیید احراز هویت", callback_data=f"kyc_approve_{user_id}")
    kb.button(text="❌ رد درخواست", callback_data=f"kyc_reject_{user_id}")
    kb.adjust(1)
    return kb.as_markup()


def filter_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎖 فیلتر رنک", callback_data="filter_rank")
    kb.button(text="💵 فیلتر قیمت", callback_data="filter_price")
    kb.button(text="✅ فقط تأییدشده‌ها", callback_data="filter_verified")
    kb.button(text="📋 نمایش همه", callback_data="filter_all")
    kb.adjust(2)
    return kb.as_markup()
