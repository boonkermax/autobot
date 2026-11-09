"""/broadcast /stats — owner only."""
import asyncio

from telegram.error import TelegramError
from telegram.ext import CommandHandler

from config import OWNER_ID
from database import one, rows


async def cmd_stats(u, c):
    if u.effective_user.id != OWNER_ID:
        return
    n = lambda t: one(f"select count(*) n from {t}")["n"]
    await u.effective_message.reply_text(f"👥 Users: {n('bot_users')}\n💬 Chats: {n('chats')}\n🔐 Sessions: {n('sessions')}")


async def cmd_broadcast(u, c):
    m = u.effective_message
    if u.effective_user.id != OWNER_ID:
        return
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message to broadcast.")
    ok = bad = 0
    for r in rows("select user_id from bot_users"):
        try:
            await m.reply_to_message.copy(r["user_id"])
            ok += 1
        except TelegramError:
            bad += 1
        await asyncio.sleep(0.05)
    await m.reply_text(f"📣 Sent {ok} · failed {bad}")


def register(app):
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
