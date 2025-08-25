import os
import sys
import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession

BOT_API_ID = '24565808'
BOT_API_HASH = '4eb74502af26e86c3571225a29243e3e'
BOT_TOKEN = '7802435088:AAHcwYbO1nFpz4jZljkwy4Xm9Nr9GRfpV2Y' 

ADMIN_IDS = {5087266104}

# --- In-Memory Storage ---
user_sessions = {}       # user_id -> (session_str, api_id, api_hash)
TARGET_GROUPS = []
forward_tasks = {}       # user_id -> task

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ Unauthorized.")
            return
        return await func(event)
    return wrapper

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/restart'))
@admin_only
async def restart_handler(event):
    await event.respond("🔄 Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.on(events.NewMessage(pattern=r'/addgroup (.+)'))
@admin_only
async def add_group(event):
    gid = event.pattern_match.group(1).strip()
    try:
        TARGET_GROUPS.append(int(gid))
        await event.respond(f"✅ Added group {gid}")
    except ValueError:
        await event.respond("Invalid ID.")

@bot.on(events.NewMessage(pattern=r'/removegroup (.+)'))
@admin_only
async def remove_group(event):
    gid = event.pattern_match.group(1).strip()
    try:
        TARGET_GROUPS.remove(int(gid))
        await event.respond(f"✅ Removed group {gid}")
    except (ValueError, KeyError):
        await event.respond("Not in list.")

@bot.on(events.NewMessage(pattern='/listgroups'))
@admin_only
async def list_groups(event):
    text = "No groups set." if not TARGET_GROUPS else "\n".join(str(g) for g in TARGET_GROUPS)
    await event.respond("Groups:\n" + text)

@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def on_addme(event):
    user = event.sender_id
    async def prompt(msg):
        await event.respond(msg)
        res = await bot.wait_for_new_message(from_users=user)
        return res.text

    api_id = int(await prompt("Send API ID:"))
    api_hash = await prompt("Send API Hash:")
    phone = await prompt("Phone number with country code:")
    await event.respond("Logging in...")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = await prompt("Enter code:")
        try:
            await client.sign_in(phone, code)
        except:
            pwd = await prompt("2FA password:")
            await client.sign_in(password=pwd)

    sess = client.session.save()
    user_sessions[user] = (sess, api_id, api_hash)
    await event.respond("✅ Logged in and session stored.")
    await client.disconnect()

@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def on_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        await event.respond("No session. Use /addme.")
        return
    if user not in forward_tasks:
        task = asyncio.create_task(user_forward_loop(user))
        forward_tasks[user] = task
        await event.respond("▶ Userbot started.")
    else:
        await event.respond("Userbot already running.")

async def user_forward_loop(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)

    @client.on(events.NewMessage(pattern='/start', from_users=user))
    async def start_fwd(e):
        client.is_forward_active = True
        await e.respond("Forwarding started.")

    @client.on(events.NewMessage(pattern='/stop', from_users=user))
    async def stop_fwd(e):
        client.is_forward_active = False
        await e.respond("Forwarding stopped.")

    await client.start()
    client.is_forward_active = False
    idx = 0

    while True:
        if getattr(client, 'is_forward_active', False) and TARGET_GROUPS:
            msgs = await client.get_messages('me', limit=10)
            if msgs:
                msg = random.choice(msgs)
                group = TARGET_GROUPS[idx % len(TARGET_GROUPS)]
                await client.forward_messages(group, msg)
                print(f"[{user}] forwarded {msg.id} to {group}")
                idx += 1
            await asyncio.sleep(random.randint(300, 1800))
        else:
            await asyncio.sleep(5)

async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
