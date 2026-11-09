import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "moodle-cli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
LOCAL_CONFIG_FILE = Path(".moodle-config.json")


class Config:
    def __init__(
        self,
        url: str = "",
        username: str = "",
        password: str = "",
        token: str = "",
        download_dir: str = "moodle_downloads",
        state_file: str = "last_check.json",
    ):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.download_dir = download_dir
        self.state_file = state_file

    @classmethod
    def load(cls) -> "Config":
        if LOCAL_CONFIG_FILE.exists():
            return cls._from_file(LOCAL_CONFIG_FILE)

        if DEFAULT_CONFIG_FILE.exists():
            return cls._from_file(DEFAULT_CONFIG_FILE)

        legacy = cls._from_legacy_py()
        if legacy:
            return legacy

        return cls()

    @classmethod
    def _from_file(cls, path: Path) -> "Config":
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                url=data.get("url", ""),
                username=data.get("username", ""),
                password=data.get("password", ""),
                token=data.get("token", ""),
                download_dir=data.get("download_dir", "moodle_downloads"),
                state_file=data.get("state_file", "last_check.json"),
            )
        except Exception:
            return cls()

    @classmethod
    def _from_legacy_py(cls) -> Optional["Config"]:
        legacy_path = Path("config.py")
        if not legacy_path.exists():
            return None

        try:
            url, user, pwd, dl_dir, state_f = "", "", "", "moodle_downloads", "last_check.json"
            content = legacy_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("MOODLE_URL") and "=" in line:
                    url = line.split("=", 1)[1].strip().strip("\"'")
                elif line.startswith("MOODLE_USERNAME") and "=" in line:
                    user = line.split("=", 1)[1].strip().strip("\"'")
                elif line.startswith("MOODLE_PASSWORD") and "=" in line:
                    pwd = line.split("=", 1)[1].strip().strip("\"'")
                elif line.startswith("DOWNLOAD_DIR") and "=" in line:
                    dl_dir = line.split("=", 1)[1].strip().strip("\"'")
                elif line.startswith("STATE_FILE") and "=" in line:
                    state_f = line.split("=", 1)[1].strip().strip("\"'")

            if url and not url.startswith("https://elearning.university-site.edu"):
                return cls(
                    url=url,
                    username=user,
                    password=pwd,
                    download_dir=dl_dir,
                    state_file=state_f,
                )
            elif url:
                return cls(
                    url=url,
                    username=user,
                    password=pwd,
                    download_dir=dl_dir,
                    state_file=state_f,
                )
        except Exception:
            pass
        return None

    def save(self, global_config: bool = True) -> Path:
        target = DEFAULT_CONFIG_FILE if global_config else LOCAL_CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": self.url,
            "username": self.username,
            "password": self.password,
            "token": self.token,
            "download_dir": self.download_dir,
            "state_file": self.state_file,
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return target

    def is_configured(self) -> bool:
        if not self.url or "university-site.edu" in self.url:
            return False
        if self.token:
            return True
        if self.username and self.password:
            if self.username in ("your_username", "") or self.password in ("your_password", ""):
                return False
            return True
        return False

    def reset(self) -> bool:
        """Clear credentials and delete configuration files."""
        self.url = ""
        self.username = ""
        self.password = ""
        self.token = ""
        deleted = False
        for path in (LOCAL_CONFIG_FILE, DEFAULT_CONFIG_FILE):
            if path.exists():
                try:
                    path.unlink()
                    deleted = True
                except OSError:
                    pass
        return deleted
