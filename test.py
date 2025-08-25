import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Bot credentials
BOT_API_ID = 123456  
BOT_API_HASH = 'abcdef1234567890abcdef1234567890'
BOT_TOKEN = '123456:ABC-DEF...'

# Forwarding targets
TARGET_GROUPS = [-1001234567890, -1009876543210]

# Store user sessions
user_sessions = {}

# Define admins
ADMIN_IDS = {111111111, 222222222}  # Replace with actual admin IDs

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ You are not authorized to use this command.")
            return
        return await func(event)
    return wrapper

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def on_addme(event):
    user = event.sender_id
    async def prompt(msg):
        await event.respond(msg)
        resp = await bot.wait_for_new_message(from_users=user)
        return resp.text

    api_id = int(await prompt("Send API ID:"))
    api_hash = await prompt("Send API Hash:")
    phone = await prompt("Send your phone number (+country code):")
    await event.respond("Logging in...")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = await prompt("Enter the login code:")
        try:
            await client.sign_in(phone, code)
        except Exception:
            password = await prompt("2FA required. Enter your password:")
            await client.sign_in(password=password)

    user_sessions[user] = (client.session.save(), api_id, api_hash)
    await event.respond("✅ Session stored successfully.")
    await client.disconnect()

@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def on_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        return await event.respond("No session found. Use /addme first.")
    await event.respond("Starting your userbot...")
    asyncio.create_task(user_forward_bot(user))

async def user_forward_bot(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)

    @client.on(events.NewMessage(pattern='/start', from_users=user))
    async def s(e):
        await e.respond("Forwarding started.")
        client.is_forward_active = True

    @client.on(events.NewMessage(pattern='/stop', from_users=user))
    async def s2(e):
        await e.respond("Forwarding stopped.")
        client.is_forward_active = False

    await client.start()
    client.is_forward_active = False
    group_idx = 0

    while True:
        if getattr(client, 'is_forward_active', False):
            msgs = await client.get_messages('me', limit=10)
            if msgs:
                msg = random.choice(msgs)
                await client.forward_messages(TARGET_GROUPS[group_idx], msg)
                group_idx = 1 - group_idx
            await asyncio.sleep(random.randint(300, 1800))
        else:
            await asyncio.sleep(5)

async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
