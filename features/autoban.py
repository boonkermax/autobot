"""/autobannow /autobanstats — ban deleted accounts (needs a logged-in admin session)."""
import asyncio
from datetime import datetime

from telegram.error import TelegramError
from telegram.ext import CommandHandler

from database import one, cget, cset
from services.userbot import tl_client, tl_peer
from utils import group_admin


@group_admin
async def cmd_autobannow(u, c):
    m, cid = u.effective_message, u.effective_chat.id
    r = one("select session_user from chats where chat_id=?", cid)
    uid = (r and r["session_user"]) or u.effective_user.id
    cl = await tl_client(uid)
    if not cl:
        return await m.reply_text("Needs a logged-in admin session: /login in private, then /accept <chat_id>.")
    note = await m.reply_text("🧹 Scanning members…")
    scanned = banned = 0
    try:
        peer = await tl_peer(cl, cid)
        async for p in cl.iter_participants(peer):
            scanned += 1
            if p.deleted:
                try:
                    await c.bot.ban_chat_member(cid, p.id)
                    banned += 1
                except TelegramError:
                    pass
                await asyncio.sleep(0.3)
        cset(cid, "autoban", {"ts": datetime.now().strftime("%d %b %Y %H:%M"), "scanned": scanned, "banned": banned})
        await note.edit_text(f"✅ Scanned {scanned} · banned {banned} deleted accounts.")
    except Exception as e:
        await note.edit_text(f"❌ {e}")
    finally:
        await cl.disconnect()


async def cmd_autobanstats(u, c):
    r = cget(u.effective_chat.id, "autoban")
    await u.effective_message.reply_text(
        f"🧹 Last scan: {r['ts']}\nScanned: {r['scanned']}\nBanned: {r['banned']}" if r else "No auto-ban scan yet.")


def register(app):
    app.add_handler(CommandHandler("autobannow", cmd_autobannow))
    app.add_handler(CommandHandler("autobanstats", cmd_autobanstats))
