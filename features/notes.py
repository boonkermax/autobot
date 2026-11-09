"""/save /get /notes /clear and #name triggers."""
import json

from telegram.ext import CommandHandler

from database import q, one, rows
from services.saved import build_saved, send_saved, dumps
from utils import group_admin


@group_admin
async def cmd_save(u, c):
    m = u.effective_message
    if not c.args:
        return await m.reply_text("Usage: /save <name> <text> (or reply)")
    d = build_saved(m)
    if not d:
        return await m.reply_text("Give text or reply to a message.")
    q("insert into notes values(?,?,?) on conflict(chat,name) do update set data=excluded.data",
      u.effective_chat.id, c.args[0].lower(), dumps(d))
    await m.reply_text(f"✅ Saved. Get it with /get {c.args[0].lower()} or #{c.args[0].lower()}")


async def cmd_get(u, c):
    if not c.args:
        return
    r = one("select data from notes where chat=? and name=?", u.effective_chat.id, c.args[0].lower())
    if r:
        await send_saved(u.effective_message, json.loads(r["data"]))
    else:
        await u.effective_message.reply_text("Note not found.")


async def cmd_notes(u, c):
    n = [r["name"] for r in rows("select name from notes where chat=?", u.effective_chat.id)]
    await u.effective_message.reply_text("📝 Notes:\n" + "\n".join(f"• #{x}" for x in n) if n else "No notes.")


@group_admin
async def cmd_clear(u, c):
    if c.args:
        q("delete from notes where chat=? and name=?", u.effective_chat.id, c.args[0].lower())
    await u.effective_message.reply_text("✅ Cleared.")


async def check(u, c):
    m = u.effective_message
    txt = m.text or m.caption or ""
    if not txt.startswith("#") or len(txt) < 2:
        return False
    r = one("select data from notes where chat=? and name=?", u.effective_chat.id, txt[1:].split()[0].lower())
    if not r:
        return False
    await send_saved(m, json.loads(r["data"]))
    return True


def register(app):
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("get", cmd_get))
    app.add_handler(CommandHandler("notes", cmd_notes))
    app.add_handler(CommandHandler("clear", cmd_clear))
