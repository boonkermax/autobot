"""Shared storage/sending of saved messages (used by notes and filters)."""
import html
import json

from telegram import InlineKeyboardMarkup as Markup
from telegram.constants import ParseMode


def extract(m):
    d = {"type": "text", "text": m.text_html or "", "file": None,
         "markup": m.reply_markup.to_dict() if m.reply_markup else None}
    for t in ("photo", "video", "document", "animation", "sticker", "audio", "voice"):
        v = getattr(m, t)
        if v:
            d.update(type=t, file=(v[-1].file_id if t == "photo" else v.file_id), text=m.caption_html or "")
            break
    return d


async def send_saved(m, d):
    mk = Markup.de_json(d["markup"], m.get_bot()) if d.get("markup") else None
    t, txt, fid = d["type"], d.get("text") or "", d.get("file")
    if t == "text" or not fid:
        return await m.reply_text(txt or "…", parse_mode=ParseMode.HTML, reply_markup=mk, disable_web_page_preview=True)
    fn = {"photo": m.reply_photo, "video": m.reply_video, "document": m.reply_document, "animation": m.reply_animation,
          "sticker": m.reply_sticker, "audio": m.reply_audio, "voice": m.reply_voice}[t]
    if t == "sticker":
        return await fn(fid, reply_markup=mk)
    return await fn(fid, caption=txt, parse_mode=ParseMode.HTML, reply_markup=mk)


def build_saved(m, name_args=1):
    parts = m.text.split(None, name_args + 1)
    inline = parts[name_args + 1] if len(parts) > name_args + 1 else None
    if m.reply_to_message and not inline:
        return extract(m.reply_to_message)
    if inline:
        return {"type": "text", "text": html.escape(inline), "file": None, "markup": None}
    return None


def dumps(d):
    return json.dumps(d)
