"""助教提供：本地只读业务接口替身；后续可替换为HR API，不是生产数据库。"""

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TeachingLeaveService:
    def __init__(self):
        self.records = json.loads((ROOT / "data/business_lab/leave_balances.json").read_text(encoding="utf-8"))["records"]
        self.calls = []

    def get_balance(self, user_id: str, year: int) -> dict:
        self.calls.append((user_id, year))
        item = next((row for row in self.records if row["user_id"] == user_id and row["year"] == year), None)
        metadata = {"year": year, "leave_type": "ANNUAL", "unit": "天",
                    "source": "teaching-leave-service", "observed_at": datetime.now(timezone.utc).isoformat()}
        if item is None:
            return {**metadata, "status": "not_found", "remaining_days": None}
        return {**metadata, "status": "ok", "remaining_days": item["remaining_days"]}
