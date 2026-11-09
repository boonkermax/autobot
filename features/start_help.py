"""/start /help /id"""
import html

from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
from telegram.constants import ChatType, ParseMode
from telegram.error import TelegramError
from telegram.ext import CommandHandler, CallbackQueryHandler

from config import UPDATES_URL
from database import q
from utils import remember

HELP = [
"""📚 <b>Complete Command Help</b>

🤖 <b>Join Request Acceptor Bot Help</b>

🚀 <b>Getting Started</b>
• /start — Open the welcome panel and quick setup buttons.
• /help — Show this complete command guide.
• /id — Get the current chat ID, chat type, title, and your user ID.

✅ <b>Join Request Tools</b>
• /login — Login with your Telegram account session in private chat.
• /logout — Remove your saved Telegram account session.
• /accept &lt;chat_id&gt; — Approve all pending join requests for a group/channel.
  Example: /accept -1001234567890
• /autoapprove on|off — Instantly approve new join requests (bot-level).
• /scan on|off — Toggle automatic pending-request scan + stats post for this chat.
• /scannow — Run a scan right now for this chat.""",

"""📚 <b>Complete Command Help</b>

🛡 <b>Group Admin Tools</b>
• /lock &lt;type&gt; — Block a content type in the group.
• /unlock &lt;type&gt; — Allow a locked content type again.
• /locks — Show current group lock status.
• /warns [@user] — Check a user's warnings; reply to a user or pass username.
• /resetwarns [@user] — Reset a user's warnings.

🛡 <b>Anti-Spam</b>
• /spam on|off — Warn, then ban, anyone repeating the same message.
• /spam limit &lt;2-20&gt; — Identical messages allowed (default 3).
• /spam window &lt;5-600&gt; — Time window in seconds (default 30).

👮 <b>Group Management</b>
• /ban · /unban · /kick — reply, @user or ID. Ban takes 30m/2h/1d/1w.
• /mute · /unmute — same usage, supports a duration.
• /warn · /unwarn — add or remove one warning.
• /del · /purge — reply to delete one message or everything below it.
• /pin [silent] · /unpin · /unpinall
• /promote · /demote · /admins · /info""",

"""📚 <b>Complete Command Help</b>

📌 <b>Group Extras</b>
• /rules · /setrules · /clearrules
• /welcome on|off · /setwelcome &lt;text&gt; · /resetwelcome — placeholders: {mention} {first} {chat} {id} {count}
• /addblacklist · /rmblacklist · /blacklist — delete + warn for banned words.
• /save &lt;name&gt; &lt;text&gt; · /get &lt;name&gt; (or #name) · /notes · /clear &lt;name&gt;
• /filter &lt;keyword&gt; — reply to any message to save it as an auto-reply (media + inline URL buttons supported).
• /filter &lt;keyword&gt; &lt;text&gt; — create a text auto-reply.
• /filters / /filterlist — list filters with Previous, page count and Next buttons.
• /stop &lt;keyword&gt; — remove one filter. /stopall — remove all filters.
• /slowmode · /mutechat · /unmutechat · /setgtitle · /setgdesc · /invitelink · /cleanservice on|off
• /report (reply) or @admin — call the admins.

🔐 <b>Lock Types</b>
all, button, emoji, forward, url, username

🧹 <b>Auto-Ban Tools</b>
• /autobannow — Scan the current group and ban deleted/deactivated accounts.
• /autobanstats — Show the latest auto-ban scan result for the group.""",

"""📚 <b>Complete Command Help</b>

📣 <b>Owner Tools</b>
• /broadcast — Reply to a message with this command to broadcast it to users.
• /stats — Show total bot users.

💡 <b>Tips</b>
• Send /id inside your group/channel to copy the correct chat ID.
• Make the bot admin with invite-user rights for auto-approval.
• Give ban/restrict rights before using auto-ban and warning enforcement.""",
]


def help_kb(i):
    nav = []
    if i > 0:
        nav.append(Btn("⬅️ Previous", callback_data=f"help:{i-1}"))
    nav.append(Btn(f"{i+1}/{len(HELP)}", callback_data="noop"))
    if i < len(HELP) - 1:
        nav.append(Btn("Next ➡️", callback_data=f"help:{i+1}"))
    return Markup([nav, [Btn("📚 Bot Updates", url=UPDATES_URL)]])


async def cmd_help(u, c):
    await u.effective_message.reply_text(HELP[0], parse_mode=ParseMode.HTML, reply_markup=help_kb(0))


async def cb_help(u, c):
    qy = u.callback_query
    if qy.data == "noop":
        return await qy.answer()
    i = int(qy.data.split(":")[1])
    try:
        await qy.edit_message_text(HELP[i], parse_mode=ParseMode.HTML, reply_markup=help_kb(i))
    except TelegramError:
        pass
    await qy.answer()


async def cmd_start(u, c):
    us = u.effective_user
    remember(us)
    q("insert or ignore into bot_users values(?)", us.id)
    if u.effective_chat.type != ChatType.PRIVATE:
        return await u.effective_message.reply_text("Send /start in private for setup or /help to view all commands.")
    un = c.bot.username
    kb = Markup([
        [Btn("📚 Bot Updates", url=UPDATES_URL)],
        [Btn("➕ Add To Group", url=f"https://t.me/{un}?startgroup=true&admin=delete_messages+restrict_members+invite_users+pin_messages+promote_members+change_info+manage_chat"),
         Btn("➕ Add To Channel", url=f"https://t.me/{un}?startchannel=true&admin=invite_users+post_messages+change_info")],
    ])
    await u.effective_message.reply_text(
        f"Hey <b>{html.escape(us.first_name)}</b> 👋\n\n"
        "I can automatically accept Telegram join requests and help admins manage groups.\n\n"
        "<b>Quick setup:</b>\n1. Add me to your group or channel as admin.\n"
        "2. Give me invite-user rights to approve join requests.\n3. Use /id to get your chat ID.\n"
        "4. Login in private with /login.\n5. Run /accept &lt;chat_id&gt; to clear pending requests.\n\n"
        "Send /help anytime to view every command with usage details.",
        parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_id(u, c):
    ch, us = u.effective_chat, u.effective_user
    await u.effective_message.reply_text(
        f"🆔 Chat ID: <code>{ch.id}</code>\nType: {ch.type}\nTitle: {html.escape(ch.title or ch.first_name or '')}\nYour ID: <code>{us.id}</code>",
        parse_mode=ParseMode.HTML)


def register(app):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CallbackQueryHandler(cb_help, pattern=r"^(help:\d+|noop)$"))
