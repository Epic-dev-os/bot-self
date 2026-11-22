import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
DATA_DIR = ROOT / "data"


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
    """Per-instance data folder. Host -> data/, tenant -> data/u_<id>/."""

    def __init__(self, scope=1):
        if isinstance(scope, int):
            folder = "data" if scope == 1 else "alt_data"
        elif scope:
            folder = f"data/u_{scope}"
        else:
            folder = "data"
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
        (self.dir / f"{name}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


class TenantStore:
    """Registry of registered accounts. Tokens live here in plaintext."""

    def __init__(self):
        self.path = DATA_DIR / "tenants.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def all(self) -> dict:
        return self._read()

    def get(self, user_id) -> dict | None:
        return self._read().get(str(user_id))

    def set(self, user_id, record: dict) -> None:
        data = self._read()
        data[str(user_id)] = record
        self._write(data)

    def remove(self, user_id) -> None:
        data = self._read()
        data.pop(str(user_id), None)
        self._write(data)
