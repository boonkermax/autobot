"""/login /logout /cancel — Telegram user-session login (stored encrypted)."""
import re

from telegram.constants import ChatType, ParseMode
from telegram.ext import CommandHandler, MessageHandler, filters
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, PasswordHashInvalidError
from telegram.error import TelegramError

import logging
from config import API_ID, API_HASH, FERNET
from database import q

log = logging.getLogger(__name__)
LOGIN = {}  # user_id -> {"stage", "client", "phone", "hash"}


async def cmd_login(u, c):
    m = u.effective_message
    if u.effective_chat.type != ChatType.PRIVATE:
        return await m.reply_text("Use /login in private chat.")
    LOGIN[u.effective_user.id] = {"stage": "phone"}
    await m.reply_text(
        "🔐 <b>Login</b>\n\nYour session is stored <b>encrypted</b> on this bot's server and is used only to list/approve "
        "pending join requests and scan members of chats you admin. Use /logout anytime to delete it. "
        "Only continue if you trust whoever hosts this bot.\n\n"
        "Send your phone number with country code (e.g. <code>+919XXXXXXXXX</code>). /cancel to abort.",
        parse_mode=ParseMode.HTML)


async def cmd_cancel(u, c):
    st = LOGIN.pop(u.effective_user.id, None)
    if st and st.get("client"):
        await st["client"].disconnect()
    await u.effective_message.reply_text("Cancelled.")


async def cmd_logout(u, c):
    q("delete from sessions where user_id=?", u.effective_user.id)
    q("update chats set session_user=null where session_user=?", u.effective_user.id)
    await u.effective_message.reply_text("✅ Session removed. Also terminate it in Telegram → Settings → Devices.")


async def private_text(u, c):
    uid = u.effective_user.id
    st = LOGIN.get(uid)
    if not st:
        return
    m = u.effective_message
    txt = m.text.strip()
    try:
        if st["stage"] == "phone":
            cl = TelegramClient(StringSession(), API_ID, API_HASH)
            await cl.connect()
            sent = await cl.send_code_request(txt)
            st.update(stage="code", client=cl, phone=txt, hash=sent.phone_code_hash)
            return await m.reply_text("📩 Code sent. Send it with spaces/dashes between digits (e.g. <code>1 2 3 4 5</code>) — plain digits get invalidated by Telegram.",
                                      parse_mode=ParseMode.HTML)
        cl = st["client"]
        if st["stage"] == "code":
            try:
                await cl.sign_in(st["phone"], re.sub(r"\D", "", txt), phone_code_hash=st["hash"])
            except SessionPasswordNeededError:
                st["stage"] = "pw"
                return await m.reply_text("🔑 2-step password?")
        elif st["stage"] == "pw":
            await cl.sign_in(password=txt)
            try:
                await m.delete()
            except TelegramError:
                pass
        data = FERNET.encrypt(cl.session.save().encode())
        q("insert into sessions values(?,?) on conflict(user_id) do update set data=excluded.data", uid, data)
        await cl.disconnect()
        LOGIN.pop(uid, None)
        await m.reply_text("✅ Logged in. Add me to your chat as admin, then run /accept &lt;chat_id&gt;.", parse_mode=ParseMode.HTML)
    except (PhoneCodeInvalidError, PhoneCodeExpiredError, PasswordHashInvalidError) as e:
        await m.reply_text(f"❌ {type(e).__name__}. Try again or /cancel.")
    except Exception as e:
        log.exception("login")
        if st.get("client"):
            await st["client"].disconnect()
        LOGIN.pop(uid, None)
        await m.reply_text(f"❌ Login failed: {e}\nStart again with /login.")


def register(app):
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, private_text))
