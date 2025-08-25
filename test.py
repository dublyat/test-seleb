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

TARGET_GROUPS = []  # Will be dynamically modified
user_sessions = {}  # user_id -> (session_str, api_id, api_hash)
forward_tasks = {}  # user_id -> asyncio.Task

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH)

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ Not authorized.")
            return
        return await func(event)
    return wrapper

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
        await event.respond(f"Group {gid} added.")
    except:
        await event.respond("Invalid group ID.")

@bot.on(events.NewMessage(pattern=r'/removegroup (.+)'))
@admin_only
async def cmd_removegroup(event):
    try:
        gid = int(event.pattern_match.group(1).strip())
        TARGET_GROUPS.remove(gid)
        await event.respond(f"Group {gid} removed.")
    except:
        await event.respond("That group isn't in the list.")

@bot.on(events.NewMessage(pattern='/listgroups'))
@admin_only
async def cmd_listgroups(event):
    if not TARGET_GROUPS:
        await event.respond("No target groups set.")
    else:
        await event.respond("Current groups:\n" + "\n".join(map(str, TARGET_GROUPS)))

@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def cmd_addme(event):
    user = event.sender_id
    async def prompt(msg):
        await event.respond(msg)
        res = await bot.wait_for_new_message(from_users=user)
        return res.text

    api_id = int(await prompt("API ID?"))
    api_hash = await prompt("API Hash?")
    phone = await prompt("Phone number (+...)?")
    await event.respond("Logging in...")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = await prompt("Enter received code:")
        try:
            await client.sign_in(phone, code)
        except:
            pwd = await prompt("Enter 2FA password:")
            await client.sign_in(password=pwd)

    user_sessions[user] = (client.session.save(), api_id, api_hash)
    await event.respond("Logged in and session stored.")
    await client.disconnect()

@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def cmd_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        await event.respond("No session found. Use /addme.")
    elif user in forward_tasks:
        await event.respond("Forwarding already running.")
    else:
        task = asyncio.create_task(user_forward_loop(user))
        forward_tasks[user] = task
        await event.respond("Userbot started.")

async def user_forward_loop(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient
