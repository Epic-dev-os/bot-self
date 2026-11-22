import asyncio
import re
import time
import urllib.parse
import aiohttp
import discord
from discord.ext import commands
from utils.storage import load_config
from utils.theme import UI, load_themes

CATEGORIES = {
    "config": "setupi, setupi2, setqr, setqr2, setsrvlink, setuserid, setaddy, setaddy2, setbinid, setltckey, setprefix, autodel, restart, alias",
    "themes": "theme list, theme set <name>, theme preview <name>, setemoji <slot> <emoji>, setbrand <name>",
    "general": "menu, allcmds, selfbot, snipe, esnipe, ghostping, srvinfo, user_info, csrv, yt, meaning, avatar, banner, icon, emojitoimg",
    "upi": "upi, upi2, qr, qr2, upiqr, paycard, vouch, exch, i2cvouch, c2ivouch",
    "deals": "deal add <sell> <buy> <item>, deals, profit, deal clear, math, i2c, c2i, l2u, u2l, e2u, u2e",
    "crypto": "addy, addy2, bal, mybal, mybal2, ltcqr, ltc, btc, sol, usdt, xrp, txidltc, txidbtc, txidtrx, txiddoge, setltchook, watchaddy, unwatchaddy, startdetect, stopdetect, listwatch",
    "auto": "afk, unafk, smartafk, ar, removear, ar_list, am, am_stop, am_list, reminder, remindlist, removeremind, rotate, stoprotate, stream, play, watch, listen, stopactivity, setgreet, cleargreet",
    "mod": "ban, kick, banid, unban, hide, unhide, chnl, role, roleperms, nuke, clear, spam, dm, transcript, spamhook, stopspamhook",
    "vc": "vcjoin, vcleave, vckick, vcmute, vcunmute, vcdeafen, vcundeafen, vcmove, vcmoveall, vclimit",
    "alerts": "setmsghook, startmsglog, stopmsglog, msglogstatus, setmentionhook, mentionon, mentionoff, setkeywordhook, addkeyword, removekeyword, keywordon, keywordoff, keywordlist, setrolepinghook, addroleping, removeroleping, rolepingon, rolepingoff, rolepinglist",
    "tools": "checkmcip, checkurl, checkpromo, ai, resetai, setprompt, resetprompt, showprompt, joke, meme, rizz, blurpify, deepfry",
}


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="menu", aliases=["help", "allcmds"])
    async def menu_cmd(self, ctx, category: str = ""):
        p = ctx.prefix
        cat = category.lower().strip()
        if cat in CATEGORIES:
            cmds = ", ".join(f"`{p}{c.strip()}`" for c in CATEGORIES[cat].split(","))
            msg = UI.card(f"Category ▸ {cat}", [("Commands", cmds)], icon="diamond")
            return await self.bot.reply(ctx, msg)

        msg = UI.card(
            "Command Hub",
            [
                ("Core & Look", f"`{p}menu config` • `{p}menu themes` • `{p}menu general`"),
                ("Money & Deals", f"`{p}menu upi` • `{p}menu deals` • `{p}menu crypto`"),
                ("Automation", f"`{p}menu auto` • `{p}menu alerts`"),
                ("Control & Utils", f"`{p}menu mod` • `{p}menu vc` • `{p}menu tools`"),
            ],
            icon="brand",
            footer=f"Prefix: {p}  •  {len(self.bot.commands)} Commands  •  Type {p}menu <category>",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="selfbot", aliases=["ping"])
    async def selfbot_info(self, ctx):
        uptime_s = int(time.time() - self.bot.start_time)
        hrs, rem = divmod(uptime_s, 3600)
        mins, secs = divmod(rem, 60)
        cfg = load_config()
        theme = load_themes().get("active_theme", "obsidian")
        msg = UI.card(
            "System Telemetry",
            [
                ("Account", f"`{self.bot.user}` (`{self.bot.user.id}`)"),
                ("Latency", f"`{round(self.bot.latency * 1000)}ms` • **Uptime** `{hrs}h {mins}m {secs}s`"),
                ("Servers", f"`{len(self.bot.guilds)}` • **Commands** `{len(self.bot.commands)}`"),
                ("Theme", f"`{theme}` • **Auto-Del** `{cfg.get('autodel', 0)}s`"),
            ],
            icon="diamond",
            footer=f"Account Slot #{self.bot.account_num}",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="snipe")
    async def snipe(self, ctx, count: int = 1):
        items = self.bot.snipes.get(ctx.channel.id, [])
        if not items:
            return await self.bot.reply(ctx, UI.status("Nothing deleted recently in this channel.", False))
        rows = []
        for idx, it in enumerate(items[:max(1, min(count, 5))], 1):
            extra = f" | {', '.join(it['attachments'])}" if it["attachments"] else ""
            rows.append((f"#{idx} {it['author']} [{it['time']}]", f"{it['content']}{extra}"))
        await self.bot.reply(ctx, UI.card("Snipe Captured", rows, icon="eye"))

    @commands.command(name="esnipe")
    async def esnipe(self, ctx):
        items = self.bot.esnipes.get(ctx.channel.id, [])
        if not items:
            return await self.bot.reply(ctx, UI.status("No edited messages captured here.", False))
        it = items[0]
        msg = UI.card(
            "Edit-Snipe Captured",
            [("Author", f"`{it['author']}` (`{it['time']}`)"), ("Before", f"`{it['before']}`"), ("After", f"`{it['after']}`")],
            icon="eye",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="ghostping")
    async def ghostping(self, ctx):
        items = self.bot.ghost_pings.get(ctx.channel.id, [])
        if not items:
            return await self.bot.reply(ctx, UI.status("No ghost pings logged in this channel.", False))
        rows = [(f"{it['author']} [{it['time']}]", it["content"]) for it in items[:5]]
        await self.bot.reply(ctx, UI.card("Ghost Pings Caught", rows, icon="warn"))

    @commands.command(name="srvinfo")
    async def srvinfo(self, ctx):
        g = ctx.guild
        if not g:
            return await self.bot.reply(ctx, UI.status("Run this inside a server.", False))
        msg = UI.card(
            f"Server ▸ {g.name}",
            [
                ("ID", f"`{g.id}`"),
                ("Owner", f"`{g.owner}` (`{g.owner_id}`)"),
                ("Members", f"`{g.member_count}`"),
                ("Channels", f"`{len(g.text_channels)}` text • `{len(g.voice_channels)}` voice"),
                ("Roles", f"`{len(g.roles)}` • **Created** `{g.created_at.strftime('%Y-%m-%d')}`"),
            ],
            icon="diamond",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="user_info", aliases=["ui"])
    async def user_info(self, ctx, user: discord.User | None = None):
        target = user or ctx.author
        member = ctx.guild.get_member(target.id) if ctx.guild else None
        joined = member.joined_at.strftime("%Y-%m-%d") if (member and member.joined_at) else "N/A"
        msg = UI.card(
            f"User ▸ {target}",
            [
                ("ID", f"`{target.id}`"),
                ("Created", f"`{target.created_at.strftime('%Y-%m-%d')}`"),
                ("Joined", f"`{joined}`"),
                ("Avatar", target.display_avatar.url),
            ],
            icon="eye",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="yt")
    async def yt(self, ctx, *, query: str):
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        await self.bot.reply(ctx, UI.card("YouTube Search", [("Query", f"`{query}`"), ("Link", url)], icon="spark"))

    @commands.command(name="meaning")
    async def meaning(self, ctx, word: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}", timeout=10) as r:
                if r.status != 200:
                    return await self.bot.reply(ctx, UI.status(f"No definition found for `{word}`.", False))
                data = await r.json()
        m = data[0]["meanings"][0]
        defn = m["definitions"][0]["definition"]
        await self.bot.reply(ctx, UI.card(f"Dictionary ▸ {word}", [("Type", f"`{m['partOfSpeech']}`"), ("Meaning", defn)], icon="spark"))

    @commands.command(name="avatar")
    async def avatar(self, ctx, user: discord.User | None = None):
        t = user or ctx.author
        await self.bot.reply(ctx, f"**{t}'s Avatar:** {t.display_avatar.url}")

    @commands.command(name="banner")
    async def banner(self, ctx, user: discord.User | None = None):
        t = await self.bot.fetch_user((user or ctx.author).id)
        if not t.banner:
            return await self.bot.reply(ctx, UI.status(f"`{t}` has no banner.", False))
        await self.bot.reply(ctx, f"**{t}'s Banner:** {t.banner.url}")

    @commands.command(name="icon")
    async def icon(self, ctx):
        if not ctx.guild or not ctx.guild.icon:
            return await self.bot.reply(ctx, UI.status("This server has no icon.", False))
        await self.bot.reply(ctx, f"**{ctx.guild.name} Icon:** {ctx.guild.icon.url}")

    @commands.command(name="emojitoimg")
    async def emojitoimg(self, ctx, emoji: str):
        m = re.match(r"<(a?):(\w+):(\d+)>", emoji.strip())
        if not m:
            return await self.bot.reply(ctx, UI.status("Provide a custom Discord emoji.", False))
        ext = "gif" if m.group(1) else "png"
        await self.bot.reply(ctx, f"https://cdn.discordapp.com/emojis/{m.group(3)}.{ext}?size=512")

    @commands.command(name="csrv")
    async def clone_server(self, ctx, copy_id: int, target_id: int):
        src, dst = self.bot.get_guild(copy_id), self.bot.get_guild(target_id)
        if not src or not dst:
            return await self.bot.reply(ctx, UI.status("Account must be in both source and target servers.", False))
        msg = await ctx.send(UI.status(f"Cloning **{src.name}** → **{dst.name}**..."))
        for ch in list(dst.channels):
            try:
                await ch.delete()
                await asyncio.sleep(0.4)
            except Exception:
                pass
        for role in reversed(src.roles):
            if role.is_default() or role.managed:
                continue
            try:
                await dst.create_role(name=role.name, permissions=role.permissions, colour=role.colour, hoist=role.hoist, mentionable=role.mentionable)
                await asyncio.sleep(0.4)
            except Exception:
                pass
        cat_map = {}
        for cat in src.categories:
            try:
                cat_map[cat.id] = await dst.create_category(name=cat.name, position=cat.position)
                await asyncio.sleep(0.4)
            except Exception:
                pass
        for ch in src.text_channels:
            try:
                await dst.create_text_channel(name=ch.name, category=cat_map.get(ch.category_id), topic=ch.topic, nsfw=ch.nsfw)
                await asyncio.sleep(0.4)
            except Exception:
                pass
        for ch in src.voice_channels:
            try:
                await dst.create_voice_channel(name=ch.name, category=cat_map.get(ch.category_id), user_limit=ch.user_limit)
                await asyncio.sleep(0.4)
            except Exception:
                pass
        try:
            await dst.edit(name=src.name)
            await msg.edit(content=UI.status(f"Cloned **{src.name}** successfully."))
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(General(bot))