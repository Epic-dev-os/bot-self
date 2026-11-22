from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from colorama import Fore, Style, init
import discord
from discord.ext import commands
from utils.storage import load_config, AccountStore
from utils.theme import UI

init(autoreset=True)

class NovaBot(commands.Bot):
    def __init__(self, account_num: int, prefix: str, owner_id: str | None, license_key: str):
        super().__init__(command_prefix=prefix, self_bot=True, help_command=None)
        self.account_num = account_num
        self.license_key = license_key
        self.license_claims = verify_key(license_key)
        self.owner_id_override = int(owner_id) if owner_id and str(owner_id).isdigit() else None
        self.store = AccountStore(account_num)
        self.start_time = time.time()
        self.snipes: dict[int, list[dict]] = {}
        self.esnipes: dict[int, list[dict]] = {}
        self.ghost_pings: dict[int, list[dict]] = {}
        self._watcher_started = False

    def is_owner_user(self, user_id: int) -> bool:
        if self.user and user_id == self.user.id:
            return True
        return bool(self.owner_id_override and user_id == self.owner_id_override)

    def autodel_time(self) -> int | None:
        val = int(load_config().get("autodel", 0) or 0)
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
            ext = f"cogs.{file.stem}"
            try:
                await self.load_extension(ext)
                print(f"{Fore.CYAN}[Account {self.account_num}] Loaded {ext}{Style.RESET_ALL}")
            except Exception as exc:
                print(f"{Fore.RED}[Account {self.account_num}] Failed {ext}: {exc}{Style.RESET_ALL}")

    async def on_ready(self):
        try:
            self.license_claims = verify_key(self.license_key, expected_user_id=self.user.id)
        except LicenseError as exc:
            print(f"{Fore.RED}[Account {self.account_num}] LICENSE ERROR: {exc}{Style.RESET_ALL}")
            await self.close()
            return

        if not self._watcher_started:
            self._watcher_started = True
            asyncio.create_task(self._license_watcher())

        print(
            f"{Fore.GREEN}[Account {self.account_num}] Online as {self.user} "
            f"(ID: {self.user.id}) | Plan: {self.license_claims['plan'].upper()} "
            f"| Guilds: {len(self.guilds)} | Prefix: {self.command_prefix}{Style.RESET_ALL}"
        )

    async def _license_watcher(self):
        while not self.is_closed():
            await asyncio.sleep(600)
            try:
                verify_key(self.license_key, expected_user_id=self.user.id)
            except LicenseError as exc:
                print(f"{Fore.RED}[Account {self.account_num}] LICENSE EXPIRED: {exc}{Style.RESET_ALL}")
                await self.close()
                return

    async def on_message(self, message: discord.Message):
        if not self.is_owner_user(message.author.id):
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
        await ctx.send(UI.status("Restarting bot system..."), delete_after=3)
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def run_account(account_num: int, token: str, prefix: str, owner_id: str | None, license_key: str):
    try:
        bot = NovaBot(account_num, prefix, owner_id, license_key)
    except LicenseError as exc:
        print(f"{Fore.RED}[Account {account_num}] LICENSE ERROR: {exc}{Style.RESET_ALL}")
        return

    register_core(bot)
    try:
        await bot.start(token.strip())
    except discord.LoginFailure:
        print(f"{Fore.RED}[Account {account_num}] Invalid Discord token in config.json{Style.RESET_ALL}")

async def main():
    cfg = load_config()
    prefix = cfg.get("prefix", ".")
    t1 = cfg.get("token_1", "").strip()
    t2 = cfg.get("token_2", "").strip()
    tasks = []

    if t1 and t1 != "YOUR_ACCOUNT_1_TOKEN":
        tasks.append(run_account(1, t1, prefix, cfg.get("user_id_1"), cfg.get("license_key_1", "")))
    else:
        print(f"{Fore.RED}[ERROR] Configure token_1 in config.json first.{Style.RESET_ALL}")
        return

    if t2:
        tasks.append(run_account(2, t2, prefix, cfg.get("user_id_2"), cfg.get("license_key_2", "")))
        print(f"{Fore.YELLOW}[INFO] Dual Account Mode Active{Style.RESET_ALL}")
    else:
        print(f"{Fore.CYAN}[INFO] Single Account Mode Active{Style.RESET_ALL}")

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
