import os
import re
from pathlib import Path
from typing import Callable, Optional
import requests


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name)
    cleaned = cleaned.strip(". ")
    return cleaned or "unnamed"


class FileDownloader:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def download(
        self,
        url: str,
        token: str,
        dest_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None,
        chunk_size: int = 65536,
    ) -> bool:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest_path.with_name(f"{dest_path.name}.part")

        sep = "&" if "?" in url else "?"
        auth_url = f"{url}{sep}token={token}"

        try:
            with self.session.get(auth_url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(part_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            if progress_callback:
                                progress_callback(len(chunk))

            os.replace(part_path, dest_path)
            return True
        except Exception:
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            raise
