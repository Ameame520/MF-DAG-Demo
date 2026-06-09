from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from mfdag.utils.io import append_jsonl, read_jsonl


class MemoryBank:
    def __init__(self, memory_path: Path, retrieval_log_path: Path):
        self.memory_path = memory_path
        self.retrieval_log_path = retrieval_log_path
        self.events: List[Dict[str, Any]] = []
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        retrieval_log_path.parent.mkdir(parents=True, exist_ok=True)
        if memory_path.exists():
            self.events = list(read_jsonl(memory_path))

    def add(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        append_jsonl(self.memory_path, event)

    def global_events(self) -> List[Dict[str, Any]]:
        return [e for e in self.events if e.get("memory_type") == "global"]

    def cohort_events(self, cohort_id: str) -> List[Dict[str, Any]]:
        return [
            e
            for e in self.events
            if e.get("memory_type") == "cohort" and e.get("cohort_id") == cohort_id
        ]
