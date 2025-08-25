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

# Runtime storage
user_sessions = {}  # user_id -> (session_str, api_id, api_hash)
TARGET_GROUPS = []  # List of group IDs for forwarding
forward_tasks = {}  # user_id -> asyncio.Task (retains task refs)

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH)

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ You are not authorized to use this command.")
            return
        return await func(event)
    return wrapper

# --- Admin-only Controls ---
@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def cmd_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        await event.respond("No session found. Use `/addme` first.")
        return
    if user in forward_tasks:
        await event.respond("Userbot forwarding already running.")
        return

    await event.respond("Please provide the user ID to start forwarding:")
    async with bot.conversation(user) as conv:
        response = await conv.get_response()
        try:
            target_user_id = int(response.text)
            if target_user_id not in user_sessions:
                await conv.send_message("User ID not found in sessions.")
                return
            task = asyncio.create_task(user_forward_loop(target_user_id))
            forward_tasks[target_user_id] = task
            await conv.send_message(f"▶ Userbot forwarding started for user ID {target_user_id}.")
        except ValueError:
            await conv.send_message("Invalid user ID. Please enter a valid integer.")

@bot.on(events.NewMessage(pattern='/stopuser'))
@admin_only
async def cmd_stopuser(event):
    user = event.sender_id
    if user not in forward_tasks:
        await event.respond("No active forwarding task found for this user.")
        return

    forward_tasks[user].cancel()
    del forward_tasks[user]
    await event.respond(f"⏹ Stopped userbot forwarding for user ID {user}.")

# --- Forwarding Loop ---
async def user_forward_loop(user_id):
    session_str, api_id, api_hash = user_sessions[user_id]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    await client.start()
    client.is_active = False
    idx = 0

    @client.on(events.NewMessage(pattern='/start', from_users=user_id))
    async def start_fwd(e):
        client.is_active = True
        await e.respond("⏯ Forwarding started.")

    @client.on(events.NewMessage(pattern='/stop', from_users=user_id))
    async def stop_fwd(e):
        client.is_active = False
        await e.respond("⏹ Forwarding stopped.")

    while True:
        if client.is_active and TARGET_GROUPS:
            msgs = await client.get_messages('me', limit=10)
            if msgs:
                msg = random.choice(msgs)
                target = TARGET_GROUPS[idx % len(TARGET_GROUPS)]
                await client.forward_messages(target, msg)
                idx += 1
            await asyncio.sleep(random.randint(30, 60))
        else:
            await asyncio.sleep(5)

# --- Bot Entrypoint ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
