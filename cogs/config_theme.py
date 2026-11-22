from discord.ext import commands
from utils.storage import update_config
from utils.theme import UI, load_themes


class ConfigTheme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _set(self, ctx, key: str, value: str, label: str, secret: bool = False):
        update_config(key, value.strip())
        try:
            await ctx.message.delete()
        except Exception:
            pass
        shown = "*hidden*" if secret else f"`{value.strip()}`"
        await self.bot.reply(ctx, UI.status(f"Updated **{label}** → {shown}"), delete_after=8)

    @commands.command(name="setupi")
    async def set_upi(self, ctx, *, upi_id: str):
        await self._set(ctx, "upi_1", upi_id, "UPI 1")

    @commands.command(name="setupi2")
    async def set_upi2(self, ctx, *, upi_id: str):
        await self._set(ctx, "upi_2", upi_id, "UPI 2")

    @commands.command(name="setqr")
    async def set_qr(self, ctx, *, qr_url: str):
        await self._set(ctx, "qr_1", qr_url, "QR 1")

    @commands.command(name="setqr2")
    async def set_qr2(self, ctx, *, qr_url: str):
        await self._set(ctx, "qr_2", qr_url, "QR 2")

    @commands.command(name="setsrvlink")
    async def set_srvlink(self, ctx, *, link: str):
        await self._set(ctx, "server_link", link, "Server Link")

    @commands.command(name="setuserid")
    async def set_userid(self, ctx, user_id: str):
        key = "user_id_1" if self.bot.account_num == 1 else "user_id_2"
        await self._set(ctx, key, user_id, "Authorized User ID")

    @commands.command(name="setaddy")
    async def set_addy(self, ctx, address: str):
        await self._set(ctx, "ltc_addy_1", address, "LTC Address 1")

    @commands.command(name="setaddy2")
    async def set_addy2(self, ctx, address: str):
        await self._set(ctx, "ltc_addy_2", address, "LTC Address 2")

    @commands.command(name="setbinid")
    async def set_binid(self, ctx, bin_id: str):
        await self._set(ctx, "binance_id", bin_id, "Binance ID")

    @commands.command(name="setltckey")
    async def set_ltckey(self, ctx, *, key: str):
        await self._set(ctx, "ltc_key", key, "LTC Key", secret=True)

    @commands.command(name="setprefix")
    async def set_prefix(self, ctx, prefix: str):
        self.bot.command_prefix = prefix
        await self._set(ctx, "prefix", prefix, "Prefix")

    @commands.command(name="autodel")
    async def set_autodel(self, ctx, seconds: int):
        update_config("autodel", max(0, seconds))
        state = f"`{seconds}s`" if seconds > 0 else "`OFF`"
        await ctx.send(UI.status(f"Auto-delete set to {state}"), delete_after=6)

    @commands.command(name="theme", aliases=["themes"])
    async def theme_cmd(self, ctx, action: str = "list", name: str = ""):
        data = load_themes()
        presets = data["presets"]

        if action.lower() == "list":
            active = data.get("active_theme", "obsidian")
            items = [f"**`{k}`** *(active)*" if k == active else f"`{k}`" for k in presets]
            msg = UI.card(
                "Theme Studio",
                [
                    ("Active Theme", f"`{active}`"),
                    ("Available (12)", ", ".join(items)),
                    ("Switch", "`.theme set <name>`"),
                    ("Preview", "`.theme preview <name>`"),
                    ("Custom Emoji", "`.setemoji <slot> <emoji>`"),
                ],
                icon="spark",
            )
            return await self.bot.reply(ctx, msg)

        target = name.lower() if name else action.lower()
        if action.lower() == "preview":
            if target not in presets:
                return await self.bot.reply(ctx, UI.status(f"Unknown theme `{target}`.", False))
            msg = UI.card(
                f"Preview: {target}",
                [
                    ("Sample Row", "`Live Layout Check`"),
                    ("Status", "Ready to apply with `.theme set " + target + "`"),
                ],
                icon="brand",
                theme_override=target,
            )
            return await self.bot.reply(ctx, msg)

        if action.lower() == "set" or action.lower() in presets:
            if target not in presets:
                return await self.bot.reply(ctx, UI.status(f"Unknown theme `{target}`.", False))
            data["active_theme"] = target
            save_themes(data)
            return await self.bot.reply(
                ctx,
                UI.card("Theme Applied", [("Active Theme", f"`{target}`"), ("Style", f"`{presets[target]['style']}`")], icon="spark"),
            )

    @commands.command(name="setemoji")
    async def set_emoji(self, ctx, slot: str = "list", *, emoji: str = ""):
        data = load_themes()
        valid_slots = list(data["presets"]["obsidian"]["icons"].keys())

        if slot.lower() == "list":
            custom = data.get("custom_emojis", {})
            rows = [(s, f"{custom.get(s, UI.icon(s))} `({s})`") for s in valid_slots]
            return await self.bot.reply(ctx, UI.card("Emoji Slots", rows, icon="star", footer="Use .setemoji <slot> <emoji> or .setemoji reset"))

        if slot.lower() == "reset":
            data["custom_emojis"] = {}
            save_themes(data)
            return await self.bot.reply(ctx, UI.status("Cleared all custom emoji overrides."))

        if slot.lower() not in valid_slots or not emoji:
            return await self.bot.reply(ctx, UI.status(f"Valid slots: `{', '.join(valid_slots)}`", False))

        data.setdefault("custom_emojis", {})[slot.lower()] = emoji.strip()
        save_themes(data)
        await self.bot.reply(ctx, UI.status(f"Slot `{slot.lower()}` set to {emoji.strip()}"))

    @commands.command(name="setbrand")
    async def set_brand(self, ctx, *, name: str):
        data = load_themes()
        data["brand_name"] = name.strip()
        save_themes(data)
        await self.bot.reply(ctx, UI.status(f"Brand name updated to **{name.strip()}**"))

    @commands.command(name="alias")
    async def alias_cmd(self, ctx, action: str = "list", short: str = "", *, target: str = ""):
        aliases = self.bot.store.load("aliases", {})
        if action == "list":
            if not aliases:
                return await self.bot.reply(ctx, UI.status("No aliases set. Use `.alias add u upi`", False))
            rows = [(f".{k}", f"→ `.{v}`") for k, v in aliases.items()]
            return await self.bot.reply(ctx, UI.card("Custom Aliases", rows, icon="gear"))
        if action == "add" and short and target:
            aliases[short.lower()] = target.strip()
            self.bot.store.save("aliases", aliases)
            return await self.bot.reply(ctx, UI.status(f"Alias `.{short.lower()}` → `.{target.strip()}` saved."))
        if action in ("del", "remove") and short:
            aliases.pop(short.lower(), None)
            self.bot.store.save("aliases", aliases)
            return await self.bot.reply(ctx, UI.status(f"Removed alias `.{short.lower()}`."))


async def setup(bot):
    await bot.add_cog(ConfigTheme(bot))