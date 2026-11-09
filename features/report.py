"""/report and @admin — ping chat admins."""
import re

from telegram.constants import ParseMode
from telegram.ext import CommandHandler

from utils import admin_map


async def cmd_report(u, c):
    a = await admin_map(c.bot, u.effective_chat.id)
    ping = "".join(f'<a href="tg://user?id={i}">\u200b</a>' for i, x in a.items() if not x.user.is_bot)
    await u.effective_message.reply_text("🚨 Reported to admins." + ping, parse_mode=ParseMode.HTML)


async def check(u, c):
    txt = u.effective_message.text or u.effective_message.caption or ""
    if re.search(r"(?i)(^|\s)@admin\b", txt):
        await cmd_report(u, c)
        return True
    return False


def register(app):
    app.add_handler(CommandHandler("report", cmd_report))
