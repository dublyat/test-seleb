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

# In-memory stores
user_sessions = {}    # user_id -> (session_str, api_id, api_hash)
TARGET_GROUPS = []    # Dynamic list of forwarding target group IDs
forward_tasks = {}    # user_id -> asyncio.Task reference

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH)

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ Unauthorized access.")
            return
        return await func(event)
    return wrapper

# --- Admin Commands ---

@bot.on(events.NewMessage(pattern='/restart'))
@admin_only
async def cmd_restart(event):
    await event.respond("🔄 Restarting bot...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.on(events.NewMessage(pattern=r'/addgroup (.+)'))
@admin_only
async def cmd_addgroup(event):
    try:
        gid = int(event.pattern_match.group(1).strip())
        TARGET_GROUPS.append(gid)
        await event.respond(f"Added group: {gid}")
    except:
        await event.respond("Invalid group ID.")

@bot.on(events.NewMessage(pattern=r'/removegroup (.+)'))
@admin_only
async def cmd_removegroup(event):
    try:
        gid = int(event.pattern_match.group(1).strip())
        TARGET_GROUPS.remove(gid)
        await event.respond(f"Removed group: {gid}")
    except:
        await event.respond("Group not found in list.")

@bot.on(events.NewMessage(pattern='/listgroups'))
@admin_only
async def cmd_listgroups(event):
    msg = "None" if not TARGET_GROUPS else "\n".join(map(str, TARGET_GROUPS))
    await event.respond(f"Forward Target Groups:\n{msg}")

@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def cmd_addme(event):
    user = event.sender_id
    async def prompt(msg):
        await event.respond(msg)
        resp = await bot.wait_for_new_message(from_users=user)
        return resp.text

    api_id = int(await prompt("Enter API ID:"))
    api_hash = await prompt("Enter API Hash:")
    phone = await prompt("Enter phone number (+...):")
    await event.respond("Logging in user...")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = await prompt("Enter the code you received:")
        try:
            await client.sign_in(phone, code)
        except:
            pwd = await prompt("2FA password required, please enter:")
            await client.sign_in(password=pwd)

    user_sessions[user] = (client.session.save(), api_id, api_hash)
    await event.respond("✅ User session stored successfully.")
    await client.disconnect()

@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def cmd_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        await event.respond("No session found. Use /addme first.")
        return
    if user in forward_tasks:
        await event.respond("Userbot already active.")
        return

    task = asyncio.create_task(user_forward_loop(user))
    forward_tasks[user] = task
    await event.respond("▶ Userbot forwarding has started.")

# --- Forwarding Logic ---

async def user_forward_loop(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.start()
    client.is_active = False
    idx = 0

    @client.on(events.NewMessage(pattern='/start', from_users=user))
    async def start_forward(e):
        client.is_active = True
        await e.respond("Forwarding activated.")

    @client.on(events.NewMessage(pattern='/stop', from_users=user))
    async def stop_forward(e):
        client.is_active = False
        await e.respond("Forwarding paused.")

    while True:
        if client.is_active and TARGET_GROUPS:
            msgs = await client.get_messages('me', limit=10)
            if msgs:
                msg = random.choice(msgs)
                target = TARGET_GROUPS[idx % len(TARGET_GROUPS)]
                await client.forward_messages(target, msg)
                idx += 1
            await asyncio.sleep(random.randint(300, 1800))
        else:
            await asyncio.sleep(5)

async def main():
    # Everything runs in this one loop. No other loops anywhere.
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
