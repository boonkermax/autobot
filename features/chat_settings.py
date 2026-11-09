"""/slowmode /mutechat /unmutechat /setgtitle /setgdesc /invitelink /cleanservice"""
import time

from telegram import ChatPermissions
from telegram.error import TelegramError
from telegram.ext import CommandHandler, MessageHandler, filters

from database import cget, cset
from utils import group_admin, toggler

LASTMSG = {}


@group_admin
async def cmd_slowmode(u, c):
    cid = u.effective_chat.id
    a = c.args[0].lower() if c.args else "off"
    s = int(a) if a.isdigit() else 0
    cset(cid, "slow", s)
    await u.effective_message.reply_text(f"🐢 Slowmode: {s}s" if s else "Slowmode off.")


async def check_slowmode(u, c):
    cid, us = u.effective_chat.id, u.effective_user
    slow = cget(cid, "slow", 0)
    if not slow:
        return False
    k = (cid, us.id)
    if time.time() - LASTMSG.get(k, 0) < slow:
        try:
            await u.effective_message.delete()
        except TelegramError:
            pass
        return True
    LASTMSG[k] = time.time()
    return False


def _perm_cmd(perms_factory, ok_text):
    @group_admin
    async def f(u, c):
        try:
            await c.bot.set_chat_permissions(u.effective_chat.id, perms_factory())
            await u.effective_message.reply_text(ok_text)
        except TelegramError as e:
            await u.effective_message.reply_text(f"❌ {e.message}")
    return f


@group_admin
async def cmd_setgtitle(u, c):
    try:
        await c.bot.set_chat_title(u.effective_chat.id, " ".join(c.args))
        await u.effective_message.reply_text("✅ Title updated.")
    except TelegramError as e:
        await u.effective_message.reply_text(f"❌ {e.message}")


@group_admin
async def cmd_setgdesc(u, c):
    try:
        await c.bot.set_chat_description(u.effective_chat.id, " ".join(c.args))
        await u.effective_message.reply_text("✅ Description updated.")
    except TelegramError as e:
        await u.effective_message.reply_text(f"❌ {e.message}")


@group_admin
async def cmd_invitelink(u, c):
    try:
        await u.effective_message.reply_text(await c.bot.export_chat_invite_link(u.effective_chat.id))
    except TelegramError as e:
        await u.effective_message.reply_text(f"❌ {e.message}")


async def on_service(u, c):
    if cget(u.effective_chat.id, "cleanservice", False):
        try:
            await u.effective_message.delete()
        except TelegramError:
            pass


def register(app):
    app.add_handler(CommandHandler("slowmode", cmd_slowmode))
    app.add_handler(CommandHandler("mutechat", _perm_cmd(ChatPermissions.no_permissions, "🔇 Chat muted.")))
    app.add_handler(CommandHandler("unmutechat", _perm_cmd(ChatPermissions.all_permissions, "🔊 Chat unmuted.")))
    app.add_handler(CommandHandler("setgtitle", cmd_setgtitle))
    app.add_handler(CommandHandler("setgdesc", cmd_setgdesc))
    app.add_handler(CommandHandler("invitelink", cmd_invitelink))
    app.add_handler(CommandHandler("cleanservice", toggler("cleanservice", "Clean service", False)))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.ALL & ~filters.StatusUpdate.NEW_CHAT_MEMBERS & filters.ChatType.GROUPS, on_service))
