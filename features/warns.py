"""/warn /unwarn /warns /resetwarns + shared do_warn()."""
import html

from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler

from config import WARN_LIMIT
from database import q, one
from utils import group_admin, is_admin, target, uid_of


async def do_warn(bot, chat_id, user, reason=""):
    uid = uid_of(user)
    q("insert into warns values(?,?,1) on conflict(chat,user) do update set n=n+1", chat_id, uid)
    n = one("select n from warns where chat=? and user=?", chat_id, uid)["n"]
    who = f'<a href="tg://user?id={uid}">user</a>'
    if n >= WARN_LIMIT:
        q("delete from warns where chat=? and user=?", chat_id, uid)
        try:
            await bot.ban_chat_member(chat_id, uid)
        except TelegramError:
            pass
        return f"🚫 {who} reached {WARN_LIMIT}/{WARN_LIMIT} warnings and was banned."
    return f"⚠️ {who} warned ({n}/{WARN_LIMIT}). {html.escape(reason)}"


@group_admin
async def cmd_warn(u, c):
    t, args = await target(u, c)
    m = u.effective_message
    if not t:
        return await m.reply_text("Reply to a user, or pass @user / ID.")
    if await is_admin(c.bot, u.effective_chat.id, uid_of(t)):
        return await m.reply_text("Can't warn an admin.")
    await m.reply_text(await do_warn(c.bot, u.effective_chat.id, t, " ".join(args)), parse_mode=ParseMode.HTML)


@group_admin
async def cmd_unwarn(u, c):
    t, _ = await target(u, c)
    if not t:
        return await u.effective_message.reply_text("Reply to a user, or pass @user / ID.")
    q("update warns set n=max(n-1,0) where chat=? and user=?", u.effective_chat.id, uid_of(t))
    await u.effective_message.reply_text("✅ Removed one warning.")


@group_admin
async def cmd_warns(u, c):
    t, _ = await target(u, c)
    t = t or u.effective_user
    r = one("select n from warns where chat=? and user=?", u.effective_chat.id, uid_of(t))
    await u.effective_message.reply_text(f"Warnings: {r['n'] if r else 0}/{WARN_LIMIT}")


@group_admin
async def cmd_resetwarns(u, c):
    t, _ = await target(u, c)
    if not t:
        return await u.effective_message.reply_text("Reply to a user, or pass @user / ID.")
    q("delete from warns where chat=? and user=?", u.effective_chat.id, uid_of(t))
    await u.effective_message.reply_text("✅ Warnings reset.")


def register(app):
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("unwarn", cmd_unwarn))
    app.add_handler(CommandHandler("warns", cmd_warns))
    app.add_handler(CommandHandler("resetwarns", cmd_resetwarns))
