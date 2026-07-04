import os
import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_ALERT_CHANNEL_ID = os.getenv("DISCORD_ALERT_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup Gemini AI Client using the new SDK
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY is not set in .env.")
    client = None

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

API_BASE = "http://localhost:8000/api"
alerted_devices = set()

class EcoActionView(discord.ui.View):
    def __init__(self, device_id: str, timeout: float = 15.0):
        super().__init__(timeout=timeout)
        self.device_id = device_id
        self.responded = False

    async def on_timeout(self):
        if not self.responded:
            self.responded = True
            async with aiohttp.ClientSession() as session:
                await session.post(f"{API_BASE}/eco/resolve/{self.device_id}", json={"action": "turn_off"})
            
            for child in self.children:
                child.disabled = True
            
            try:
                await self.message.edit(content="⚠️ No response received within 15 seconds. Auto-shutdown protocol executed.", view=None)
            except Exception as e:
                print(f"Error editing message on timeout: {e}")

    @discord.ui.button(label="Approve Shutdown", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.responded = True
        for child in self.children:
            child.disabled = True
            
        async with aiohttp.ClientSession() as session:
            await session.post(f"{API_BASE}/eco/resolve/{self.device_id}", json={"action": "turn_off"})
            
        await interaction.response.edit_message(content=f"Shutdown approved for {self.device_id}.", view=None)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.responded = True
        for child in self.children:
            child.disabled = True
            
        async with aiohttp.ClientSession() as session:
            await session.post(f"{API_BASE}/eco/resolve/{self.device_id}", json={"action": "ignore"})
            
        await interaction.response.edit_message(content=f"Shutdown denied for {self.device_id}. Device remains ON.", view=None)

@tasks.loop(seconds=5)
async def eco_polling():
    print("Bot eco_polling loop running... checking backend.")
    if not DISCORD_ALERT_CHANNEL_ID:
        print("Warning: DISCORD_ALERT_CHANNEL_ID is not set.")
        return
        
    try:
        data = await fetch_json(f"{API_BASE}/eco/pending")
        if data and "pending_approvals" in data:
            pending = data["pending_approvals"]
            if pending:
                print(f"Found {len(pending)} pending approval(s) from backend.")
            channel = bot.get_channel(int(DISCORD_ALERT_CHANNEL_ID))
            if not channel:
                print(f"Error: Could not find Discord channel with ID {DISCORD_ALERT_CHANNEL_ID}. Ensure bot has access.")
                return
                
            for dev in pending:
                if dev["id"] not in alerted_devices:
                    alerted_devices.add(dev["id"])
                    
                    view = EcoActionView(device_id=dev["id"])
                    msg = await channel.send(f"⚠️ **Eco-Mode Alert** ⚠️\n{dev['room']} {dev['type']} ({dev['id']}) has been ON for over 30 minutes (simulated). Action required!", view=view)
                    view.message = msg
                    
    except Exception as e:
        print(f"Error in eco_polling: {e}")

@eco_polling.before_loop
async def before_eco_polling():
    await bot.wait_until_ready()

async def fetch_json(url: str):
    """Fetches JSON data from the backend with error handling and timeout."""
    try:
        timeout = aiohttp.ClientTimeout(total=5) # 5 seconds timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        print(f"Backend fetch error: {e}")
        return None

async def generate_human_response(raw_data: str) -> str:
    """Passes the raw JSON data to Gemini to get a friendly response."""
    if not client:
        return f"I'm sorry Boss, but my AI core is offline (Missing API Key). Here is the raw data:\n```json\n{raw_data}\n```"
    
    try:
        # Construct the system instructions using the new GenerateContentConfig
        config = types.GenerateContentConfig(
            system_instruction="You are a helpful, friendly, and conversational office assistant. Translate this raw JSON office energy data into a natural, concise, and polite response for The Boss. Do not output raw JSON, markdown tables, or robotic lists. Speak naturally."
        )
        
        # Run the synchronous generate_content call in a separate thread to prevent blocking the Discord event loop
        def generate():
            return client.models.generate_content(
                model='gemini-1.5-pro',
                contents=raw_data,
                config=config
            )
            
        response = await asyncio.to_thread(generate)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I'm sorry Boss, I've gathered the sensor data but my communication module is experiencing interference (LLM Error). I'll have it fixed shortly!"

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")
    if not eco_polling.is_running():
        print("Starting eco_polling task in bot...")
        eco_polling.start()

@bot.command(name="status")
async def status(ctx):
    """Returns a summary of devices ON/OFF per room."""
    async with ctx.typing():
        data = await fetch_json(f"{API_BASE}/status")
        if not data:
            await ctx.send("I'm sorry Boss, but I couldn't reach the office monitoring backend. The server might be offline.")
            return
        
        response_text = await generate_human_response(str(data))
        await ctx.send(response_text)

@bot.command(name="room")
async def room(ctx, *, room_name: str):
    """Returns the specific status of a requested room (e.g. !room Drawing Room)."""
    async with ctx.typing():
        data = await fetch_json(f"{API_BASE}/status")
        if not data:
            await ctx.send("I'm sorry Boss, but I couldn't reach the office monitoring backend. The server might be offline.")
            return
        
        room_devices = [d for d in data.get("devices", []) if d["room"].lower() == room_name.lower()]
        
        if not room_devices:
            await ctx.send(f"I couldn't find any devices in a room named '{room_name}'. Please double check the room name!")
            return
        
        room_data_str = str({"room": room_name, "devices": room_devices})
        response_text = await generate_human_response(room_data_str)
        await ctx.send(response_text)

@bot.command(name="usage")
async def usage(ctx):
    """Returns the live total power draw in Watts and estimated daily kWh usage."""
    async with ctx.typing():
        total_data = await fetch_json(f"{API_BASE}/usage/total")
        room_data = await fetch_json(f"{API_BASE}/usage/rooms")
        
        if not total_data or not room_data:
            await ctx.send("I'm sorry Boss, but I couldn't reach the usage endpoints on our backend server.")
            return
            
        combined_data = {
            "total_office_power": total_data,
            "power_by_room": room_data
        }
        
        response_text = await generate_human_response(str(combined_data))
        await ctx.send(response_text)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set. Please add it to your .env file.")
    else:
        bot.run(DISCORD_TOKEN)
