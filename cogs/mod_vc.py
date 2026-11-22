import asyncio
import io
import aiohttp
import discord
from discord.ext import commands
from utils.theme import UI


class ModVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hook_stop = False

    @commands.command(name="ban")
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        await member.ban(reason=reason)
        await self.bot.reply(ctx, UI.status(f"Banned `{member}` ({reason})"))

    @commands.command(name="kick")
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        await member.kick(reason=reason)
        await self.bot.reply(ctx, UI.status(f"Kicked `{member}` ({reason})"))

    @commands.command(name="banid")
    async def banid(self, ctx, user_id: int):
        await ctx.guild.ban(discord.Object(id=user_id))
        await self.bot.reply(ctx, UI.status(f"Banned ID `{user_id}`"))

    @commands.command(name="unban")
    async def unban(self, ctx, user_id: int):
        await ctx.guild.unban(discord.Object(id=user_id))
        await self.bot.reply(ctx, UI.status(f"Unbanned ID `{user_id}`"))

    @commands.command(name="hide")
    async def hide(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await self.bot.reply(ctx, UI.status("Channel hidden from `@everyone`."))

    @commands.command(name="unhide")
    async def unhide(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await self.bot.reply(ctx, UI.status("Channel visible to `@everyone`."))

    @commands.command(name="chnl")
    async def create_chnl(self, ctx, *, name: str):
        ch = await ctx.guild.create_text_channel(name)
        await self.bot.reply(ctx, UI.status(f"Created channel {ch.mention}"))

    @commands.command(name="role")
    async def create_role(self, ctx, *, name: str):
        r = await ctx.guild.create_role(name=name)
        await self.bot.reply(ctx, UI.status(f"Created role `{r.name}` (`{r.id}`)"))

    @commands.command(name="roleperms")
    async def roleperms(self, ctx, guild_id: int, role_id: int):
        g = self.bot.get_guild(guild_id)
        r = g.get_role(role_id) if g else None
        if not r:
            return await self.bot.reply(ctx, UI.status("Role not found.", False))
        perms = [name for name, val in r.permissions if val]
        await self.bot.reply(ctx, UI.card(f"Role Perms ▸ {r.name}", [("Enabled", ", ".join(f"`{p}`" for p in perms[:25]) or "None")], icon="gear"))

    @commands.command(name="nuke")
    async def nuke(self, ctx):
        pos = ctx.channel.position
        new_ch = await ctx.channel.clone(reason="Channel nuke")
        await ctx.channel.delete()
        await new_ch.edit(position=pos)
        await new_ch.send(UI.status("Channel nuked & recreated."))

    @commands.command(name="clear")
    async def clear(self, ctx, amount: int = 10):
        deleted = 0
        async for m in ctx.channel.history(limit=amount + 1):
            if m.author.id == self.bot.user.id:
                try:
                    await m.delete()
                    deleted += 1
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
        await ctx.send(UI.status(f"Cleared `{deleted}` of your messages."), delete_after=4)

    @commands.command(name="spam")
    async def spam(self, ctx, amount: int, *, text: str):
        await ctx.message.delete()
        for _ in range(min(amount, 25)):
            await ctx.send(text)
            await asyncio.sleep(0.6)

    @commands.command(name="dm")
    async def dm_user(self, ctx, user: discord.User, *, text: str):
        await user.send(text)
        await self.bot.reply(ctx, UI.status(f"Sent DM to `{user}`."))

    @commands.command(name="transcript")
    async def transcript(self, ctx, limit: int = 50):
        lines = []
        async for m in ctx.channel.history(limit=min(limit, 500), oldest_first=True):
            ts = m.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{ts}] {m.author}: {m.content}")
        buf = io.BytesIO("\n".join(lines).encode("utf-8"))
        await self.bot.reply(ctx, UI.status(f"Exported `{len(lines)}` messages."), file=discord.File(buf, "transcript.txt"))

    @commands.command(name="spamhook")
    async def spamhook(self, ctx, url: str, name: str, count: int, *, text: str):
        self.hook_stop = False
        await self.bot.reply(ctx, UI.status(f"Sending `{min(count, 25)}` webhook messages..."))
        async with aiohttp.ClientSession() as s:
            for _ in range(min(count, 25)):
                if self.hook_stop:
                    break
                await s.post(url, json={"username": name, "content": text})
                await asyncio.sleep(0.7)

    @commands.command(name="stopspamhook")
    async def stopspamhook(self, ctx):
        self.hook_stop = True
        await self.bot.reply(ctx, UI.status("Webhook sender stopped."))

    @commands.command(name="vcjoin")
    async def vcjoin(self, ctx, channel_id: int):
        ch = self.bot.get_channel(channel_id)
        if not isinstance(ch, discord.VoiceChannel):
            return await self.bot.reply(ctx, UI.status("Invalid voice channel ID.", False))
        await ch.connect()
        await self.bot.reply(ctx, UI.status(f"Joined VC `{ch.name}`."))

    @commands.command(name="vcleave")
    async def vcleave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            return await self.bot.reply(ctx, UI.status("Left voice channel."))
        await self.bot.reply(ctx, UI.status("Not connected to a voice channel.", False))

    @commands.command(name="vckick")
    async def vckick(self, ctx, member: discord.Member):
        await member.move_to(None)
        await self.bot.reply(ctx, UI.status(f"Disconnected `{member}` from VC."))

    @commands.command(name="vcmute")
    async def vcmute(self, ctx, member: discord.Member):
        await member.edit(mute=True)
        await self.bot.reply(ctx, UI.status(f"Server-muted `{member}`."))

    @commands.command(name="vcunmute")
    async def vcunmute(self, ctx, member: discord.Member):
        await member.edit(mute=False)
        await self.bot.reply(ctx, UI.status(f"Unmuted `{member}`."))

    @commands.command(name="vcdeafen")
    async def vcdeafen(self, ctx, member: discord.Member):
        await member.edit(deafen=True)
        await self.bot.reply(ctx, UI.status(f"Server-deafened `{member}`."))

    @commands.command(name="vcundeafen")
    async def vcundeafen(self, ctx, member: discord.Member):
        await member.edit(deafen=False)
        await self.bot.reply(ctx, UI.status(f"Undeafened `{member}`."))

    @commands.command(name="vcmove")
    async def vcmove(self, ctx, member: discord.Member, channel_id: int):
        ch = self.bot.get_channel(channel_id)
        await member.move_to(ch)
        await self.bot.reply(ctx, UI.status(f"Moved `{member}` to `{ch.name}`."))

    @commands.command(name="vcmoveall")
    async def vcmoveall(self, ctx, from_id: int, to_id: int):
        src, dst = self.bot.get_channel(from_id), self.bot.get_channel(to_id)
        for m in list(src.members):
            await m.move_to(dst)
        await self.bot.reply(ctx, UI.status(f"Moved all members from `{src.name}` → `{dst.name}`."))

    @commands.command(name="vclimit")
    async def vclimit(self, ctx, limit: int, channel_id: int):
        ch = self.bot.get_channel(channel_id)
        await ch.edit(user_limit=limit)
        await self.bot.reply(ctx, UI.status(f"Set user limit of `{ch.name}` to `{limit}`."))


async def setup(bot):
    await bot.add_cog(ModVC(bot))