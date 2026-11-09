"""/rules /setrules /clearrules"""
import html

from telegram.constants import ParseMode
from telegram.ext import CommandHandler

from database import cget, cset
from utils import group_admin


@group_admin
async def cmd_setrules(u, c):
    m = u.effective_message
    parts = m.text.split(None, 1)
    if m.reply_to_message and m.reply_to_message.text:
        txt = m.reply_to_message.text_html
    else:
        txt = html.escape(parts[1]) if len(parts) > 1 else ""
    if not txt:
        return await m.reply_text("Usage: /setrules <text> or reply to a message.")
    cset(u.effective_chat.id, "rules", txt)
    await m.reply_text("✅ Rules saved.")


async def cmd_rules(u, c):
    await u.effective_message.reply_text(cget(u.effective_chat.id, "rules") or "No rules set.", parse_mode=ParseMode.HTML)


@group_admin
async def cmd_clearrules(u, c):
    cset(u.effective_chat.id, "rules", None)
    await u.effective_message.reply_text("✅ Rules cleared.")


def register(app):
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("setrules", cmd_setrules))
    app.add_handler(CommandHandler("clearrules", cmd_clearrules))
