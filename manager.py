from __future__ import annotations

import asyncio
import time

import discord
from colorama import Fore, Style

from utils.storage import TenantStore, load_config

MAX_ACCOUNTS = 30


class TenantError(Exception):
    pass


class TenantManager:
    """Owns every spawned selfbot instance. One per registered user."""

    def __init__(self, host):
        self.host = host
        self.store = TenantStore()
        self.runners: dict[int, object] = {}
        self.lock = asyncio.Lock()

    # ---------------- channel policy ----------------
    def allowed_channels(self) -> set[int]:
        cfg = load_config()
        ids: set[int] = set()
        panel = cfg.get("panel_channel")
        if panel:
            try:
                ids.add(int(panel))
            except (TypeError, ValueError):
                pass
        for cid in cfg.get("command_channels") or []:
            try:
                ids.add(int(cid))
            except (TypeError, ValueError):
                pass
        return ids

    def channel_allowed(self, channel_id: int) -> bool:
        if load_config().get("allow_anywhere"):
            return True
        allowed = self.allowed_channels()
        return not allowed or channel_id in allowed

    # ---------------- lifecycle ----------------
    async def start_all(self) -> None:
        records = self.store.all()
        if not records:
            return
        print(f"{Fore.CYAN}[HOST] Restoring {len(records)} account(s){Style.RESET_ALL}")
        for uid, rec in records.items():
            try:
                await self.add(int(uid), rec["token"], rec.get("prefix", "."), persist=False)
            except Exception as exc:
                print(f"{Fore.RED}[HOST] Restore failed for {uid}: {exc}{Style.RESET_ALL}")

    async def add(self, user_id: int, token: str, prefix: str, *, persist: bool = True):
        async with self.lock:
            if user_id in self.runners:
                await self._stop(user_id)
            elif len(self.runners) >= MAX_ACCOUNTS:
                raise TenantError(f"Server is full ({MAX_ACCOUNTS} accounts).")

            bot = self.host.__class__(prefix=prefix, owner_id=user_id,
                                      is_host=False, manager=self)
            try:
                await bot.login(token.strip())
            except discord.LoginFailure:
                raise TenantError("Discord rejected that token.")

            if bot.user and bot.user.id != user_id:
                owner = bot.user
                await bot.close()
                raise TenantError(f"That token belongs to **{owner}** (`{owner.id}`), not you.")

            bot._runner_task = asyncio.create_task(bot.connect(), name=f"tenant-{user_id}")
            self.runners[user_id] = bot

            if persist:
                self.store.set(user_id, {
                    "token": token.strip(),
                    "prefix": prefix,
                    "added_at": int(time.time()),
                })
            return bot

    async def _stop(self, user_id: int) -> None:
        bot = self.runners.pop(user_id, None)
        if bot is None:
            return
        try:
            await bot.close()
        except Exception:
            pass

    async def remove(self, user_id: int, *, persist: bool = True) -> bool:
        existed = user_id in self.runners or self.store.get(user_id) is not None
        await self._stop(user_id)
        if persist:
            self.store.remove(user_id)
        return existed

    def update_prefix(self, user_id: int, prefix: str) -> None:
        rec = self.store.get(user_id)
        if rec is not None:
            rec["prefix"] = prefix
            self.store.set(user_id, rec)

    def update_autodel(self, user_id: int, seconds: int) -> None:
        rec = self.store.get(user_id)
        if rec is not None:
            rec["autodel"] = seconds
            self.store.set(user_id, rec)

    async def shutdown(self) -> None:
        for uid in list(self.runners):
            await self._stop(uid)
