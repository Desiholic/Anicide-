import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import threading
import asyncio

# OTHER BOT SCRIPTS WILL BE RAN AFTER THE BOT IS INITIALLY RUN
import moderation
import starboard

load_dotenv()

# Get setting values
TOKEN = os.getenv("BOT_TOKEN")

# Create intents & initialize Client
Intents = discord.Intents.all()
Intents.message_content = True

Client = commands.Bot(command_prefix="/", intents=Intents)

@Client.event
async def on_ready():
    print("Client ready")

    await Client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="discord.gg/anicide"))

    await asyncio.sleep(1)

    # Multi-threading
    def thread_task_moderation():
        asyncio.run(moderation.main(Client))
    moderation_t = threading.Thread(target=thread_task_moderation)
    moderation_t.start()


    def thread_task_starboard():
        asyncio.run(starboard.main(Client))
    starboard_t = threading.Thread(target=thread_task_starboard)
    starboard_t.start()

    # Wait for each thread to finish successfully, then syncing all the slash commands together
    moderation_t.join()
    starboard_t.join()

    print("Initializing slash commands...")
    await Client.tree.sync()
    print("Slash commands initiated!")

Client.run(TOKEN)