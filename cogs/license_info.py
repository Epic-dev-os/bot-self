from __future__ import annotations

from discord.ext import commands
from utils.theme import UI


class LicenseInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="license", aliases=["lic"])
    async def license_status(self, ctx):
        claims = getattr(self.bot, "license_claims", {})
        plan = str(claims.get("plan", "unknown")).upper()
        exp = claims.get("exp")
        exp_str = "`Lifetime (Never)`" if exp is None else f"<t:{exp}:R> (<t:{exp}:D>)"

        msg = UI.card(
            "License Status",
            [
                ("Plan", f"`{plan}`"),
                ("Bound Account", f"`{claims.get('sub', 'N/A')}`"),
                ("Expires", exp_str),
                ("Key ID", f"`{claims.get('jti', 'N/A')}`"),
            ],
            icon="diamond",
        )
        await self.bot.reply(ctx, msg)


async def setup(bot):
    await bot.add_cog(LicenseInfo(bot))