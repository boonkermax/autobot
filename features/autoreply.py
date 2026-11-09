"""/filter /filters /filterlist /stop /stopall — keyword auto-replies (media + buttons)."""
import html
import json
import re

from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, CallbackQueryHandler

from database import q, rows
from services.saved import build_saved, send_saved, dumps
from utils import group_admin

PER = 10


@group_admin
async def cmd_filter(u, c):
    m = u.effective_message
    if not c.args:
        return await m.reply_text("Usage: /filter <keyword> <text> — or reply to a message")
    d = build_saved(m)
    if not d:
        return await m.reply_text("Give reply text or reply to a message.")
    q("insert into filt values(?,?,?) on conflict(chat,kw) do update set data=excluded.data",
      u.effective_chat.id, c.args[0].lower(), dumps(d))
    await m.reply_text(f"✅ Filter saved: {html.escape(c.args[0].lower())}", parse_mode=ParseMode.HTML)


@group_admin
async def cmd_stop(u, c):
    if c.args:
        q("delete from filt where chat=? and kw=?", u.effective_chat.id, c.args[0].lower())
    await u.effective_message.reply_text("✅ Filter removed.")


@group_admin
async def cmd_stopall(u, c):
    q("delete from filt where chat=?", u.effective_chat.id)
    await u.effective_message.reply_text("✅ All filters removed.")


def filt_page(chat_id, p):
    ks = [r["kw"] for r in rows("select kw from filt where chat=? order by kw", chat_id)]
    pages = max(1, -(-len(ks) // PER))
    p = max(0, min(p, pages - 1))
    txt = "🔎 <b>Filters</b>\n" + ("\n".join(f"• {html.escape(k)}" for k in ks[p * PER:(p + 1) * PER]) if ks else "None yet.")
    nav = []
    if p > 0:
        nav.append(Btn("⬅️ Previous", callback_data=f"flt:{p-1}"))
    nav.append(Btn(f"{p+1}/{pages}", callback_data="noop"))
    if p < pages - 1:
        nav.append(Btn("Next ➡️", callback_data=f"flt:{p+1}"))
    return txt, Markup([nav])


async def cmd_filters(u, c):
    t, k = filt_page(u.effective_chat.id, 0)
    await u.effective_message.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=k)


async def cb_filters(u, c):
    qy = u.callback_query
    t, k = filt_page(qy.message.chat_id, int(qy.data.split(":")[1]))
    try:
        await qy.edit_message_text(t, parse_mode=ParseMode.HTML, reply_markup=k)
    except TelegramError:
        pass
    await qy.answer()


async def check(u, c):
    m = u.effective_message
    txt = (m.text or m.caption or "").lower()
    if not txt:
        return False
    for r in rows("select kw,data from filt where chat=?", u.effective_chat.id):
        if re.search(rf"(?<!\w){re.escape(r['kw'])}(?!\w)", txt):
            await send_saved(m, json.loads(r["data"]))
            return True
    return False


def register(app):
    app.add_handler(CommandHandler("filter", cmd_filter))
    app.add_handler(CommandHandler(["filters", "filterlist"], cmd_filters))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("stopall", cmd_stopall))
    app.add_handler(CallbackQueryHandler(cb_filters, pattern=r"^flt:\d+$"))
