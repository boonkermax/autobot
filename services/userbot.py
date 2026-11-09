"""Telethon user-session helpers (pending join requests, member scans)."""
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetChatInviteImportersRequest, HideAllChatJoinRequestsRequest
from telethon.tl.types import InputUserEmpty

from config import API_ID, API_HASH, FERNET
from database import one


async def tl_client(uid):
    r = one("select data from sessions where user_id=?", uid)
    if not r:
        return None
    cl = TelegramClient(StringSession(FERNET.decrypt(r["data"]).decode()), API_ID, API_HASH)
    await cl.connect()
    if not await cl.is_user_authorized():
        await cl.disconnect()
        return None
    return cl


async def tl_peer(cl, chat_id):
    try:
        return await cl.get_input_entity(chat_id)
    except ValueError:
        await cl.get_dialogs()
        return await cl.get_input_entity(chat_id)


async def pending_count(cl, peer):
    r = await cl(GetChatInviteImportersRequest(peer=peer, requested=True, offset_date=None,
                                               offset_user=InputUserEmpty(), limit=1, q=""))
    return r.count


async def approve_all(cl, chat_id):
    """Approve every pending join request. Returns (found, approved)."""
    peer = await tl_peer(cl, chat_id)
    found = await pending_count(cl, peer)
    remaining = found
    for _ in range(30):
        if remaining <= 0:
            break
        await cl(HideAllChatJoinRequestsRequest(peer=peer, approved=True))
        await asyncio.sleep(1)
        new = await pending_count(cl, peer)
        if new >= remaining:
            break
        remaining = new
    return found, found - remaining
