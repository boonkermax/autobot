"""/accept, instant auto-approve, chat registration when bot is added/removed."""
import logging
import re

from telegram.error import TelegramError
from telegram.ext import CommandHandler, ChatJoinRequestHandler, ChatMemberHandler
from telethon.errors import FloodWaitError

from database import q, one, cget, cset
from services.userbot import tl_client, approve_all
from utils import is_admin, register_chat, clear_admin_cache, toggler

log = logging.getLogger(__name__)


async def cmd_accept(u, c):
    m, us = u.effective_message, u.effective_user
    if not c.args or not re.fullmatch(r"-?\d+", c.args[0]):
        return await m.reply_text("Usage: /accept <chat_id>")
    chat_id = int(c.args[0])
    if not await is_admin(c.bot, chat_id, us.id):
        return await m.reply_text("⛔ You must be an admin of that chat (and the bot must be in it).")
    cl = await tl_client(us.id)
    if not cl:
        return await m.reply_text("Login first with /login (private chat).")
    note = await m.reply_text("⏳ Approving pending requests…")
    try:
        found, ok = await approve_all(cl, chat_id)
        try:
            register_chat(await c.bot.get_chat(chat_id), us.id)
        except TelegramError:
            pass
        q("update chats set session_user=? where chat_id=?", us.id, chat_id)
        cset(chat_id, "total_approved", cget(chat_id, "total_approved", 0) + ok)
        await note.edit_text(f"✅ Pending found: {found}\nApproved: {ok}")
    except FloodWaitError as e:
        await note.edit_text(f"Flood wait, retry in {e.seconds}s.")
    except Exception as e:
        await note.edit_text(f"❌ {e}")
    finally:
        await cl.disconnect()


async def on_join_request(u, c):
    r = u.chat_join_request
    if not cget(r.chat.id, "autoapprove", True):
        return
    try:
        await r.approve()
        cset(r.chat.id, "total_approved", cget(r.chat.id, "total_approved", 0) + 1)
    except TelegramError as e:
        log.warning("approve fail %s", e)


async def on_my_chat_member(u, c):
    ev = u.my_chat_member
    new = ev.new_chat_member.status
    if new in ("administrator", "member"):
        has = one("select 1 from sessions where user_id=?", ev.from_user.id)
        register_chat(ev.chat, ev.from_user.id if has else None)
        clear_admin_cache(ev.chat.id)
    elif new in ("left", "kicked"):
        q("delete from chats where chat_id=?", ev.chat.id)


def register(app):
    app.add_handler(CommandHandler("accept", cmd_accept))
    app.add_handler(CommandHandler("autoapprove", toggler("autoapprove", "Auto-approve")))
    app.add_handler(ChatJoinRequestHandler(on_join_request))
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
