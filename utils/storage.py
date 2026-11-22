import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def update_config(key: str, value) -> dict:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    return cfg


class AccountStore:
    def __init__(self, account_num: int = 1):
        folder = "data" if account_num == 1 else "alt_data"
        self.dir = ROOT / folder
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self, name: str, default=None):
        path = self.dir / f"{name}.json"
        if not path.exists():
            data = {} if default is None else default
            self.save(name, data)
            return data
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {} if default is None else default

    def save(self, name: str, data) -> None:
        path = self.dir / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")