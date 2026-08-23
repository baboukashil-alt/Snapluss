import nextcord as discord
from nextcord.ext import commands
from aiohttp import web
import asyncio
import os

TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

sessions = {}

class ValidationView(discord.ui.View):
    def __init__(self, session_id, step):
        super().__init__(timeout=600)
        self.session_id = session_id
        self.step = step

    @discord.ui.button(label="✅ Valider", style=discord.ButtonStyle.success)
    async def valider(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessions[self.session_id] = "validated"
        for item in self.children:
            item.disabled = True
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        await interaction.response.edit_message(content=f"✅ Validé par {interaction.user.mention}", embed=embed, view=self)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessions[self.session_id] = "refused"
        for item in self.children:
            item.disabled = True
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        await interaction.response.edit_message(content=f"❌ Refusé par {interaction.user.mention}", embed=embed, view=self)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")

async def handle_status(request):
    sid = request.match_info.get("session_id")
    return web.json_response({"status": sessions.get(sid, "pending")})

async def handle_step(request):
    data = await request.json()
    sid = data.get("session_id")
    step = data.get("step", 1)
    embed_data = data.get("embed", {})
    sessions[sid] = "pending"
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=embed_data.get("title", "Nouvelle demande"),
            description=embed_data.get("description", ""),
            color=embed_data.get("color", 0xFFFC00)
        )
        for f in embed_data.get("fields", []):
            embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", True))
        embed.set_footer(text=f"Snap+ · Session {sid}")
        view = ValidationView(sid, step)
        await channel.send(embed=embed, view=view)
    return web.json_response({"ok": True})

async def handle_notify(request):
    data = await request.json()
    embed_data = data.get("embed", {})
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=embed_data.get("title", "Notification"),
            description=embed_data.get("description", ""),
            color=embed_data.get("color", 0x00cc66)
        )
        for f in embed_data.get("fields", []):
            embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", True))
        embed.set_footer(text="Snap+ Staff Panel")
        await channel.send(embed=embed)
    return web.json_response({"ok": True})

async def start_web():
    app = web.Application()
    app.router.add_get("/status/{session_id}", handle_status)
    app.router.add_post("/step", handle_step)
    app.router.add_post("/notify", handle_notify)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"✅ Web démarré port {port}")

async def main():
    await start_web()
    await bot.start(TOKEN)

asyncio.run(main())
