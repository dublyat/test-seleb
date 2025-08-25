import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# === Bot Configuration ===
BOT_API_ID = 123456  # Your bot's API ID
BOT_API_HASH = 'your_bot_api_hash'
BOT_TOKEN = '123456:ABC-DEF...'

# Admin user IDs allowed to control the bot
ADMIN_IDS = {111111111, 222222222}

# Target group IDs for alternating forwarding
TARGET_GROUPS = [-1001234567890, -1009876543210]

# In-memory store: Telegram user ID -> (session_str, api_id, api_hash)
user_sessions = {}

def admin_only(handler):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("⛔ You are not authorized to use this command.")
            return
        return await handler(event)
    return wrapper

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def on_addme(event):
    user = event.sender_id
    async def prompt(text):
        await event.respond(text)
        resp = await bot.wait_for_new_message(from_users=user)
        return resp.text

    api_id = int(await prompt("Send your **API ID**:"))
    api_hash = await prompt("Send your **API Hash**:")
    phone = await prompt("Send your **phone number** (with country code):")
    await event.respond("Logging in... Watch for prompts here.")

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = await prompt("Enter the login **code** you received:")
        try:
            await client.sign_in(phone, code)
        except Exception:
            password = await prompt("2FA required. Enter your **password**:")
            await client.sign_in(password=password)

    session_str = client.session.save()
    user_sessions[user] = (session_str, api_id, api_hash)
    await event.respond("✅ Login successful! Session stored securely.")
    await client.disconnect()

@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def on_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        return await event.respond("No session found. Use /addme first.")
    await event.respond("Userbot is starting—forwarding enabled.")
    asyncio.create_task(user_forward_bot(user))

async def user_forward_bot(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)

    @client.on(events.NewMessage(pattern='/start', from_users=user))
    async def start_cmd(e):
        client.is_forward_active = True
        await e.respond("Forwarding started.")

    @client.on(events.NewMessage(pattern='/stop', from_users=user))
    async def stop_cmd(e):
        client.is_forward_active = False
        await e.respond("Forwarding stopped.")

    await client.start()
    client.is_forward_active = False
    group_idx = 0

    while True:
        if getattr(client, 'is_forward_active', False):
            saved = await client.get_messages('me', limit=10)
            if saved:
                msg = random.choice(saved)
                target = TARGET_GROUPS[group_idx]
                await client.forward_messages(entity=target, messages=msg)
                print(f"[User {user}] forwarded message {msg.id} to {target}")
                group_idx ^= 1
            await asyncio.sleep(random.randint(300, 1800))
        else:
            await asyncio.sleep(5)

async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

