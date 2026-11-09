"""/addblacklist /rmblacklist /blacklist + enforcement (delete + warn)."""
import html
import re

from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler

from database import q, rows
from utils import group_admin, tmp_reply
from .warns import do_warn


@group_admin
async def cmd_addbl(u, c):
    w = " ".join(c.args).lower()
    if not w:
        return await u.effective_message.reply_text("Usage: /addblacklist <word>")
    q("insert or ignore into bl values(?,?)", u.effective_chat.id, w)
    await u.effective_message.reply_text("✅ Added.")


@group_admin
async def cmd_rmbl(u, c):
    q("delete from bl where chat=? and word=?", u.effective_chat.id, " ".join(c.args).lower())
    await u.effective_message.reply_text("✅ Removed.")


async def cmd_bl(u, c):
    w = [r["word"] for r in rows("select word from bl where chat=?", u.effective_chat.id)]
    await u.effective_message.reply_text(
        "🚫 Blacklist:\n" + "\n".join(f"• {html.escape(x)}" for x in w) if w else "Blacklist empty.",
        parse_mode=ParseMode.HTML)


async def check(u, c):
    m, cid = u.effective_message, u.effective_chat.id
    txt = (m.text or m.caption or "").lower()
    if not txt:
        return False
    words = [r["word"] for r in rows("select word from bl where chat=?", cid)]
    if not any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", txt) for w in words):
        return False
    try:
        await m.delete()
    except TelegramError:
        pass
    await tmp_reply(m, await do_warn(c.bot, cid, u.effective_user, "Blacklisted word."), 6)
    return True


def register(app):
    app.add_handler(CommandHandler("addblacklist", cmd_addbl))
    app.add_handler(CommandHandler("rmblacklist", cmd_rmbl))
    app.add_handler(CommandHandler("blacklist", cmd_bl))
