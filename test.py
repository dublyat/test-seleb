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


# Global flag to control the forwarding process
is_forwarding_active = False

# Initialize the Telegram client
# Function to forward a random message from saved messages
async def forward_random_message():
    global is_forwarding_active
    group_index = 0  # Start by sending to the first group (index 0)

    while is_forwarding_active:
        # Fetch saved messages (this can be adjusted to any message you want)
        saved_messages = await client.get_messages('me', limit=10)  # 'me' is the Saved Messages

        if saved_messages:
            random_message = random.choice(saved_messages)  # Pick a random message
            target_group = TARGET_GROUPS[group_index]  # Pick the current target group

            # Forward the message to the chosen group/channel
            await client.send_message(target_group, random_message.text)
            print(f"Forwarded message to {target_group}: {random_message.text}")

            # Switch to the next group (loop between the two groups)
            group_index = 1 - group_index  # Toggle between 0 and 1

            # Set random interval between 5 and 30 minutes
            random_interval = random.randint(300, 1800)  # 5 to 30 minutes
            await asyncio.sleep(random_interval)

# Command to start the forwarding process
@client.on(events.NewMessage(pattern='/start'))
async def start_forwarding(event):
    global is_forwarding_active
    if not is_forwarding_active:
        is_forwarding_active = True
        await event.respond("Forwarding started...")
        print("Forwarding started.")
        # Start forwarding in a separate task (loop)
        loop = asyncio.get_event_loop()
        loop.create_task(forward_random_message())
    else:
        await event.respond("Forwarding is already running.")

# Command to stop the forwarding process
@client.on(events.NewMessage(pattern='/stop'))
async def stop_forwarding(event):
    global is_forwarding_active
    if is_forwarding_active:
        is_forwarding_active = False
        await event.respond("Forwarding stopped.")
        print("Forwarding stopped.")
    else:
        await event.respond("No forwarding process is running.")

# Main function to start the client
async def main():
    await client.start(phone_number)  # Starts the client and logs in
    print("Logged in successfully.")
    await client.run_until_disconnected()  # Run the client until you manually stop it

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
