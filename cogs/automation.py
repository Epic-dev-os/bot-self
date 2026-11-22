import asyncio
import re
import time
import discord
from discord.ext import commands, tasks
from utils.storage import load_config
from utils.theme import UI


def parse_duration(text: str) -> int:
    m = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not m:
        raise ValueError("Use format like 30s, 5m, 2h, or 1d")
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]
    return int(m.group(1)) * mult


class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.am_tasks: dict[int, asyncio.Task] = {}
        self.rotator_task: asyncio.Task | None = None
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()
        if self.rotator_task:
            self.rotator_task.cancel()
        for t in self.am_tasks.values():
            t.cancel()

    def _expand_vars(self, text: str, message: discord.Message) -> str:
        cfg = load_config()
        return (
            text.replace("{user}", message.author.mention)
            .replace("{name}", message.author.name)
            .replace("{time}", time.strftime("%H:%M"))
            .replace("{upi}", cfg.get("upi_1", "Not Set"))
        )

    @commands.command(name="afk")
    async def afk(self, ctx, *, reason: str = "AFK"):
        self.bot.store.save("afk", {"active": True, "smart": False, "reason": reason, "since": int(time.time())})
        await self.bot.reply(ctx, UI.card("AFK Enabled", [("Reason", f"`{reason}`")], icon="spark"))

    @commands.command(name="smartafk")
    async def smartafk(self, ctx, *, reason: str = "Away"):
        self.bot.store.save("afk", {"active": True, "smart": True, "reason": reason, "since": int(time.time())})
        await self.bot.reply(ctx, UI.card("Smart AFK Enabled", [("Reason", f"`{reason}`"), ("Auto-Off", "Turns off on your next message")], icon="spark"))

    @commands.command(name="unafk")
    async def unafk(self, ctx):
        self.bot.store.save("afk", {"active": False})
        await self.bot.reply(ctx, UI.status("AFK disabled."))

    @commands.command(name="ar")
    async def ar_add(self, ctx, *, payload: str):
        if "," not in payload:
            return await self.bot.reply(ctx, UI.status("Format: `.ar trigger, response`", False))
        trigger, response = [x.strip() for x in payload.split(",", 1)]
        data = self.bot.store.load("ar", {})
        data[trigger.lower()] = response
        self.bot.store.save("ar", data)
        await self.bot.reply(ctx, UI.status(f"Auto-Reply added for `{trigger}`."))

    @commands.command(name="removear")
    async def ar_del(self, ctx, *, trigger: str):
        data = self.bot.store.load("ar", {})
        data.pop(trigger.lower(), None)
        self.bot.store.save("ar", data)
        await self.bot.reply(ctx, UI.status(f"Removed Auto-Reply `{trigger}`."))

    @commands.command(name="ar_list")
    async def ar_list(self, ctx):
        data = self.bot.store.load("ar", {})
        rows = [(k, f"`{v[:50]}`") for k, v in data.items()] or [("Empty", "No auto-replies configured")]
        await self.bot.reply(ctx, UI.card("Auto-Responder List", rows, icon="gear"))

    @commands.command(name="am")
    async def am_start(self, ctx, interval: str, channel_id: int, *, msg: str):
        secs = max(10, parse_duration(interval))
        if channel_id in self.am_tasks:
            self.am_tasks[channel_id].cancel()

        async def _runner():
            ch = self.bot.get_channel(channel_id)
            while ch:
                try:
                    await ch.send(msg)
                except Exception:
                    pass
                await asyncio.sleep(secs)

        self.am_tasks[channel_id] = asyncio.create_task(_runner())
        am_data = self.bot.store.load("am", {})
        am_data[str(channel_id)] = {"interval": interval, "msg": msg}
        self.bot.store.save("am", am_data)
        await self.bot.reply(ctx, UI.status(f"Auto-Message active in `{channel_id}` every `{interval}`."))

    @commands.command(name="am_stop")
    async def am_stop(self, ctx, channel_id: int):
        t = self.am_tasks.pop(channel_id, None)
        if t:
            t.cancel()
        am_data = self.bot.store.load("am", {})
        am_data.pop(str(channel_id), None)
        self.bot.store.save("am", am_data)
        await self.bot.reply(ctx, UI.status(f"Stopped Auto-Message in `{channel_id}`."))

    @commands.command(name="am_list")
    async def am_list(self, ctx):
        am_data = self.bot.store.load("am", {})
        rows = [(k, f"Every `{v['interval']}` → `{v['msg'][:40]}`") for k, v in am_data.items()] or [("Empty", "None running")]
        await self.bot.reply(ctx, UI.card("Active Auto-Messages", rows, icon="gear"))

    @commands.command(name="reminder")
    async def reminder_add(self, ctx, duration: str, channel_id: int, *, text: str):
        due = int(time.time()) + parse_duration(duration)
        items = self.bot.store.load("remind", [])
        rid = max((i["id"] for i in items), default=0) + 1
        items.append({"id": rid, "due": due, "channel_id": channel_id, "text": text})
        self.bot.store.save("remind", items)
        await self.bot.reply(ctx, UI.status(f"Reminder `#{rid}` scheduled in `{duration}`."))

    @commands.command(name="remindlist")
    async def remind_list(self, ctx):
        items = self.bot.store.load("remind", [])
        rows = [(f"#{i['id']}", f"<t:{i['due']}:R> in `{i['channel_id']}`: `{i['text'][:40]}`") for i in items] or [("None", "No pending reminders")]
        await self.bot.reply(ctx, UI.card("Reminders", rows, icon="spark"))

    @commands.command(name="removeremind")
    async def remind_del(self, ctx, rid: int):
        items = [i for i in self.bot.store.load("remind", []) if i["id"] != rid]
        self.bot.store.save("remind", items)
        await self.bot.reply(ctx, UI.status(f"Removed reminder `#{rid}`."))

    @tasks.loop(seconds=10)
    async def reminder_loop(self):
        items = self.bot.store.load("remind", [])
        now = time.time()
        remaining = []
        changed = False
        for item in items:
            if item["due"] <= now:
                changed = True
                ch = self.bot.get_channel(item["channel_id"])
                if ch:
                    try:
                        await ch.send(UI.card(f"Reminder #{item['id']}", [("Note", item["text"])], icon="bolt"))
                    except Exception:
                        pass
            else:
                remaining.append(item)
        if changed:
            self.bot.store.save("remind", remaining)

    @reminder_loop.before_loop
    async def before_rem(self):
        await self.bot.wait_until_ready()

    @commands.command(name="stream")
    async def stream(self, ctx, *, title: str):
        await self.bot.change_presence(activity=discord.Streaming(name=title, url="https://twitch.tv/discord"))
        await self.bot.reply(ctx, UI.status(f"Streaming: `{title}`"))

    @commands.command(name="play")
    async def play(self, ctx, *, title: str):
        await self.bot.change_presence(activity=discord.Game(name=title))
        await self.bot.reply(ctx, UI.status(f"Playing: `{title}`"))

    @commands.command(name="watch")
    async def watch(self, ctx, *, title: str):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=title))
        await self.bot.reply(ctx, UI.status(f"Watching: `{title}`"))

    @commands.command(name="listen")
    async def listen(self, ctx, *, title: str):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))
        await self.bot.reply(ctx, UI.status(f"Listening to: `{title}`"))

    @commands.command(name="stopactivity")
    async def stopactivity(self, ctx):
        await self.bot.change_presence(activity=None)
        await self.bot.reply(ctx, UI.status("Cleared activity."))

    @commands.command(name="rotate")
    async def rotate(self, ctx, *, items: str):
        entries = [x.strip() for x in items.split(";") if x.strip()]
        if not entries:
            return await self.bot.reply(ctx, UI.status("Separate statuses with `;` e.g. `.rotate Online; Selling Nitro`", False))
        if self.rotator_task:
            self.rotator_task.cancel()

        async def _rot():
            idx = 0
            while True:
                try:
                    await self.bot.change_presence(activity=discord.CustomActivity(name=entries[idx % len(entries)]))
                except Exception:
                    pass
                idx += 1
                await asyncio.sleep(12)

        self.rotator_task = asyncio.create_task(_rot())
        await self.bot.reply(ctx, UI.status(f"Rotating `{len(entries)}` custom statuses every 12s."))

    @commands.command(name="stoprotate")
    async def stoprotate(self, ctx):
        if self.rotator_task:
            self.rotator_task.cancel()
            self.rotator_task = None
        await self.bot.reply(ctx, UI.status("Status rotator stopped."))

    @commands.command(name="setgreet")
    async def setgreet(self, ctx, *, text: str):
        g = self.bot.store.load("greet", {"enabled": False, "text": "", "seen": []})
        g["enabled"], g["text"] = True, text
        self.bot.store.save("greet", g)
        await self.bot.reply(ctx, UI.status("First-DM greeting enabled."))

    @commands.command(name="cleargreet")
    async def cleargreet(self, ctx):
        self.bot.store.save("greet", {"enabled": False, "text": "", "seen": []})
        await self.bot.reply(ctx, UI.status("First-DM greeting disabled."))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.bot.user:
            return

        afk = self.bot.store.load("afk", {"active": False})
        if message.author.id == self.bot.user.id:
            if afk.get("active") and afk.get("smart") and not message.content.startswith(str(self.bot.command_prefix)):
                self.bot.store.save("afk", {"active": False})
            return

        if afk.get("active") and (isinstance(message.channel, discord.DMChannel) or self.bot.user in message.mentions):
            await message.channel.send(UI.card("Currently AFK", [("Reason", afk.get("reason", "AFK")), ("Since", f"<t:{afk.get('since', 0)}:R>")], icon="spark"))

        if isinstance(message.channel, discord.DMChannel):
            g = self.bot.store.load("greet", {"enabled": False, "text": "", "seen": []})
            if g.get("enabled") and message.author.id not in g.get("seen", []):
                g.setdefault("seen", []).append(message.author.id)
                self.bot.store.save("greet", g)
                await message.channel.send(self._expand_vars(g["text"], message))

        ar = self.bot.store.load("ar", {})
        reply = ar.get(message.content.strip().lower())
        if reply:
            await message.channel.send(self._expand_vars(reply, message))


async def setup(bot):
    await bot.add_cog(Automation(bot))