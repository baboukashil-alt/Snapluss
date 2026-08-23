import discord
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.environ.get("TOKEN")  # mis dans les variables Railway

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# sessions en attente { session_id: { "step": 1, "channel_id": ..., "message_id": ... } }
sessions = {}

class ValidationView(discord.ui.View):
    def __init__(self, session_id, step):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.step = step

    @discord.ui.button(label="✅ Valider", style=discord.ButtonStyle.success)
    async def valider(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=f"✅ **Étape {self.step} validée** par {interaction.user.mention}",
            embed=interaction.message.embeds[0] if interaction.message.embeds else None,
            view=None
        )
        # marque la session comme validée
        if self.session_id in sessions:
            sessions[self.session_id]["status"] = "validated"

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=f"❌ **Étape {self.step} refusée** par {interaction.user.mention}",
            embed=interaction.message.embeds[0] if interaction.message.embeds else None,
            view=None
        )
        if self.session_id in sessions:
            sessions[self.session_id]["status"] = "refused"

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sync: {len(synced)}")
    except Exception as e:
        print(e)

# endpoint HTTP pour que le site puisse poll le statut
from aiohttp import web
import asyncio

async def handle_status(request):
    session_id = request.match_info.get("session_id")
    if session_id in sessions:
        return web.json_response({"status": sessions[session_id].get("status", "pending")})
    return web.json_response({"status": "pending"})

async def handle_step(request):
    data = await request.json()
    session_id = data.get("session_id")
    step = data.get("step", 1)
    embed_data = data.get("embed", {})
    channel_id = int(os.environ.get("CHANNEL_ID", 0))

    sessions[session_id] = {"status": "pending", "step": step}

    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title=embed_data.get("title", "Nouvelle demande"),
            description=embed_data.get("description", ""),
            color=embed_data.get("color", 0xFFFC00)
        )
        for field in embed_data.get("fields", []):
            embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", True))
        embed.set_footer(text=f"Snap+ · Session {session_id}")

        view = ValidationView(session_id, step)
        await channel.send(embed=embed, view=view)

    return web.json_response({"ok": True})

async def start_web():
    app = web.Application()
    app.router.add_get("/status/{session_id}", handle_status)
    app.router.add_post("/step", handle_step)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()
    print("Serveur web démarré")

async def main():
    async with bot:
        await start_web()
        await bot.start(TOKEN)

asyncio.run(main())
