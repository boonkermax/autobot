"""/welcome /setwelcome /resetwelcome + new-member greeting."""
import html

from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, MessageHandler, filters

from database import cget, cset
from utils import group_admin, mention, toggler


@group_admin
async def cmd_setwelcome(u, c):
    parts = u.effective_message.text.split(None, 1)
    if len(parts) < 2:
        return await u.effective_message.reply_text("Usage: /setwelcome <text> — {mention} {first} {chat} {id} {count}")
    cset(u.effective_chat.id, "welcome_text", parts[1])
    cset(u.effective_chat.id, "welcome", True)
    await u.effective_message.reply_text("✅ Welcome message set.")


@group_admin
async def cmd_resetwelcome(u, c):
    cset(u.effective_chat.id, "welcome_text", None)
    await u.effective_message.reply_text("✅ Welcome reset to default.")


async def on_new_members(u, c):
    ch, m = u.effective_chat, u.effective_message
    if cget(ch.id, "cleanservice", False):
        try:
            await m.delete()
        except TelegramError:
            pass
    if not cget(ch.id, "welcome", False):
        return
    tpl = cget(ch.id, "welcome_text") or "Welcome {mention} to {chat}! 🎉"
    try:
        count = await c.bot.get_chat_member_count(ch.id)
    except TelegramError:
        count = "?"
    for us in m.new_chat_members:
        if us.is_bot:
            continue
        txt = (tpl.replace("{mention}", mention(us)).replace("{first}", html.escape(us.first_name or ""))
               .replace("{chat}", html.escape(ch.title or "")).replace("{id}", str(us.id)).replace("{count}", str(count)))
        try:
            await c.bot.send_message(ch.id, txt, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass


def register(app):
    app.add_handler(CommandHandler("welcome", toggler("welcome", "Welcome", False)))
    app.add_handler(CommandHandler("setwelcome", cmd_setwelcome))
    app.add_handler(CommandHandler("resetwelcome", cmd_resetwelcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS & filters.ChatType.GROUPS, on_new_members))
