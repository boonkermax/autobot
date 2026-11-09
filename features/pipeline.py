"""Group message pipeline: runs each feature's check() in order."""
from telegram.ext import MessageHandler, filters

from utils import is_admin, remember
from . import locks, blacklist, chat_settings, antispam, report, notes, autoreply

# enforcement — non-admins only
ENFORCE = (locks.check, blacklist.check, chat_settings.check_slowmode, antispam.check)
# responders — everyone
RESPOND = (report.check, notes.check, autoreply.check)


async def on_group_msg(u, c):
    m, ch, us = u.effective_message, u.effective_chat, u.effective_user
    if not m or not us or (m.text and m.text.startswith("/")):
        return
    remember(us)
    if not await is_admin(c.bot, ch.id, us.id):
        for chk in ENFORCE:
            if await chk(u, c):
                return
    for chk in RESPOND:
        if await chk(u, c):
            return


def register(app):
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL, on_group_msg), group=1)
