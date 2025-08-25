import random
import time
import asyncio
from telethon import TelegramClient, events

api_id = '28119255'  
api_hash = '337f330b7ab0c169c6296bc80338c6fd'   
phone_number = '+6283185102534'

TARGET_GROUPS = ['@botkontol_eror', -1003031999070]

# Initialize the client
client = TelegramClient('auto_forward_bot', api_id, api_hash)


is_forwarding_active = False

async def forward_random_message():
    global is_forwarding_active
    group_index = 0

    while is_forwarding_active:
        saved_messages = await client.get_messages('me', limit=10)
        if saved_messages:
            msg = random.choice(saved_messages)
            target = TARGET_GROUPS[group_index]

            # Properly forward the message (preserves original headers and formatting)
            await client.forward_messages(
                target,
                msg.id,
                from_peer='me'  # Source is your 'Saved Messages' (Saved Messages = 'me')
            )
            print(f"Forwarded message ID {msg.id} to {target}")

            # Toggle which group to forward to next
            group_index = 1 - group_index

            # Wait for a random interval between 5 and 30 minutes
            await asyncio.sleep(random.randint(300, 1800))

@client.on(events.NewMessage(pattern='/start'))
async def start_forwarding(event):
    global is_forwarding_active
    if not is_forwarding_active:
        is_forwarding_active = True
        await event.respond("Forwarding started...")
        asyncio.get_event_loop().create_task(forward_random_message())
    else:
        await event.respond("Forwarding is already running.")

@client.on(events.NewMessage(pattern='/stop'))
async def stop_forwarding(event):
    global is_forwarding_active
    if is_forwarding_active:
        is_forwarding_active = False
        await event.respond("Forwarding stopped.")
    else:
        await event.respond("No forwarding process is running.")

async def main():
    await client.start(phone_number)
    print("Logged in successfully.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

