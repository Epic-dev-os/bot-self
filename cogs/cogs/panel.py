from __future__ import annotations

import discord
from discord.ext import commands

from manager import TenantError
from utils.theme import UI

PANEL_TITLE = "Selfbot Access Panel"
PANEL_DESC = (
    "Connect your own Discord account and use the full command set under "
    "your own prefix.\n\n"
    "**1.** Click **Connect Account**\n"
    "**2.** Paste your user token and choose a prefix\n"
    "**3.** Start using commands in this channel\n\n"
    "Only you control your account. Nobody else's commands will trigger it, "
    "and yours won't trigger theirs."
)


async def safe_respond(interaction: discord.Interaction, text: str, ephemeral: bool = True) -> None:
    for attempt in (
        lambda: interaction.response.send_message(text, ephemeral=ephemeral),
        lambda: interaction.followup.send(text, ephemeral=ephemeral),
        lambda: interaction.channel.send(text),
    ):
        try:
            await attempt()
            return
        except Exception:
            continue


class ConnectModal(discord.ui.Modal, title="Connect your account"):
    token = discord.ui.TextInput(
        label="User Token",
        placeholder="Paste your Discord user token",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=True,
    )
    prefix = discord.ui.TextInput(
        label="Command Prefix",
        placeholder=". or ! or ? or $",
        default=".",
        max_length=3,
        required=True,
    )

    def __init__(self, bot):
        super().__init__(timeout=600)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        raw_prefix = self.prefix.value.strip()
        if not raw_prefix or " " in raw_prefix:
            return await safe_respond(interaction, "Prefix cannot be empty or contain spaces.")

        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        try:
            bot = await self.bot.manager.add(interaction.user.id, self.token.value, raw_prefix)
        except TenantError as exc:
            return await safe_respond(interaction, f"**Failed:** {exc}")
        except Exception as exc:
            return await safe_respond(interaction, f"**Failed:** `{exc}`")

        await safe_respond(
            interaction,
            UI.status(
                f"Connected as **{bot.user}** — prefix `{raw_prefix}`. "
                f"Try `{raw_prefix}menu` in this channel."
            ),
        )


class PanelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Connect Account", style=discord.ButtonStyle.success,
                       custom_id="panel:connect")
    async def connect(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(ConnectModal(self.bot))
        except Exception as exc:
            await safe_respond(interaction, f"Could not open form: `{exc}`")

    @discord.ui.button(label="My Status", style=discord.ButtonStyle.secondary,
                       custom_id="panel:status")
    async def status(self, interaction: discord.Interaction, button: discord.ui.Button):
        rec = self.bot.manager.store.get(interaction.user.id)
        if not rec:
            return await safe_respond(interaction, "You have no account connected.")
        live = "online" if interaction.user.id in self.bot.manager.runners else "offline"
        await safe_respond(
            interaction,
            UI.card("Your Connection", [
                ("Prefix", f"`{rec.get('prefix', '.')}`"),
                ("State", f"`{live}`"),
                ("Commands", f"`{rec.get('prefix', '.')}menu`"),
            ], icon="gear"),
        )

    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.danger,
                       custom_id="panel:disconnect")
    async def disconnect(self, interaction: discord.Interaction, button: discord.ui.Button):
        existed = await self.bot.manager.remove(interaction.user.id)
        text = "Account disconnected and removed." if existed else "Nothing to disconnect."
        await safe_respond(interaction, UI.status(text, ok=existed))


def build_panel_view(bot) -> PanelView:
    return PanelView(bot)


class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _embed(self) -> discord.Embed:
        embed = discord.Embed(title=PANEL_TITLE, description=PANEL_DESC, colour=0x2B2D31)
        embed.add_field(
            name="How to get your token",
            value="Browser: DevTools (F12) → Application → Local Storage → `discord.com` → `token`.\n"
                  "Mobile: use a token grabber or Discord settings → Advanced.",
            inline=False,
        )
        embed.add_field(
            name="Limits",
            value=f"Up to **{len(self.bot.manager.runners)}** accounts online right now.",
            inline=True,
        )
        embed.set_footer(text="Tokens are stored locally on the host.")
        return embed

    async def post_panel(self, channel: discord.abc.Messageable) -> discord.Message:
        return await channel.send(embed=self._embed(), view=build_panel_view(self.bot))


async def setup(bot):
    await bot.add_cog(Panel(bot))
