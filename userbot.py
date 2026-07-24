"""
userbot.py
یوزربات (Telethon) که پشت‌صحنه گروه معامله رو می‌سازه، ربات اصلی + ادمین‌ها رو
بهش اضافه و ادمین می‌کنه، و لینک دعوت (برای خریدار/فروشنده که روش کلیک کنن) رو
برمی‌گردونه.

نکته مهم: این کار با Bot API تلگرام ممکن نیست (ربات‌ها نمی‌تونن گروه بسازن)،
به همین خاطر از یه اکانت شخصی (یوزربات، با MTProto/Telethon) استفاده می‌شه.
"""
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, InviteToChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatAdminRights

from config import (
    USERBOT_API_ID, USERBOT_API_HASH, USERBOT_SESSION,
    ADMIN_USERNAMES, DEAL_GROUP_INVITE_USAGE_LIMIT,
)

_client = TelegramClient(StringSession(USERBOT_SESSION), USERBOT_API_ID, USERBOT_API_HASH)

_ADMIN_RIGHTS = ChatAdminRights(
    change_info=True,
    post_messages=True,
    edit_messages=True,
    delete_messages=True,
    ban_users=True,
    invite_users=True,
    pin_messages=True,
    add_admins=False,
    anonymous=False,
    manage_call=True,
    other=True,
)


async def _ensure_connected():
    if not _client.is_connected():
        await _client.connect()
    if not await _client.is_user_authorized():
        raise RuntimeError(
            "یوزربات لاگین نیست - USERBOT_SESSION رو تو config.py چک کن."
        )


async def create_deal_group(title: str, bot_username: str, about: str = "") -> dict:
    """
    یه گروه (مگاگروپ) جدید می‌سازه، ربات اصلی و ادمین‌های تنظیم‌شده رو اضافه/ادمین
    می‌کنه، و یه لینک دعوت با تعداد استفاده محدود برمی‌گردونه.

    خروجی: {"chat_id": int, "invite_link": str}
    """
    await _ensure_connected()

    result = await _client(CreateChannelRequest(
        title=title,
        about=about or "گروه امن معامله - ایجاد شده خودکار",
        megagroup=True,
    ))
    channel = result.chats[0]

    to_invite_usernames = [bot_username] + [u for u in ADMIN_USERNAMES if u]
    entities = []
    for username in to_invite_usernames:
        try:
            entity = await _client.get_entity(username)
            entities.append(entity)
        except Exception:
            logging.exception("پیدا کردن کاربر %s برای اضافه به گروه ناموفق بود", username)

    if entities:
        try:
            await _client(InviteToChannelRequest(channel, entities))
        except Exception:
            logging.exception("اضافه کردن کاربران به گروه معامله ناموفق بود")

    for entity in entities:
        try:
            await _client(EditAdminRequest(channel, entity, _ADMIN_RIGHTS, "Deal Admin"))
        except Exception:
            logging.exception("ادمین کردن %s تو گروه معامله ناموفق بود", entity)

    invite = await _client(ExportChatInviteRequest(
        peer=channel,
        usage_limit=DEAL_GROUP_INVITE_USAGE_LIMIT,
    ))

    return {"chat_id": channel.id, "invite_link": invite.link}


async def shutdown():
    if _client.is_connected():
        await _client.disconnect()
