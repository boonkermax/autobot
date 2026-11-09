"""/lock /unlock /locks + enforcement."""
import re

from telegram.error import TelegramError
from telegram.ext import CommandHandler

from database import cget, cset
from utils import group_admin, mention, tmp_reply

LOCKS = ["all", "button", "emoji", "forward", "url", "username"]
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F000-\U0001F2FF]")
URL_RE = re.compile(r"(https?://|www\.|t\.me/|\b\w+\.(com|net|org|io|me|in|co|xyz)\b)", re.I)


def violates(m, locks):
    txt = m.text or m.caption or ""
    ents = list(m.entities or []) + list(m.caption_entities or [])
    if "all" in locks:
        return "all"
    if "button" in locks and m.reply_markup and getattr(m.reply_markup, "inline_keyboard", None):
        return "button"
    if "emoji" in locks and (EMOJI_RE.search(txt) or any(e.type == "custom_emoji" for e in ents)):
        return "emoji"
    if "forward" in locks and m.forward_origin:
        return "forward"
    if "url" in locks and (URL_RE.search(txt) or any(e.type in ("url", "text_link") for e in ents)):
        return "url"
    if "username" in locks and (re.search(r"@\w{4,}", txt) or any(e.type == "mention" for e in ents)):
        return "username"


@group_admin
async def cmd_lock(u, c):
    cid = u.effective_chat.id
    t = c.args[0].lower() if c.args else ""
    if t not in LOCKS:
        return await u.effective_message.reply_text("Types: " + ", ".join(LOCKS))
    cur = set(cget(cid, "locks", []))
    cur.add(t)
    cset(cid, "locks", sorted(cur))
    await u.effective_message.reply_text(f"🔒 Locked: {t}")


@group_admin
async def cmd_unlock(u, c):
    cid = u.effective_chat.id
    t = c.args[0].lower() if c.args else ""
    cur = set(cget(cid, "locks", []))
    cur.discard(t)
    cset(cid, "locks", sorted(cur))
    await u.effective_message.reply_text(f"🔓 Unlocked: {t}")


@group_admin
async def cmd_locks(u, c):
    cur = cget(u.effective_chat.id, "locks", [])
    await u.effective_message.reply_text("\n".join(f"{'🔒' if t in cur else '🔓'} {t}" for t in LOCKS))


async def check(u, c):
    """Return True if message was handled (deleted)."""
    m, us = u.effective_message, u.effective_user
    locks = cget(u.effective_chat.id, "locks", [])
    v = violates(m, locks) if locks else None
    if not v:
        return False
    try:
        await m.delete()
    except TelegramError:
        pass
    await tmp_reply(m, f"🔒 {mention(us)}, <b>{v}</b> is locked here.", 4)
    return True


def register(app):
    app.add_handler(CommandHandler("lock", cmd_lock))
    app.add_handler(CommandHandler("unlock", cmd_unlock))
    app.add_handler(CommandHandler("locks", cmd_locks))
