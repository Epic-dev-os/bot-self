import ast
import io
import operator
import time
import urllib.parse
import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import qrcode
from utils.storage import load_config
from utils.theme import UI, load_themes

OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg,
}


def safe_eval(expr: str) -> float:
    node = ast.parse(expr, mode="eval").body

    def _ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return OPS[type(n.op)](_ev(n.left), _ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](_ev(n.operand))
        raise ValueError("Invalid math expression")

    return _ev(node)


def load_font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def build_payment_card(brand: str, upi_id: str, amount: float, note: str, uri: str) -> io.BytesIO:
    w, h = 520, 680
    img = Image.new("RGB", (w, h), (15, 17, 23))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([(18, 18), (w - 18, h - 18)], radius=28, fill=(24, 27, 36), outline=(88, 101, 242), width=3)
    draw.text((w // 2, 58), brand.upper(), fill=(180, 190, 255), anchor="mm", font=load_font(26))
    draw.text((w // 2, 95), "INSTANT UPI PAYMENT", fill=(140, 148, 168), anchor="mm", font=load_font(15))

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((300, 300))

    draw.rounded_rectangle([(96, 128), (424, 456)], radius=20, fill=(255, 255, 255))
    img.paste(qr_img, (110, 142))

    draw.text((w // 2, 500), f"INR {amount:,.2f}", fill=(255, 255, 255), anchor="mm", font=load_font(34))
    draw.text((w // 2, 548), upi_id, fill=(130, 224, 170), anchor="mm", font=load_font(20))
    draw.text((w // 2, 592), f"Note: {note[:36]}", fill=(160, 168, 185), anchor="mm", font=load_font(17))
    draw.text((w // 2, 634), "Scan with GPay / PhonePe / Paytm / FamApp", fill=(105, 112, 130), anchor="mm", font=load_font(13))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class PaymentsDeals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _rates(self) -> dict:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin,tether&vs_currencies=usd,inr,eur"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                d = await r.json()
        return {"ltc_usd": d["litecoin"]["usd"], "ltc_inr": d["litecoin"]["inr"], "usd_inr": d["tether"]["inr"], "usd_eur": d["tether"]["eur"]}

    @commands.command(name="upi")
    async def upi(self, ctx):
        u = load_config().get("upi_1") or "Not set (`.setupi <id>`)"
        await self.bot.reply(ctx, UI.card("Instant UPI Payment", [("Primary UPI", f"`{u}`"), ("Note", "*Share screenshot after paying.*")], icon="bolt"))

    @commands.command(name="upi2")
    async def upi2(self, ctx):
        u = load_config().get("upi_2") or "Not set (`.setupi2 <id>`)"
        await self.bot.reply(ctx, UI.card("Backup UPI Payment", [("Secondary UPI", f"`{u}`")], icon="bolt"))

    @commands.command(name="qr")
    async def qr(self, ctx):
        await self.bot.reply(ctx, load_config().get("qr_1") or UI.status("Use `.setqr <url>` first.", False))

    @commands.command(name="qr2")
    async def qr2(self, ctx):
        await self.bot.reply(ctx, load_config().get("qr_2") or UI.status("Use `.setqr2 <url>` first.", False))

    @commands.command(name="upiqr")
    async def upiqr(self, ctx, amount: float, *, note: str = "Payment"):
        u = load_config().get("upi_1")
        if not u:
            return await self.bot.reply(ctx, UI.status("Set UPI first with `.setupi <id>`.", False))
        uri = f"upi://pay?{urllib.parse.urlencode({'pa': u, 'am': f'{amount:.2f}', 'tn': note, 'cu': 'INR'})}"
        buf = io.BytesIO()
        qrcode.make(uri).save(buf, format="PNG")
        buf.seek(0)
        await self.bot.reply(ctx, UI.card("UPI QR", [("Amount", f"`₹{amount:,.2f}`"), ("UPI", f"`{u}`"), ("Note", f"`{note}`")], icon="bolt"), file=discord.File(buf, "upi_qr.png"))

    @commands.command(name="paycard")
    async def paycard(self, ctx, amount: float, *, note: str = "Order Payment"):
        u = load_config().get("upi_1")
        if not u:
            return await self.bot.reply(ctx, UI.status("Set UPI first with `.setupi <id>`.", False))
        brand = load_themes().get("brand_name", "Nova Selfbot")
        uri = f"upi://pay?{urllib.parse.urlencode({'pa': u, 'am': f'{amount:.2f}', 'tn': note, 'cu': 'INR'})}"
        buf = build_payment_card(brand, u, amount, note, uri)
        await self.bot.reply(ctx, file=discord.File(buf, "payment_card.png"))

    @commands.command(name="vouch")
    async def vouch(self, ctx, *, product: str):
        await self.bot.reply(ctx, f"### {UI.icon('star')} Vouch Template\n```+rep {self.bot.user.mention} Legit | {product}```\n-# {UI.icon('spark')} Copy & paste in vouches")

    @commands.command(name="exch")
    async def exch(self, ctx, *, details: str):
        await self.bot.reply(ctx, f"```+rep {self.bot.user.mention} Fast Exchange | {details}```")

    @commands.command(name="i2cvouch")
    async def i2cvouch(self, ctx, inr_amt: str, ltc_amt: str):
        await self.bot.reply(ctx, f"```+rep {self.bot.user.mention} Exchanged ₹{inr_amt} INR -> {ltc_amt} LTC```")

    @commands.command(name="c2ivouch")
    async def c2ivouch(self, ctx, ltc_amt: str, inr_amt: str):
        await self.bot.reply(ctx, f"```+rep {self.bot.user.mention} Exchanged {ltc_amt} LTC -> ₹{inr_amt} INR```")

    @commands.command(name="deal")
    async def deal_cmd(self, ctx, action: str, sell: float = 0.0, buy: float = 0.0, *, item: str = "Item"):
        deals = self.bot.store.load("deals", [])
        if action.lower() == "add":
            profit = round(sell - buy, 2)
            deals.append({"item": item, "sell": sell, "buy": buy, "profit": profit, "ts": int(time.time())})
            self.bot.store.save("deals", deals)
            return await self.bot.reply(ctx, UI.card("Deal Logged", [("Item", f"`{item}`"), ("Sell / Buy", f"`₹{sell:,.2f}` / `₹{buy:,.2f}`"), ("Net Profit", f"`+₹{profit:,.2f}`")], icon="coin"))
        if action.lower() == "clear":
            self.bot.store.save("deals", [])
            return await self.bot.reply(ctx, UI.status("Cleared all logged deals."))

    @commands.command(name="profit", aliases=["deals"])
    async def profit_cmd(self, ctx):
        deals = self.bot.store.load("deals", [])
        if not deals:
            return await self.bot.reply(ctx, UI.status("No deals logged yet. Use `.deal add <sell> <buy> <item>`", False))
        total_sales = sum(d["sell"] for d in deals)
        total_profit = sum(d["profit"] for d in deals)
        last = deals[-1]
        msg = UI.card(
            "Deal Ledger",
            [
                ("Total Deals", f"`{len(deals)}`"),
                ("Gross Sales", f"`₹{total_sales:,.2f}`"),
                ("Net Profit", f"`+₹{total_profit:,.2f}`"),
                ("Last Deal", f"`{last['item']}` (`+₹{last['profit']:,.2f}`)"),
            ],
            icon="coin",
        )
        await self.bot.reply(ctx, msg)

    @commands.command(name="math")
    async def math_cmd(self, ctx, *, expr: str):
        val = safe_eval(expr.replace("x", "*").replace("÷", "/"))
        await self.bot.reply(ctx, UI.card("Calculator", [("Expression", f"`{expr}`"), ("Result", f"**`{val:g}`**")], icon="gear"))

    @commands.command(name="i2c")
    async def i2c(self, ctx, amt: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("INR → Crypto", [("INR", f"`₹{amt:,.2f}`"), ("USD", f"`${amt/r['usd_inr']:,.2f}`"), ("LTC", f"`{amt/r['ltc_inr']:.6f} LTC`")], icon="coin"))

    @commands.command(name="c2i")
    async def c2i(self, ctx, usd: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("USD → INR", [("USD", f"`${usd:,.2f}`"), ("INR", f"`₹{usd*r['usd_inr']:,.2f}`")], icon="coin"))

    @commands.command(name="l2u")
    async def l2u(self, ctx, ltc: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("LTC → USD", [("LTC", f"`{ltc}`"), ("USD", f"`${ltc*r['ltc_usd']:,.2f}`")], icon="coin"))

    @commands.command(name="u2l")
    async def u2l(self, ctx, usd: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("USD → LTC", [("USD", f"`${usd:,.2f}`"), ("LTC", f"`{usd/r['ltc_usd']:.6f} LTC`")], icon="coin"))

    @commands.command(name="e2u")
    async def e2u(self, ctx, eur: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("EUR → USD", [("EUR", f"`€{eur:,.2f}`"), ("USD", f"`${eur/r['usd_eur']:,.2f}`")], icon="coin"))

    @commands.command(name="u2e")
    async def u2e(self, ctx, usd: float):
        r = await self._rates()
        await self.bot.reply(ctx, UI.card("USD → EUR", [("USD", f"`${usd:,.2f}`"), ("EUR", f"`€{usd*r['usd_eur']:,.2f}`")], icon="coin"))


async def setup(bot):
    await bot.add_cog(PaymentsDeals(bot))