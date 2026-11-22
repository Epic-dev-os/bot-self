import io
import random
import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageOps
from utils.storage import load_config
from utils.theme import UI

RIZZ = [
    "Are you a Wi-Fi signal? Because I'm feeling a strong connection.",
    "Do you have a map? I just got lost in your profile.",
    "Even my bot's latency drops when you show up.",
]


class AlertsTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _alerts(self):
        return self.bot.store.load("alerts", {
            "msg_hook": "", "msg_on": False,
            "mention_hook": "", "mention_on": False,
            "kw_hook": "", "kw_on": False, "keywords": [],
            "role_hook": "", "role_on": False, "roles": [],
        })

    async def _post_hook(self, url: str, title: str, desc: str, color: int = 0x5865F2):
        if not url:
            return
        async with aiohttp.ClientSession() as s:
            try:
                await s.post(url, json={"embeds": [{"title": title, "description": desc, "color": color}]}, timeout=8)
            except Exception:
                pass

    @commands.command(name="setmsghook")
    async def setmsghook(self, ctx, url: str):
        a = self._alerts(); a["msg_hook"] = url; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Message log webhook saved."))

    @commands.command(name="startmsglog")
    async def startmsglog(self, ctx):
        a = self._alerts(); a["msg_on"] = True; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Message logging **ON**."))

    @commands.command(name="stopmsglog")
    async def stopmsglog(self, ctx):
        a = self._alerts(); a["msg_on"] = False; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Message logging **OFF**."))

    @commands.command(name="msglogstatus")
    async def msglogstatus(self, ctx):
        a = self._alerts()
        await self.bot.reply(ctx, UI.status(f"Message Logging: `{'ON' if a['msg_on'] else 'OFF'}`"))

    @commands.command(name="setmentionhook")
    async def setmentionhook(self, ctx, url: str):
        a = self._alerts(); a["mention_hook"] = url; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Mention alert webhook saved."))

    @commands.command(name="mentionon")
    async def mentionon(self, ctx):
        a = self._alerts(); a["mention_on"] = True; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Mention alerts **ON**."))

    @commands.command(name="mentionoff")
    async def mentionoff(self, ctx):
        a = self._alerts(); a["mention_on"] = False; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Mention alerts **OFF**."))

    @commands.command(name="setkeywordhook")
    async def setkeywordhook(self, ctx, url: str):
        a = self._alerts(); a["kw_hook"] = url; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Keyword alert webhook saved."))

    @commands.command(name="addkeyword")
    async def addkeyword(self, ctx, *, word: str):
        a = self._alerts()
        if word.lower() not in a["keywords"]:
            a["keywords"].append(word.lower())
        self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status(f"Added keyword `{word}`."))

    @commands.command(name="removekeyword")
    async def removekeyword(self, ctx, *, word: str):
        a = self._alerts()
        a["keywords"] = [w for w in a["keywords"] if w != word.lower()]
        self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status(f"Removed keyword `{word}`."))

    @commands.command(name="keywordon")
    async def keywordon(self, ctx):
        a = self._alerts(); a["kw_on"] = True; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Keyword alerts **ON**."))

    @commands.command(name="keywordoff")
    async def keywordoff(self, ctx):
        a = self._alerts(); a["kw_on"] = False; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Keyword alerts **OFF**."))

    @commands.command(name="keywordlist")
    async def keywordlist(self, ctx):
        a = self._alerts()
        await self.bot.reply(ctx, UI.card("Tracked Keywords", [("Status", "`ON`" if a["kw_on"] else "`OFF`"), ("Words", ", ".join(f"`{w}`" for w in a["keywords"]) or "None")], icon="eye"))

    @commands.command(name="setrolepinghook")
    async def setrolepinghook(self, ctx, url: str):
        a = self._alerts(); a["role_hook"] = url; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Roleping webhook saved."))

    @commands.command(name="addroleping")
    async def addroleping(self, ctx, role_id: str):
        a = self._alerts()
        if role_id not in a["roles"]:
            a["roles"].append(role_id)
        self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status(f"Tracking role ID `{role_id}`."))

    @commands.command(name="removeroleping")
    async def removeroleping(self, ctx, role_id: str):
        a = self._alerts()
        a["roles"] = [r for r in a["roles"] if r != role_id]
        self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status(f"Removed role ID `{role_id}`."))

    @commands.command(name="rolepingon")
    async def rolepingon(self, ctx):
        a = self._alerts(); a["role_on"] = True; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Roleping alerts **ON**."))

    @commands.command(name="rolepingoff")
    async def rolepingoff(self, ctx):
        a = self._alerts(); a["role_on"] = False; self.bot.store.save("alerts", a)
        await self.bot.reply(ctx, UI.status("Roleping alerts **OFF**."))

    @commands.command(name="rolepinglist")
    async def rolepinglist(self, ctx):
        a = self._alerts()
        await self.bot.reply(ctx, UI.card("Tracked Role Pings", [("Status", "`ON`" if a["role_on"] else "`OFF`"), ("Roles", ", ".join(f"`{r}`" for r in a["roles"]) or "None")], icon="eye"))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        a = self._alerts()
        if a["msg_on"] and a["msg_hook"] and message.content:
            await self._post_hook(a["msg_hook"], "Message Deleted", f"**Author:** {message.author}\n**Channel:** {message.channel}\n**Content:** {message.content}", 0xED4245)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        a = self._alerts()
        if a["msg_on"] and a["msg_hook"] and before.content != after.content:
            await self._post_hook(a["msg_hook"], "Message Edited", f"**Author:** {before.author}\n**Before:** {before.content}\n**After:** {after.content}", 0xFEE75C)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.bot.user or message.author.id == self.bot.user.id:
            return
        a = self._alerts()
        if a["mention_on"] and self.bot.user in message.mentions:
            await self._post_hook(a["mention_hook"], "Mention Alert", f"**From:** {message.author}\n**Message:** {message.content}\n[Jump]({message.jump_url})")
        if a["kw_on"] and any(k in message.content.lower() for k in a["keywords"]):
            await self._post_hook(a["kw_hook"], "Keyword Match", f"**From:** {message.author}\n**Message:** {message.content}\n[Jump]({message.jump_url})", 0x57F287)
        if a["role_on"] and any(str(r.id) in a["roles"] for r in message.role_mentions):
            await self._post_hook(a["role_hook"], "Role Ping Alert", f"**From:** {message.author}\n**Message:** {message.content}\n[Jump]({message.jump_url})", 0xEB459E)

    @commands.command(name="checkmcip")
    async def checkmcip(self, ctx, ip: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.mcsrvstat.us/3/{ip}", timeout=10) as r:
                d = await r.json()
        online = d.get("online", False)
        players = f"{d.get('players', {}).get('online', 0)}/{d.get('players', {}).get('max', 0)}" if online else "0/0"
        await self.bot.reply(ctx, UI.card(f"Minecraft Server ▸ {ip}", [("Status", "`ONLINE`" if online else "`OFFLINE`"), ("Players", f"`{players}`"), ("Version", f"`{d.get('version', 'N/A')}`")], icon="diamond"))

    @commands.command(name="checkurl")
    async def checkurl(self, ctx, url: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(url, allow_redirects=True, timeout=10) as r:
                await self.bot.reply(ctx, UI.card("URL Inspector", [("Status", f"`HTTP {r.status}`"), ("Final URL", f"`{str(r.url)}`")], icon="eye"))

    @commands.command(name="checkpromo")
    async def checkpromo(self, ctx, link: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(link, allow_redirects=True, timeout=10) as r:
                await self.bot.reply(ctx, UI.card("Promo Link Check", [("HTTP Code", f"`{r.status}`"), ("Destination", f"`{str(r.url)[:90]}`")], icon="spark"))

    @commands.command(name="ai")
    async def ai_chat(self, ctx, *, prompt: str):
        cfg = load_config()
        key = cfg.get("ai_api_key", "").strip()
        if not key:
            return await self.bot.reply(ctx, UI.status("Set `ai_api_key` in `config.json` to use `.ai`.", False))
        mem = self.bot.store.load("ai", {"system": "You are a concise, helpful assistant.", "history": []})
        mem["history"].append({"role": "user", "content": prompt})
        msgs = [{"role": "system", "content": mem["system"]}] + mem["history"][-10:]
        async with aiohttp.ClientSession() as s:
            async with s.post(cfg["ai_base_url"], headers={"Authorization": f"Bearer {key}"}, json={"model": cfg.get("ai_model", "gpt-4o-mini"), "messages": msgs}, timeout=25) as r:
                d = await r.json()
        reply = d["choices"][0]["message"]["content"]
        mem["history"].append({"role": "assistant", "content": reply})
        self.bot.store.save("ai", mem)
        await self.bot.reply(ctx, reply[:1950])

    @commands.command(name="resetai")
    async def resetai(self, ctx):
        mem = self.bot.store.load("ai", {"system": "You are a concise, helpful assistant.", "history": []})
        mem["history"] = []
        self.bot.store.save("ai", mem)
        await self.bot.reply(ctx, UI.status("AI memory cleared."))

    @commands.command(name="setprompt")
    async def setprompt(self, ctx, *, system_prompt: str):
        mem = self.bot.store.load("ai", {"system": "", "history": []})
        mem["system"] = system_prompt
        self.bot.store.save("ai", mem)
        await self.bot.reply(ctx, UI.status("Updated AI system prompt."))

    @commands.command(name="resetprompt")
    async def resetprompt(self, ctx):
        mem = self.bot.store.load("ai", {"system": "", "history": []})
        mem["system"] = "You are a concise, helpful assistant."
        self.bot.store.save("ai", mem)
        await self.bot.reply(ctx, UI.status("Reset AI system prompt."))

    @commands.command(name="showprompt")
    async def showprompt(self, ctx):
        mem = self.bot.store.load("ai", {"system": "Default"})
        await self.bot.reply(ctx, UI.card("AI System Prompt", [("Prompt", f"`{mem.get('system')}`")], icon="spark"))

    @commands.command(name="rizz")
    async def rizz(self, ctx, user: discord.User):
        await self.bot.reply(ctx, f"{user.mention} {random.choice(RIZZ)}")

    @commands.command(name="joke")
    async def joke(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://official-joke-api.appspot.com/random_joke", timeout=8) as r:
                d = await r.json()
        await self.bot.reply(ctx, UI.card("Joke", [("Setup", d["setup"]), ("Punchline", f"||{d['punchline']}||")], icon="star"))

    @commands.command(name="meme")
    async def meme(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://meme-api.com/gimme", timeout=8) as r:
                d = await r.json()
        await self.bot.reply(ctx, f"**{d['title']}**\n{d['url']}")

    async def _avatar_fx(self, ctx, user: discord.User | None, mode: str):
        t = user or ctx.author
        async with aiohttp.ClientSession() as s:
            async with s.get(t.display_avatar.url, timeout=10) as r:
                raw = await r.read()
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if mode == "blurpify":
            im = ImageOps.colorize(ImageOps.grayscale(im), black="#23272A", white="#5865F2")
        else:
            im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(4.0)).enhance(3.0)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        await self.bot.reply(ctx, file=discord.File(buf, f"{mode}.png"))

    @commands.command(name="blurpify")
    async def blurpify(self, ctx, user: discord.User | None = None):
        await self._avatar_fx(ctx, user, "blurpify")

    @commands.command(name="deepfry")
    async def deepfry(self, ctx, user: discord.User | None = None):
        await self._avatar_fx(ctx, user, "deepfry")


async def setup(bot):
    await bot.add_cog(AlertsTools(bot))