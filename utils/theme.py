import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME_FILE = ROOT / "themes.json"

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
)


def fmt_text(text: str, use_small_caps: bool = True) -> str:
    return text.lower().translate(SMALL_CAPS_MAP) if use_small_caps else text


def load_themes() -> dict:
    return json.loads(THEME_FILE.read_text(encoding="utf-8"))


def save_themes(data: dict) -> None:
    THEME_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class UI:
    @staticmethod
    def _active(theme_override: str | None = None) -> tuple[dict, dict]:
        data = load_themes()
        name = theme_override or data.get("active_theme", "obsidian")
        preset = data["presets"].get(name, data["presets"]["obsidian"])
        merged_icons = dict(preset["icons"])
        if not theme_override:
            merged_icons.update(data.get("custom_emojis", {}))
        return data, {**preset, "icons": merged_icons, "name": name}

    @staticmethod
    def icon(slot: str) -> str:
        _, preset = UI._active()
        return preset["icons"].get(slot, "•")

    @staticmethod
    def card(
        title: str,
        rows: list[tuple[str, str]],
        icon: str = "brand",
        footer: str | None = None,
        theme_override: str | None = None,
    ) -> str:
        data, p = UI._active(theme_override)
        sc = p.get("small_caps", True)
        style = p.get("style", "quote")
        div = p.get("divider", "—")
        ic = p["icons"].get(icon, "◈")
        arr = p["icons"].get("arrow", "▸")
        spk = p["icons"].get("spark", "✦")
        foot = footer or f"{data.get('brand_name', 'Nova Selfbot')}  •  {data.get('version', 'v1.0')}  •  {p['name']}"

        if style == "code":
            lines = [f"```ini\n[{ic} {title.upper()}]"]
            for k, v in rows:
                clean_v = v.replace("`", "").replace("*", "")
                lines.append(f"{arr} {k} {div} {clean_v}")
            lines.append(f"\n; {foot}\n```")
            return "\n".join(lines)

        if style == "bracket":
            lines = [f"### {ic} ⟦ {fmt_text(title, sc)} ⟧"]
            for k, v in rows:
                lines.append(f"> **{arr} {fmt_text(k, sc)}** {div} {v}")
            lines.append(f"\n-# {spk} {fmt_text(foot, sc)}")
            return "\n".join(lines)

        if style == "clean":
            lines = [f"**{ic} {title}**"]
            for k, v in rows:
                lines.append(f"{arr} **{k}**{div} {v}")
            lines.append(f"-# {foot}")
            return "\n".join(lines)

        lines = [f"### {ic} {fmt_text(title, sc)}"]
        for k, v in rows:
            lines.append(f"> **{arr} {fmt_text(k, sc)}** {div} {v}")
        lines.append(f"\n-# {spk} {fmt_text(foot, sc)}")
        return "\n".join(lines)

    @staticmethod
    def status(message: str, ok: bool = True) -> str:
        ic = UI.icon("check" if ok else "cross")
        return f"> **{ic}** {message}"