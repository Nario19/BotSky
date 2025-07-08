import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import yt_dlp
import wikipedia
import datetime
import asyncio
import random
import requests

# ---------------- CONFIG ----------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

HEADERS = {"x-apisports-key": FOOTBALL_API_KEY}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------- UTILIDADES --------------

def yt_search_link(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={'+'.join(query.split())}"

# -------------- MÚSICA (YT‑DLP) ---------

def get_audio_url(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return info["url"], info["title"]

@bot.command()
async def play(ctx, *, query):
    if ctx.author.voice is None:
        return await ctx.send("Debes estar en un canal de voz.")
    canal = ctx.author.voice.channel
    if ctx.voice_client is None:
        await canal.connect()
    elif ctx.voice_client.channel != canal:
        await ctx.voice_client.move_to(canal)
    try:
        url, title = get_audio_url(query)
        ctx.voice_client.stop()
        source = discord.FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        ctx.voice_client.play(source, after=lambda e: None)
        await ctx.send(f"🎵 Reproduciendo: **{title}**")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹️ Música detenida.")

@bot.command()
async def salir(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🚪 Bot salió del canal de voz.")

# -------------- COMANDOS GENERALES ------

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "hola" in message.content.lower():
        await message.channel.send(f"👋 Hola {message.author.name}!")
    await bot.process_commands(message)

@bot.command()
async def wiki(ctx, *, termino):
    try:
        resumen = wikipedia.summary(termino, sentences=2, auto_suggest=False)
        await ctx.send(f"📚 {resumen}")
    except Exception:
        await ctx.send("❌ No se encontró el término.")

@bot.command()
async def yt(ctx, *, busqueda):
    await ctx.send(f"🔍 {yt_search_link(busqueda)}")

@bot.command()
async def hora(ctx):
    await ctx.send(f"🕒 Hora UTC: {datetime.datetime.utcnow().strftime('%H:%M:%S')}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 ¡Pong!")

@bot.command()
async def temporizador(ctx, segundos: int):
    await ctx.send(f"⏰ Temporizador de {segundos} s iniciado...")
    await asyncio.sleep(segundos)
    await ctx.send("⏱️ ¡Tiempo!")

@bot.command()
async def dado(ctx):
    await ctx.send(f"🎲 Salió: **{random.randint(1,6)}**")

@bot.command()
async def encuesta(ctx, *, pregunta):
    msg = await ctx.send(f"📊 {pregunta}\n✅ = Sí | ❌ = No")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

# -------------- FÚTBOL (API‑SPORTS) -----

IMPORTANT_COUNTRIES = ["England", "Spain", "Germany", "Italy", "France", "Netherlands", "Argentina", "Brazil", "Portugal"]

@bot.command()
async def partidoshoy(ctx):
    try:
        hoy = datetime.datetime.now().strftime('%Y-%m-%d')
        res = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS,
                           params={"date": hoy, "timezone": "America/Lima"}, timeout=10).json()
        juegos = [f for f in res.get("response", []) if f["league"]["country"] in IMPORTANT_COUNTRIES]
        if not juegos:
            return await ctx.send("❌ No hay partidos importantes hoy.")
        texto = f"📅 **Partidos importantes hoy ({hoy}):**\n"
        for f in juegos:
            h,a = f['teams']['home']['name'], f['teams']['away']['name']
            hora = f['fixture']['date'][11:16]
            texto += f"- {h} vs {a} ({hora})\n"
        await ctx.send(texto)
    except Exception as e:
        await ctx.send(f"❌ Error al obtener partidos: {e}")

@bot.command()
async def liga(ctx, *, nombre):
    try:
        search = requests.get("https://v3.football.api-sports.io/leagues", headers=HEADERS,
                              params={"search": nombre}, timeout=10).json()
        if not search["response"]:
            return await ctx.send("❌ Liga no encontrada.")
        lid = search["response"][0]["league"]["id"]
        hoy = datetime.datetime.now().strftime('%Y')
        fixtures = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS,
                                params={"league": lid, "season": hoy, "next": 5}, timeout=10).json()
        if not fixtures["response"]:
            return await ctx.send("❌ No hay partidos próximos en esta liga.")
        texto = f"🏟️ Próximos partidos en {nombre.title()}:\n"
        for f in fixtures["response"]:
            h,a = f['teams']['home']['name'], f['teams']['away']['name']
            fecha = f['fixture']['date'][:10]
            texto += f"- {h} vs {a} ({fecha})\n"
        await ctx.send(texto)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def cuotas(ctx, *, equipo):
    try:
        t = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS,
                          params={"search": equipo}, timeout=10).json()
        if not t["response"]:
            return await ctx.send("❌ Equipo no encontrado.")
        tid = t["response"][0]["team"]["id"]

        def buscar(partido_param):
            fx = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS,
                              params={"team": tid, **partido_param}, timeout=10).json()
            for f in fx["response"]:
                oid = f['fixture']['id']
                odds = requests.get("https://v3.football.api-sports.io/odds", headers=HEADERS,
                                    params={"fixture": oid}, timeout=10).json()
                if odds["response"]:
                    return f, odds["response"][0]
            return None, None

        fixture, odata = buscar({"last": 5})
        if fixture is None:
            fixture, odata = buscar({"next": 5})
        if fixture is None:
            return await ctx.send("❌ Sin cuotas disponibles para este equipo.")

        h,a = fixture['teams']['home']['name'], fixture['teams']['away']['name']
        fecha = fixture['fixture']['date'][:16].replace('T',' ')
        vals = odata['bookmakers'][0]['bets'][0]['values']
        texto = f"📊 **Cuotas {h} vs {a} ({fecha})**\n"
        for v in vals:
            texto += f"- {v['value']}: {v['odd']}\n"
        await ctx.send(texto)
    except Exception as e:
        await ctx.send(f"❌ Error al obtener cuotas: {e}")

# -------------- INFO --------------------

@bot.command()
async def info(ctx):
    embed = discord.Embed(title="🤖 Comandos del Bot", description="Lista de comandos disponibles:", color=discord.Color.blue())
    embed.add_field(name="🎵 Música", value="""
`!play <nombre o URL>` – Reproduce música desde YouTube
`!pause` – Pausa la canción actual
`!resume` – Reanuda la música
`!stop` – Detiene la música
`!salir` – Sale del canal de voz
""", inline=False)

    embed.add_field(name="🔍 Utilidades", value="""
`!wiki <término>` – Busca información en Wikipedia
`!yt <término>` – Busca en YouTube
`!hora` – Hora actual (UTC)
`!ping` – Verifica actividad
`!temporizador <segundos>` – Alarma
`!dado` – Lanza un dado
`!encuesta <pregunta>` – Encuesta con reacciones
""", inline=False)

    embed.add_field(name="🏟️ Deportes", value="""
`!cuotas <equipo>` – Muestra cuotas del próximo o último partido del equipo
`!liga <nombre>` – Lista partidos de una liga
`!partidoshoy` – Muestra partidos importantes del día
""", inline=False)

    embed.add_field(name="🎭 Extra", value="""
Escribe "hola" – El bot te saluda
""", inline=False)

    embed.set_footer(text="Usa los comandos con ! al inicio.")
    await ctx.send(embed=embed)

bot.run(TOKEN)
