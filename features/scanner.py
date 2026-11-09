"""Automatic pending-request scan job + stats posting."""
import asyncio
import html
import logging
from datetime import datetime, timedelta

from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler
from telethon.errors import FloodWaitError

from config import SCAN_MIN
from database import one, rows, cget, cset
from services.userbot import tl_client, approve_all
from utils import group_admin, register_chat, toggler

log = logging.getLogger(__name__)


def stats_text(title, found, ok, total, err=None):
    nxt = (datetime.now() + timedelta(minutes=SCAN_MIN)).strftime("%H:%M")
    s = (f"📊 <b>Pending Request Scan</b>\n• Chat: {html.escape(title or '')}\n"
         f"• Pending found: <b>{found}</b>\n• Approved: <b>{ok}</b>\n• Total approved: {total}\n")
    if err:
        s += f"• Error: {html.escape(err)}\n"
    return s + f"• Scanned: {datetime.now().strftime('%d %b %H:%M')}\n• Next scan ≈ {nxt}"


async def scan_chat(bot, r, clients):
    cid, uid = r["chat_id"], r["session_user"]
    found = ok = 0
    err = None
    if not uid or not one("select 1 from sessions where user_id=?", uid):
        if not cget(cid, "nosession_notice"):
            cset(cid, "nosession_notice", True)
            try:
                await bot.send_message(cid, "ℹ️ Auto-scan needs a logged-in admin: open the bot in private → /login → /accept <chat_id>.")
            except TelegramError:
                pass
        return
    try:
        if uid not in clients:
            clients[uid] = await tl_client(uid)
        cl = clients[uid]
        if not cl:
            raise RuntimeError("session expired — /login again")
        found, ok = await approve_all(cl, cid)
        cset(cid, "total_approved", cget(cid, "total_approved", 0) + ok)
    except FloodWaitError as e:
        err = f"flood wait {e.seconds}s"
        await asyncio.sleep(min(e.seconds, 60))
    except Exception as e:
        err = str(e)[:120]
    old = cget(cid, "stats_msg")
    if old:
        try:
            await bot.delete_message(cid, old)
        except TelegramError:
            pass
    try:
        msg = await bot.send_message(cid, stats_text(r["title"], found, ok, cget(cid, "total_approved", 0), err),
                                     parse_mode=ParseMode.HTML)
        cset(cid, "stats_msg", msg.message_id)
    except TelegramError as e:
        log.warning("stats post %s: %s", cid, e)


async def _close(clients):
    for cl in clients.values():
        if cl:
            await cl.disconnect()


async def scan_all(ctx):
    clients = {}
    try:
        for r in rows("select * from chats"):
            if not cget(r["chat_id"], "scan", True):
                continue
            await scan_chat(ctx.bot, r, clients)
            await asyncio.sleep(2)
    finally:
        await _close(clients)


@group_admin
async def cmd_scannow(u, c):
    ch = u.effective_chat
    has = one("select 1 from sessions where user_id=?", u.effective_user.id)
    register_chat(ch, u.effective_user.id if has else None)
    clients = {}
    try:
        await scan_chat(c.bot, one("select * from chats where chat_id=?", ch.id), clients)
    finally:
        await _close(clients)


def register(app):
    app.add_handler(CommandHandler("scan", toggler("scan", "Auto-scan")))
    app.add_handler(CommandHandler("scannow", cmd_scannow))
    app.job_queue.run_repeating(scan_all, interval=SCAN_MIN * 60, first=60, name="scan_all")
