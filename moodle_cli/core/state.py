import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class StateManager:
    def __init__(self, state_path: str = "last_check.json"):
        self.state_path = Path(state_path)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.state_path)

    def is_module_seen(self, course_id: int, module_id: int) -> bool:
        key = f"{course_id}_{module_id}"
        return key in self.data

    def record_module(self, course_id: int, module_id: int, timestamp: str) -> None:
        key = f"{course_id}_{module_id}"
        if key not in self.data:
            self.data[key] = timestamp

    def get_file_record(self, course_id: int, module_id: int, filename: str) -> Optional[Dict[str, Any]]:
        key = f"{course_id}_{module_id}_{filename}"
        val = self.data.get(key)
        return val if isinstance(val, dict) else None

    def record_file(
        self,
        course_id: int,
        module_id: int,
        filename: str,
        path: str,
        timemodified: int,
        filesize: int,
        course_name: str,
        module_name: str,
    ) -> None:
        key = f"{course_id}_{module_id}_{filename}"
        self.data[key] = {
            "path": path,
            "timemodified": timemodified,
            "filesize": filesize,
            "course": course_name,
            "module": module_name,
        }

    def clean_missing_files(self) -> int:
        removed = 0
        keys_to_delete = []

        for key, val in self.data.items():
            if isinstance(val, dict) and "path" in val:
                target_path = Path(val["path"])
                if not target_path.is_file():
                    keys_to_delete.append(key)
                    removed += 1

        for key in keys_to_delete:
            del self.data[key]

        if removed > 0:
            self.save()
        return removed
