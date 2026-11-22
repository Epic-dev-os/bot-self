from __future__ import annotations

import discord
from discord.ext import commands

from utils.storage import load_config, update_config
from utils.theme import UI


class HostControl(commands.Cog):
    """Owner-only control surface. Loaded on the host account only."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setchannel")
    async def set_channel(self, ctx, channel: discord.TextChannel | None = None):
        channel = channel or ctx.channel
        update_config("panel_channel", str(channel.id))

        old = load_config().get("panel_message_id")
        if old and channel.id == int(load_config().get("panel_channel", 0)):
            try:
                msg = await channel.fetch_message(int(old))
                await msg.delete()
            except Exception:
                pass

        panel = self.bot.get_cog("Panel")
        message = await panel.post_panel(channel)
        update_config("panel_message_id", str(message.id))
        await self.bot.reply(ctx, UI.status(f"Panel bound to {channel.mention}."))

    @commands.command(name="panel")
    async def panel(self, ctx):
        panel = self.bot.get_cog("Panel")
        message = await panel.post_panel(ctx.channel)
        update_config("panel_message_id", str(message.id))

    @commands.command(name="addchannel")
    async def add_channel(self, ctx, channel: discord.TextChannel):
        ids = load_config().get("command_channels") or []
        if str(channel.id) in ids:
            return await self.bot.reply(ctx, UI.status("Already allowed.", False))
        ids.append(str(channel.id))
        update_config("command_channels", ids)
        await self.bot.reply(ctx, UI.status(f"Commands now allowed in {channel.mention}."))

    @commands.command(name="delchannel")
    async def del_channel(self, ctx, channel: discord.TextChannel):
        ids = load_config().get("command_channels") or []
        if str(channel.id) not in ids:
            return await self.bot.reply(ctx, UI.status("Not in the allow list.", False))
        ids.remove(str(channel.id))
        update_config("command_channels", ids)
        await self.bot.reply(ctx, UI.status(f"Removed {channel.mention}."))

    @commands.command(name="anywhere")
    async def anywhere(self, ctx, state: str = "on"):
        on = state.lower() in ("on", "true", "1", "yes")
        update_config("allow_anywhere", on)
        await self.bot.reply(ctx, UI.status(f"Commands {'anywhere' if on else 'channel-locked'}."))

    @commands.command(name="tenants")
    async def tenants(self, ctx):
        records = self.bot.manager.store.all()
        if not records:
            return await self.bot.reply(ctx, UI.status("No accounts registered.", False))
        rows = []
        for uid, rec in records.items():
            state = "online" if int(uid) in self.bot.manager.runners else "offline"
            rows.append((f"{uid}", f"`{rec.get('prefix', '.')}` • {state}"))
        await self.bot.reply(ctx, UI.card(f"Registered Accounts ({len(rows)})", rows, icon="gear"))

    @commands.command(name="revoke")
    async def revoke(self, ctx, user_id: int):
        existed = await self.bot.manager.remove(user_id)
        await self.bot.reply(ctx, UI.status(
            f"Revoked `{user_id}`." if existed else f"`{user_id}` was not registered.", ok=existed
        ))


async def setup(bot):
    await bot.add_cog(HostControl(bot))
