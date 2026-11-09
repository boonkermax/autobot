"""ban/unban/kick/mute/unmute/del/purge/pin/unpin/unpinall/promote/demote/admins/info"""
from telegram import ChatPermissions
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler

from database import one
from utils import (group_admin, is_admin, target, uid_of, parse_dur, tmp_reply,
                   admin_map, clear_admin_cache, mention)


def mod_cmd(action):
    @group_admin
    async def f(u, c):
        m, cid = u.effective_message, u.effective_chat.id
        t, args = await target(u, c)
        if not t:
            return await m.reply_text("Reply to a user, or pass @user / ID.")
        uid = uid_of(t)
        if action in ("ban", "kick", "mute") and await is_admin(c.bot, cid, uid):
            return await m.reply_text("Can't do that to an admin.")
        until = parse_dur(args[0]) if args else None
        try:
            if action == "ban":
                await c.bot.ban_chat_member(cid, uid, until_date=until)
            elif action == "unban":
                await c.bot.unban_chat_member(cid, uid, only_if_banned=True)
            elif action == "kick":
                await c.bot.ban_chat_member(cid, uid)
                await c.bot.unban_chat_member(cid, uid)
            elif action == "mute":
                await c.bot.restrict_chat_member(cid, uid, ChatPermissions.no_permissions(), until_date=until)
            elif action == "unmute":
                await c.bot.restrict_chat_member(cid, uid, ChatPermissions.all_permissions())
            await m.reply_text(f"✅ {action} done" + (f" until {until:%d %b %H:%M} UTC" if until and action in ("ban", "mute") else ""))
        except TelegramError as e:
            await m.reply_text(f"❌ {e.message}")
    return f


@group_admin
async def cmd_del(u, c):
    m = u.effective_message
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message.")
    for x in (m.reply_to_message, m):
        try:
            await x.delete()
        except TelegramError:
            pass


@group_admin
async def cmd_purge(u, c):
    m = u.effective_message
    if not m.reply_to_message:
        return await m.reply_text("Reply to the first message to purge.")
    ids = list(range(m.reply_to_message.message_id, m.message_id + 1))
    for i in range(0, len(ids), 100):
        try:
            await c.bot.delete_messages(m.chat_id, ids[i:i + 100])
        except TelegramError:
            pass
    await tmp_reply(m, f"🧹 Purged {len(ids)} messages.")


@group_admin
async def cmd_pin(u, c):
    m = u.effective_message
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message to pin.")
    try:
        await c.bot.pin_chat_message(m.chat_id, m.reply_to_message.message_id,
                                     disable_notification=bool(c.args and c.args[0] == "silent"))
    except TelegramError as e:
        await m.reply_text(f"❌ {e.message}")


@group_admin
async def cmd_unpin(u, c):
    m = u.effective_message
    try:
        await c.bot.unpin_chat_message(m.chat_id, m.reply_to_message.message_id if m.reply_to_message else None)
    except TelegramError as e:
        await m.reply_text(f"❌ {e.message}")


@group_admin
async def cmd_unpinall(u, c):
    try:
        await c.bot.unpin_all_chat_messages(u.effective_chat.id)
        await u.effective_message.reply_text("📌 All unpinned.")
    except TelegramError as e:
        await u.effective_message.reply_text(f"❌ {e.message}")


def promote_cmd(on):
    @group_admin
    async def f(u, c):
        t, _ = await target(u, c)
        m = u.effective_message
        if not t:
            return await m.reply_text("Reply to a user, or pass @user / ID.")
        try:
            await c.bot.promote_chat_member(u.effective_chat.id, uid_of(t), can_manage_chat=on, can_delete_messages=on,
                                            can_restrict_members=on, can_pin_messages=on, can_invite_users=on)
            clear_admin_cache(u.effective_chat.id)
            await m.reply_text("✅ Promoted." if on else "✅ Demoted.")
        except TelegramError as e:
            await m.reply_text(f"❌ {e.message}")
    return f


async def cmd_admins(u, c):
    clear_admin_cache(u.effective_chat.id)
    a = await admin_map(c.bot, u.effective_chat.id)
    await u.effective_message.reply_text(
        "👮 <b>Admins</b>\n" + "\n".join(f"• {mention(x.user)}" for x in a.values() if not x.user.is_bot),
        parse_mode=ParseMode.HTML)


async def cmd_info(u, c):
    m = u.effective_message
    t, _ = await target(u, c)
    t = t or u.effective_user
    uid = uid_of(t)
    try:
        cm = await c.bot.get_chat_member(u.effective_chat.id, uid)
        us = cm.user
        w = one("select n from warns where chat=? and user=?", u.effective_chat.id, uid)
        info = (f"👤 {mention(us)}\nID: <code>{us.id}</code>\nUsername: @{us.username or '-'}\n"
                f"Status: {cm.status}\nWarns: {w['n'] if w else 0}")
    except TelegramError as e:
        info = f"❌ {e.message}"
    await m.reply_text(info, parse_mode=ParseMode.HTML)


def register(app):
    for name in ("ban", "unban", "kick", "mute", "unmute"):
        app.add_handler(CommandHandler(name, mod_cmd(name)))
    app.add_handler(CommandHandler("del", cmd_del))
    app.add_handler(CommandHandler("purge", cmd_purge))
    app.add_handler(CommandHandler("pin", cmd_pin))
    app.add_handler(CommandHandler("unpin", cmd_unpin))
    app.add_handler(CommandHandler("unpinall", cmd_unpinall))
    app.add_handler(CommandHandler("promote", promote_cmd(True)))
    app.add_handler(CommandHandler("demote", promote_cmd(False)))
    app.add_handler(CommandHandler("admins", cmd_admins))
    app.add_handler(CommandHandler("info", cmd_info))
