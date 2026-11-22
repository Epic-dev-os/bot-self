from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import discord
from colorama import Fore, Style, init
from discord.ext import commands

from manager import TenantManager
from utils.storage import AccountStore, load_config
from utils.theme import UI

init(autoreset=True)

HOST_ONLY_COGS = {"panel", "host_control"}


class NovaBot(commands.Bot):
    def __init__(self, prefix: str, owner_id: int | str | None = None, *,
                 is_host: bool = False, manager: TenantManager | None = None):
        super().__init__(command_prefix=prefix, self_bot=True, help_command=None)
        self.is_host = is_host
        self.manager = manager
        self.owner_id_override = int(owner_id) if owner_id and str(owner_id).isdigit() else None
        self.store = AccountStore(1 if is_host else self.owner_id_override)
        self.start_time = time.time()
        self.snipes: dict[int, list[dict]] = {}
        self.esnipes: dict[int, list[dict]] = {}
        self.ghost_pings: dict[int, list[dict]] = {}
        self._watcher_started = False
        self._runner_task: asyncio.Task | None = None

    @property
    def label(self) -> str:
        return "HOST" if self.is_host else f"USER:{self.owner_id_override}"

    def is_owner_user(self, user_id: int) -> bool:
        if self.user and user_id == self.user.id:
            return True
        return bool(self.owner_id_override and user_id == self.owner_id_override)

    def set_prefix(self, prefix: str) -> None:
        self.command_prefix = prefix
        if not self.is_host and self.owner_id_override:
            self.manager.update_prefix(self.owner_id_override, prefix)

    def autodel_time(self) -> int | None:
        if self.is_host:
            val = int(load_config().get("autodel", 0) or 0)
        else:
            rec = self.manager.store.get(self.owner_id_override) or {}
            val = int(rec.get("autodel", 0) or 0)
        return val if val > 0 else None

    async def reply(self, ctx: commands.Context, content: str = "", **kwargs):
        if "delete_after" not in kwargs and self.autodel_time():
            kwargs["delete_after"] = self.autodel_time()
        return await ctx.send(content, **kwargs)

    async def setup_hook(self):
        cogs_dir = Path(__file__).parent / "cogs"
        for file in sorted(cogs_dir.glob("*.py")):
            if file.name.startswith("_"):
                continue
            if not self.is_host and file.stem in HOST_ONLY_COGS:
                continue
            ext = f"cogs.{file.stem}"
            try:
                await self.load_extension(ext)
                print(f"{Fore.CYAN}[{self.label}] Loaded {ext}{Style.RESET_ALL}")
            except Exception as exc:
                print(f"{Fore.RED}[{self.label}] Failed {ext}: {exc}{Style.RESET_ALL}")

        if self.is_host:
            from cogs.panel import build_panel_view
            self.add_view(build_panel_view(self))

    async def on_ready(self):
        print(
            f"{Fore.GREEN}[{self.label}] Online as {self.user} "
            f"(ID: {self.user.id}) | Guilds: {len(self.guilds)} | Prefix: {self.command_prefix}{Style.RESET_ALL}"
        )
        if self.is_host and not self._watcher_started:
            self._watcher_started = True
            await self.manager.start_all()

    async def on_message(self, message: discord.Message):
        if not self.is_owner_user(message.author.id):
            return
        if message.author.bot and message.author.id != (self.user.id if self.user else 0):
            return

        if not self.is_host:
            if not self.manager.channel_allowed(message.channel.id):
                return

        prefix = self.command_prefix
        if isinstance(prefix, str) and message.content.startswith(prefix):
            parts = message.content[len(prefix):].split(" ", 1)
            aliases = self.store.load("aliases", {})
            if parts[0].lower() in aliases:
                rest = f" {parts[1]}" if len(parts) > 1 else ""
                message.content = f"{prefix}{aliases[parts[0].lower()]}{rest}"

        await self.process_commands(message)

    async def _delete_trigger(self, message: discord.Message, delay: float):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass

    async def on_command(self, ctx: commands.Context):
        delay = load_config().get("deltrigger", None)
        if delay is not None and delay >= 0:
            asyncio.create_task(self._delete_trigger(ctx.message, delay))

    async def on_message_delete(self, message: discord.Message):
        if message.content or message.attachments:
            bucket = self.snipes.setdefault(message.channel.id, [])
            bucket.insert(0, {
                "author": str(message.author),
                "content": message.content or "[Attachment]",
                "attachments": [a.url for a in message.attachments],
                "time": message.created_at.strftime("%H:%M:%S UTC"),
            })
            del bucket[25:]

        if self.user and self.user in message.mentions and message.author.id != self.user.id:
            gp = self.ghost_pings.setdefault(message.channel.id, [])
            gp.insert(0, {
                "author": str(message.author),
                "content": message.content,
                "time": message.created_at.strftime("%H:%M:%S UTC"),
            })
            del gp[15:]

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content:
            return
        bucket = self.esnipes.setdefault(before.channel.id, [])
        bucket.insert(0, {
            "author": str(before.author),
            "before": before.content,
            "after": after.content,
            "time": time.strftime("%H:%M:%S UTC", time.gmtime()),
        })
        del bucket[25:]

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        try:
            await ctx.send(UI.status(f"Error: `{error}`", ok=False), delete_after=10)
        except Exception:
            pass


def register_core(bot: NovaBot):
    @bot.command(name="restart")
    async def restart_cmd(ctx: commands.Context):
        if not bot.is_host:
            return await ctx.send(UI.status("Restart is host-only."), delete_after=3)
        await ctx.send(UI.status("Restarting all accounts..."), delete_after=3)
        os.execv(sys.executable, [sys.executable] + sys.argv)


async def main():
    cfg = load_config()
    host_token = (cfg.get("host_token") or cfg.get("token_1") or "").strip()
    if not host_token or host_token.startswith("YOUR_"):
        print(f"{Fore.RED}[ERROR] Set host_token in config.json first.{Style.RESET_ALL}")
        return

    host = NovaBot(cfg.get("host_prefix") or ".", cfg.get("owner_id"), is_host=True)
    host.manager = TenantManager(host)
    register_core(host)

    try:
        await host.start(host_token)
    except discord.LoginFailure:
        print(f"{Fore.RED}[ERROR] Invalid host token in config.json{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
