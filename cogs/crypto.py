import io
import aiohttp
import discord
from discord.ext import commands, tasks
import qrcode
from utils.storage import load_config
from utils.theme import UI


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ltc_watcher.start()

    def cog_unload(self):
        self.ltc_watcher.cancel()

    async def _coin_price(self, ctx, coin_id: str, symbol: str):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,inr&include_24hr_change=true"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                d = (await r.json())[coin_id]
        chg = d.get("usd_24h_change", 0.0)
        msg = UI.card(
            f"{symbol} Live Price",
            [("USD", f"`${d['usd']:,.4f}`"), ("INR", f"`₹{d['inr']:,.2f}`"), ("24h Change", f"`{chg:+.2f}%`")],
            icon="coin",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="ltc")
    async def ltc_price(self, ctx): await self._coin_price(ctx, "litecoin", "LTC")

    @commands.command(name="btc")
    async def btc_price(self, ctx): await self._coin_price(ctx, "bitcoin", "BTC")

    @commands.command(name="sol")
    async def sol_price(self, ctx): await self._coin_price(ctx, "solana", "SOL")

    @commands.command(name="usdt")
    async def usdt_price(self, ctx): await self._coin_price(ctx, "tether", "USDT")

    @commands.command(name="xrp")
    async def xrp_price(self, ctx): await self._coin_price(ctx, "ripple", "XRP")

    @commands.command(name="addy")
    async def addy(self, ctx):
        a = load_config().get("ltc_addy_1") or "Not set (`.setaddy <address>`)"
        await self.bot.reply(ctx, UI.card("Litecoin Address", [("Primary LTC", f"`{a}`")], icon="coin"))

    @commands.command(name="addy2")
    async def addy2(self, ctx):
        a = load_config().get("ltc_addy_2") or "Not set (`.setaddy2 <address>`)"
        await self.bot.reply(ctx, UI.card("Secondary LTC Address", [("Backup LTC", f"`{a}`")], icon="coin"))

    async def _check_ltc_bal(self, ctx, address: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance", timeout=10) as r:
                if r.status != 200:
                    return await self.bot.reply(ctx, UI.status("Invalid LTC address or API rate-limited.", False))
                d = await r.json()
            async with s.get("https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd,inr", timeout=10) as pr:
                rate = (await pr.json())["litecoin"]

        conf = d["balance"] / 1e8
        unconf = d["unconfirmed_balance"] / 1e8
        recv = d["total_received"] / 1e8
        msg = UI.card(
            "Litecoin Wallet Check",
            [
                ("Address", f"`{address}`"),
                ("Confirmed", f"`{conf:.6f} LTC` (`${conf*rate['usd']:,.2f}` | `₹{conf*rate['inr']:,.0f}`)"),
                ("Unconfirmed", f"`{unconf:.6f} LTC`"),
                ("Total Received", f"`{recv:.6f} LTC`"),
            ],
            icon="coin",
            footer=f"1 LTC = ${rate['usd']:,.2f}",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="bal")
    async def bal(self, ctx, address: str):
        await self._check_ltc_bal(ctx, address)

    @commands.command(name="mybal")
    async def mybal(self, ctx):
        a = load_config().get("ltc_addy_1")
        if not a:
            return await self.bot.reply(ctx, UI.status("Set address with `.setaddy <address>`.", False))
        await self._check_ltc_bal(ctx, a)

    @commands.command(name="mybal2")
    async def mybal2(self, ctx):
        a = load_config().get("ltc_addy_2")
        if not a:
            return await self.bot.reply(ctx, UI.status("Set address with `.setaddy2 <address>`.", False))
        await self._check_ltc_bal(ctx, a)

    @commands.command(name="ltcqr")
    async def ltcqr(self, ctx, address: str, usd_amt: float):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd", timeout=10) as r:
                ltc_usd = (await r.json())["litecoin"]["usd"]
        ltc_amt = usd_amt / ltc_usd
        buf = io.BytesIO()
        qrcode.make(f"litecoin:{address}?amount={ltc_amt:.6f}").save(buf, format="PNG")
        buf.seek(0)
        await self.bot.reply(ctx, UI.card("LTC Payment QR", [("Address", f"`{address}`"), ("Amount", f"`{ltc_amt:.6f} LTC` (`${usd_amt:,.2f}`)")], icon="coin"), file=discord.File(buf, "ltc_qr.png"))

    async def _blockcypher_tx(self, ctx, chain: str, symbol: str, txid: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.blockcypher.com/v1/{chain}/main/txs/{txid}", timeout=10) as r:
                if r.status != 200:
                    return await self.bot.reply(ctx, UI.status(f"{symbol} TxID not found.", False))
                d = await r.json()
        total = d.get("total", 0) / 1e8
        fees = d.get("fees", 0) / 1e8
        msg = UI.card(
            f"{symbol} Transaction",
            [
                ("TxID", f"`{txid[:18]}...`"),
                ("Confirmations", f"`{d.get('confirmations', 0)}`"),
                ("Total Output", f"`{total:.6f} {symbol}`"),
                ("Fees", f"`{fees:.6f} {symbol}`"),
                ("Received", f"`{d.get('received', 'N/A')}`"),
            ],
            icon="bolt",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="txidltc")
    async def txidltc(self, ctx, txid: str): await self._blockcypher_tx(ctx, "ltc", "LTC", txid)

    @commands.command(name="txidbtc")
    async def txidbtc(self, ctx, txid: str): await self._blockcypher_tx(ctx, "btc", "BTC", txid)

    @commands.command(name="txiddoge")
    async def txiddoge(self, ctx, txid: str): await self._blockcypher_tx(ctx, "doge", "DOGE", txid)

    @commands.command(name="txidtrx")
    async def txidtrx(self, ctx, txid: str):
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://apilist.tronscanapi.com/api/transaction-info?hash={txid}", timeout=10) as r:
                if r.status != 200:
                    return await self.bot.reply(ctx, UI.status("TRON TxID lookup failed.", False))
                d = await r.json()
        if not d or "hash" not in d:
            return await self.bot.reply(ctx, UI.status("TRON TxID not found.", False))
        msg = UI.card(
            "TRON Transaction",
            [
                ("Hash", f"`{txid[:18]}...`"),
                ("Confirmed", f"`{d.get('confirmed', False)}`"),
                ("Owner", f"`{d.get('ownerAddress', 'N/A')}`"),
                ("Result", f"`{d.get('contractRet', 'N/A')}`"),
            ],
            icon="bolt",
        )
        await self.bot.reply(ctx, msg)

    def _det_data(self):
        return self.bot.store.load("ltc_detection", {"webhook": "", "active": False, "addresses": {}})

    @commands.command(name="setltchook")
    async def setltchook(self, ctx, webhook: str):
        d = self._det_data()
        d["webhook"] = webhook.strip()
        self.bot.store.save("ltc_detection", d)
        await self.bot.reply(ctx, UI.status("LTC detection webhook saved."))

    @commands.command(name="watchaddy")
    async def watchaddy(self, ctx, address: str):
        d = self._det_data()
        d["addresses"][address] = None
        self.bot.store.save("ltc_detection", d)
        await self.bot.reply(ctx, UI.status(f"Watching LTC address `{address}`."))

    @commands.command(name="unwatchaddy")
    async def unwatchaddy(self, ctx, address: str):
        d = self._det_data()
        d["addresses"].pop(address, None)
        self.bot.store.save("ltc_detection", d)
        await self.bot.reply(ctx, UI.status(f"Stopped watching `{address}`."))

    @commands.command(name="startdetect")
    async def startdetect(self, ctx):
        d = self._det_data()
        d["active"] = True
        self.bot.store.save("ltc_detection", d)
        await self.bot.reply(ctx, UI.status("LTC Transaction Detector **ON**."))

    @commands.command(name="stopdetect")
    async def stopdetect(self, ctx):
        d = self._det_data()
        d["active"] = False
        self.bot.store.save("ltc_detection", d)
        await self.bot.reply(ctx, UI.status("LTC Transaction Detector **OFF**."))

    @commands.command(name="listwatch")
    async def listwatch(self, ctx):
        d = self._det_data()
        addrs = list(d["addresses"].keys())
        rows = [("Status", "`ON`" if d["active"] else "`OFF`"), ("Watched", ", ".join(f"`{a}`" for a in addrs) or "None")]
        await self.bot.reply(ctx, UI.card("LTC Detector", rows, icon="eye"))

    @tasks.loop(seconds=45)
    async def ltc_watcher(self):
        d = self._det_data()
        if not d.get("active") or not d.get("webhook") or not d.get("addresses"):
            return
        changed = False
        async with aiohttp.ClientSession() as s:
            for addr, last_recv in list(d["addresses"].items()):
                try:
                    async with s.get(f"https://api.blockcypher.com/v1/ltc/main/addrs/{addr}/balance", timeout=10) as r:
                        if r.status != 200:
                            continue
                        info = await r.json()
                    total_recv = info.get("total_received", 0)
                    if last_recv is None:
                        d["addresses"][addr] = total_recv
                        changed = True
                    elif total_recv > last_recv:
                        delta = (total_recv - last_recv) / 1e8
                        d["addresses"][addr] = total_recv
                        changed = True
                        payload = {"embeds": [{"title": "LTC Received", "color": 0x5865F2, "description": f"**Address:** `{addr}`\n**Received:** `+{delta:.6f} LTC`"}]}
                        await s.post(d["webhook"], json=payload, timeout=10)
                except Exception:
                    continue
        if changed:
            self.bot.store.save("ltc_detection", d)

    @ltc_watcher.before_loop
    async def before_watcher(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Crypto(bot))