import asyncio
import functools
import html
import re
import time
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.error import TelegramError

from config import OWNER_ID
from database import q, one, cget, cset

_adm = {}  # chat_id -> (timestamp, {user_id: ChatMember})


async def admin_map(bot, chat_id):
    t, m = _adm.get(chat_id, (0, {}))
    if time.time() - t > 60:
        try:
            m = {a.user.id: a for a in await bot.get_chat_administrators(chat_id)}
        except TelegramError:
            m = {}
        _adm[chat_id] = (time.time(), m)
    return m


def clear_admin_cache(chat_id):
    _adm.pop(chat_id, None)


async def is_admin(bot, chat_id, uid):
    return uid == OWNER_ID or uid in await admin_map(bot, chat_id)


def mention(u):
    return f'<a href="tg://user?id={u.id}">{html.escape(u.first_name or "user")}</a>'


def remember(u):
    if u and not u.is_bot:
        q("insert into users values(?,?,?) on conflict(user_id) do update set username=excluded.username, first_name=excluded.first_name",
          u.id, (u.username or "").lower(), u.first_name)


def group_admin(f):
    @functools.wraps(f)
    async def w(u: Update, c):
        ch, m = u.effective_chat, u.effective_message
        if ch.type == ChatType.PRIVATE:
            return await m.reply_text("Use this command inside a group.")
        if not await is_admin(c.bot, ch.id, u.effective_user.id):
            return await m.reply_text("⛔ Admins only.")
        return await f(u, c)
    return w


def toggler(key, label, default=True):
    """Generic `/cmd on|off` admin command backed by the cfg table."""
    @group_admin
    async def f(u, c):
        cid = u.effective_chat.id
        if c.args and c.args[0].lower() in ("on", "off"):
            cset(cid, key, c.args[0].lower() == "on")
        await u.effective_message.reply_text(f"{label}: {'ON' if cget(cid, key, default) else 'OFF'}")
    return f


def uid_of(t):
    return t.id if hasattr(t, "id") else t


async def target(u, c):
    """Resolve (user_or_id, remaining_args) from reply, @username (seen users) or numeric ID."""
    m = u.effective_message
    args = list(c.args)
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user, args
    if args:
        a = args[0]
        if a.lstrip("-").isdigit():
            return int(a), args[1:]
        if a.startswith("@"):
            r = one("select user_id from users where username=?", a[1:].lower())
            if r:
                return r["user_id"], args[1:]
    return None, args


def parse_dur(s):
    mt = re.fullmatch(r"(\d+)([mhdw])", s or "")
    if not mt:
        return None
    unit = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}[mt[2]]
    return datetime.now(timezone.utc) + timedelta(**{unit: int(mt[1])})


async def tmp_reply(m, text, secs=5):
    r = await m.chat.send_message(text, parse_mode=ParseMode.HTML)

    async def _d():
        await asyncio.sleep(secs)
        try:
            await r.delete()
        except TelegramError:
            pass
    asyncio.create_task(_d())


def register_chat(chat, session_user=None):
    q("insert into chats(chat_id,title,type,session_user) values(?,?,?,?) on conflict(chat_id) do update set title=excluded.title, type=excluded.type",
      chat.id, chat.title, chat.type, session_user)
    if session_user and one("select session_user from chats where chat_id=?", chat.id)["session_user"] is None:
        q("update chats set session_user=? where chat_id=?", session_user, chat.id)
