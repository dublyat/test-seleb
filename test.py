import os
import sys
import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession

BOT_API_ID = 123456
BOT_API_HASH = 'your_bot_api_hash'
BOT_TOKEN = '123456:ABC-DEF...' 

ADMIN_IDS = {111111111, 222222222}

user_sessions = {} 
TARGET_GROUPS = [] 

def admin_only(func):
    async def wrapper(event):
        if event.sender_id not in ADMIN_IDS:
            await event.respond("ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ - ɢᴛғᴏ")
            return
        return await func(event)
    return wrapper

# --- Initialize Bot Client ---
bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH).start(bot_token=BOT_TOKEN)

# --- Command: Restart Bot ---
@bot.on(events.NewMessage(pattern='/restart'))
@admin_only
async def restart_handler(event):
    await event.respond("ʀᴇsᴛᴀʀᴛɪɴɢ ʙᴏᴛ 🔄")
    # Restart the current process with same Python binary and arguments
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    help_text = (
        "/startuser - ᴜsᴇʀ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ\n"
        "/addme - ᴀᴅᴅ ɴᴇᴡ sᴇssɪᴏɴ\n"
        "/addgroup <group_id> - Add a group to the forwarding list.\n"
        "/removegroup <group_id> - Remove a group from the forwarding list.\n"
        "/listgroups - List all target groups.\n"
        "/restart - Restart the bot (admin only).\n"
        "Use /help for more detailed information on each command."
    )
    await event.respond(help_text)

# --- Group Management Commands ---
@bot.on(events.NewMessage(pattern=r'/addgroup (.+)'))
@admin_only
async def add_group(event):
    group_id = event.pattern_match.group(1).strip()
    try:
        TARGET_GROUPS.append(int(group_id))
        await event.respond(f"✅ ɢʀᴏᴜᴘ ᴀᴅᴅᴇᴅ: {group_id}")
    except ValueError:
        await event.respond("ɪɴᴠᴀʟɪᴅ ɪᴅ. ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ɴᴜᴍᴇʀɪᴄ ɪᴅ.")

@bot.on(events.NewMessage(pattern=r'/removegroup (.+)'))
@admin_only
async def remove_group(event):
    group_id = event.pattern_match.group(1).strip()
    try:
        TARGET_GROUPS.remove(int(group_id))
        await event.respond(f"✅ ʀᴇᴍᴏᴠᴇᴅ ᴛᴀʀɢᴇᴛ: {group_id}")
    except (ValueError, KeyError):
        await event.respond("ᴛʜᴀᴛ ɪᴅ ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ʟɪsᴛ.")

@bot.on(events.NewMessage(pattern='/listgroups'))
@admin_only
async def list_groups(event):
    if TARGET_GROUPS:
        await event.respond("ᴄᴜʀʀᴇɴᴛ ᴛᴀʀɢᴇᴛ:\n" + "\n".join(str(g) for g in TARGET_GROUPS))
    else:
        await event.respond("ɴᴏ ᴛᴀʀɢᴇᴛ.")

# --- Command: Add and Login User Session ---
@bot.on(events.NewMessage(pattern='/addme'))
@admin_only
async def on_addme(event):
    user = event.sender_id
    async def prompt(prompt_text):
        await event.respond(prompt_text)
        resp = await bot.wait_for_new_message(from_users=user)
        return resp.text

    api_id = int(await prompt("Send your **API ID**:"))
    api_hash = await prompt("Send your **API Hash**:")
    phone = await prompt("Send your **phone number** (with country code):")
    await event.respond("Logging in... Watch here for prompts.")

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
    await event.respond("✅ Logged in successfully. Session stored securely.")
    await client.disconnect()

# --- Command: Start Forwarding Loop ---
@bot.on(events.NewMessage(pattern='/startuser'))
@admin_only
async def on_startuser(event):
    user = event.sender_id
    if user not in user_sessions:
        await event.respond("No session found. Please use /addme first.")
        return
    await event.respond("Userbot started. Use /start and /stop in your own Telegram account to control forwarding.")
    asyncio.create_task(user_forward_bot(user))

# --- Forward Loop ---
async def user_forward_bot(user):
    session_str, api_id, api_hash = user_sessions[user]
    client = TelegramClient(StringSession(session_str), api_id, api_hash)

    @client.on(events.NewMessage(pattern='/start', from_users=user))
    async def start_forward(e):
        client.is_forward_active = True
        await e.respond("⏯ Forwarding started.")

    @client.on(events.NewMessage(pattern='/stop', from_users=user))
    async def stop_forward(e):
        client.is_forward_active = False
        await e.respond("⏹ Forwarding stopped.")

    await client.start()
    client.is_forward_active = False
    group_idx = 0

    while True:
        if getattr(client, 'is_forward_active', False) and TARGET_GROUPS:
            saved = await client.get_messages('me', limit=10)
            if saved:
                msg = random.choice(saved)
                target = TARGET_GROUPS[group_idx % len(TARGET_GROUPS)]
                await client.forward_messages(entity=target, messages=msg)
                print(f"[User {user}] forwarded message {msg.id} to {target}")
                group_idx += 1

            delay = random.randint(300, 1800)
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(5)

# --- Run Bot ---
async def main():
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
