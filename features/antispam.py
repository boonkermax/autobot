"""/spam on|off|limit|window + repeated-message enforcement (warn, then ban)."""
import time
from collections import defaultdict, deque

from telegram.error import TelegramError
from telegram.ext import CommandHandler

from database import cget, cset
from utils import group_admin, mention, tmp_reply

SPAM = defaultdict(deque)
STRIKE = {}


@group_admin
async def cmd_spam(u, c):
    cid, m = u.effective_chat.id, u.effective_message
    a = [x.lower() for x in c.args]
    try:
        if a and a[0] in ("on", "off"):
            cset(cid, "spam", a[0] == "on")
        elif len(a) == 2 and a[0] == "limit" and 2 <= int(a[1]) <= 20:
            cset(cid, "spam_limit", int(a[1]))
        elif len(a) == 2 and a[0] == "window" and 5 <= int(a[1]) <= 600:
            cset(cid, "spam_window", int(a[1]))
        else:
            return await m.reply_text("/spam on|off · /spam limit <2-20> · /spam window <5-600>")
    except ValueError:
        return await m.reply_text("Number expected.")
    await m.reply_text(f"Anti-spam: {'ON' if cget(cid, 'spam', False) else 'OFF'} · limit {cget(cid, 'spam_limit', 3)} · window {cget(cid, 'spam_window', 30)}s")


async def check(u, c):
    m, us, cid = u.effective_message, u.effective_user, u.effective_chat.id
    if not cget(cid, "spam", False):
        return False
    txt = m.text or m.caption or ""
    key = (cid, us.id)
    h = hash(txt or str(type(m.effective_attachment)))
    now = time.time()
    dq = SPAM[key]
    dq.append((now, h))
    win = cget(cid, "spam_window", 30)
    while dq and now - dq[0][0] > win:
        dq.popleft()
    if sum(1 for _, x in dq if x == h) < cget(cid, "spam_limit", 3):
        return False
    dq.clear()
    s = STRIKE.get(key, 0) + 1
    STRIKE[key] = s
    try:
        await m.delete()
    except TelegramError:
        pass
    if s == 1:
        await tmp_reply(m, f"⚠️ {mention(us)}, stop spamming — next time is a ban.", 6)
        return True
    STRIKE.pop(key, None)
    try:
        await c.bot.ban_chat_member(cid, us.id)
    except TelegramError:
        pass
    await tmp_reply(m, f"🚫 {mention(us)} banned for spam.", 6)
    return True


def register(app):
    app.add_handler(CommandHandler("spam", cmd_spam))
