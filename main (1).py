import asyncio
import json
import os
import random
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
)
from telethon.tl.functions.messages import GetHistoryRequest

# === 🔧 Configuration ===
BOT_API_ID = 24565808
BOT_API_HASH = "4eb74502af26e86c3571225a29243e3e"
BOT_TOKEN = "7802435088:AAHcwYbO1nFpz4jZljkwy4Xm9Nr9GRfpV2Y"  # Replace with your bot token
CONFIG_PATH = "config.json"
ACCOUNTS_DIR = "accounts"

os.makedirs(ACCOUNTS_DIR, exist_ok=True)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"admins": [123456789], "groups": [], "accounts": []}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)

config = load_config()
admins = config.get("admins", [])
user_states = {}

# === 🤖 Bot Setup ===
bot = TelegramClient("bot_controller", BOT_API_ID, BOT_API_HASH).start(bot_token=BOT_TOKEN)

# === /start Command ===
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if event.sender_id not in admins:
        return await event.reply("🚫 You are not authorized.")
    await event.reply("✅ Welcome!\n\nCommands:\n- /gen\n- /addgroup\n- /removegroup")

# === /gen Command ===
@bot.on(events.NewMessage(pattern="/gen"))
async def gen_session_handler(event):
    if event.sender_id not in admins:
        return await event.reply("🚫 Not authorized.")
    user_states[event.sender_id] = {"step": "awaiting_phone"}
    await event.respond("📞 Please enter your **phone number** (with country code).", buttons=Button.clear())

# === Session Handler ===
@bot.on(events.NewMessage())
async def handle_session_flow(event):
    user_id = event.sender_id
    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state["step"] == "awaiting_phone":
        phone = event.raw_text.strip()
        state["phone"] = phone
        state["session"] = StringSession()
        state["client"] = TelegramClient(state["session"], BOT_API_ID, BOT_API_HASH)

        try:
            await state["client"].connect()
            await state["client"].send_code_request(phone)
            state["step"] = "awaiting_code"
            await event.reply("📨 Code sent! Please enter the **login code**.")
        except PhoneNumberInvalidError:
            await event.reply("❌ Invalid phone number. Please try `/gen` again.")
            user_states.pop(user_id)
        except Exception as e:
            await event.reply(f"❌ Error: {e}")
            user_states.pop(user_id)

    elif state["step"] == "awaiting_code":
        code = event.raw_text.strip()
        phone = state["phone"]
        try:
            await state["client"].sign_in(phone=phone, code=code)
            await finalize_session(user_id, event)
        except SessionPasswordNeededError:
            state["step"] = "awaiting_password"
            await event.reply("🔐 2FA enabled. Please enter your **password**.")
        except PhoneCodeInvalidError:
            await event.reply("❌ Invalid code. Please try `/gen` again.")
            user_states.pop(user_id)
        except Exception as e:
            await event.reply(f"❌ Error: {e}")
            user_states.pop(user_id)

    elif state["step"] == "awaiting_password":
        password = event.raw_text.strip()
        try:
            await state["client"].sign_in(password=password)
            await finalize_session(user_id, event)
        except Exception as e:
            await event.reply(f"❌ 2FA failed: {e}")
            user_states.pop(user_id)

async def finalize_session(user_id, event):
    state = user_states[user_id]
    client = state["client"]
    session_string = client.session.save()

    me = await client.get_me()
    session_name = f"{me.id}_{me.username or 'user'}"
    session_path = os.path.join(ACCOUNTS_DIR, f"{session_name}.session")

    with open(session_path, "wb") as f:
        client.session.save(f)

    if session_name not in config["accounts"]:
        config["accounts"].append(session_name)
        save_config(config)

    await client.disconnect()
    user_states.pop(user_id)

    await event.respond(
        f"✅ Session saved for {me.first_name} (@{me.username or 'N/A'})\n\nClick to reveal the string session:",
        buttons=[Button.inline("🔑 Reveal String", data=f"show_string:{session_name}")]
    )

# === Reveal String Handler ===
@bot.on(events.CallbackQuery(data=lambda d: d.decode().startswith("show_string:")))
async def reveal_string(event):
    if event.sender_id not in admins:
        return await event.answer("🚫 Not authorized.", alert=True)

    session_key = event.data.decode().split(":")[1]
    path = os.path.join(ACCOUNTS_DIR, f"{session_key}.session")

    if not os.path.exists(path):
        return await event.edit("❌ Session not found.")

    temp_client = TelegramClient(path, BOT_API_ID, BOT_API_HASH)
    await temp_client.connect()
    session_string = temp_client.session.save()
    await temp_client.disconnect()

    await event.edit(f"🔐 **String Session:**\n\n`{session_string}`\n\n⚠️ Keep this private!")

# === /addgroup Command ===
@bot.on(events.NewMessage(pattern=r"^/addgroup"))
async def add_group(event):
    if event.sender_id not in admins:
        return await event.reply("🚫 Not authorized.")
    if not event.is_group:
        return await event.reply("❌ This command must be used in a group.")
    group_id = event.chat_id
    if group_id not in config["groups"]:
        config["groups"].append(group_id)
        save_config(config)
        await event.reply("✅ Group added.")
    else:
        await event.reply("⚠️ Already added.")

# === /removegroup Command ===
@bot.on(events.NewMessage(pattern=r"^/removegroup"))
async def remove_group(event):
    if event.sender_id not in admins:
        return await event.reply("🚫 Not authorized.")
    if not event.is_group:
        return await event.reply("❌ This command must be used in a group.")
    group_id = event.chat_id
    if group_id in config["groups"]:
        config["groups"].remove(group_id)
        save_config(config)
        await event.reply("✅ Removed.")
    else:
        await event.reply("⚠️ Not found.")

# === Auto Forwarder ===
async def auto_forwarder(session_name):
    session_path = os.path.join(ACCOUNTS_DIR, f"{session_name}.session")
    client = TelegramClient(session_path, BOT_API_ID, BOT_API_HASH)
    await client.start()

    while True:
        try:
            messages = await client(GetHistoryRequest(peer='me', limit=20, offset_id=0,
                                                      max_id=0, min_id=0, add_offset=0, hash=0))
            if not messages.messages:
                await asyncio.sleep(60)
                continue

            msg = random.choice(messages.messages)
            for group_id in config["groups"]:
                try:
                    await client.forward_messages(group_id, msg)
                    print(f"[{session_name}] Forwarded to {group_id}")
                except Exception as e:
                    print(f"[{session_name}] Forward failed: {e}")

            await asyncio.sleep(random.randint(60, 300))
        except Exception as e:
            print(f"[{session_name}] Error: {e}")
            await asyncio.sleep(120)

# === Start Everything ===
async def start_all():
    await bot.start()
    tasks = [asyncio.create_task(auto_forwarder(session)) for session in config["accounts"]]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(start_all())

