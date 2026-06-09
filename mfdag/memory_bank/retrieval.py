from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from mfdag.mean_field.compressor import MeanFieldCompressor
from mfdag.utils.io import append_jsonl


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class MemoryRetriever:
    def __init__(self, compressor: MeanFieldCompressor, retrieval_log_path):
        self.compressor = compressor
        self.retrieval_log_path = retrieval_log_path

    def retrieve_global_recent(self, events: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        return events[-k:]

    def retrieve_global_similar(
        self,
        events: List[Dict[str, Any]],
        current_state: Dict[str, Any],
        k: int,
    ) -> List[Dict[str, Any]]:
        query = self.compressor.feature_vector(current_state)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for e in events:
            ss = e.get("state_summary") or {}
            vec = self.compressor.feature_vector(ss) if ss else []
            if vec:
                scored.append((_cosine(query, vec), e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:k]]

    def retrieve_cohort_recent(self, events: List[Dict[str, Any]], cohort_id: str, k: int) -> List[Dict[str, Any]]:
        filtered = [e for e in events if e.get("cohort_id") == cohort_id]
        return filtered[-k:]

    def retrieve_cohort_similar(
        self,
        events: List[Dict[str, Any]],
        cohort_id: str,
        current_state: Dict[str, Any],
        k: int,
    ) -> List[Dict[str, Any]]:
        filtered = [e for e in events if e.get("cohort_id") == cohort_id]
        return self.retrieve_global_similar(filtered, current_state, k)

    def retrieve_all(
        self,
        memory_bank,
        cohort_id: str,
        current_state: Dict[str, Any],
        top_k_global: int,
        top_k_cohort: int,
        thread_id: str,
        step_id: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        global_events = memory_bank.global_events()
        cohort_events = memory_bank.cohort_events(cohort_id)
        g_recent = self.retrieve_global_recent(global_events, top_k_global)
        g_similar = self.retrieve_global_similar(global_events, current_state, top_k_global)
        c_recent = self.retrieve_cohort_recent(cohort_events, cohort_id, top_k_cohort)
        c_similar = self.retrieve_cohort_similar(cohort_events, cohort_id, current_state, top_k_cohort)

        merged_global = _dedupe_by_id(g_recent + g_similar)[:top_k_global]
        merged_cohort = _dedupe_by_id(c_recent + c_similar)[:top_k_cohort]

        log = {
            "thread_id": thread_id,
            "step_id": step_id,
            "cohort_id": cohort_id,
            "global_memory_ids": [e["memory_id"] for e in merged_global],
            "cohort_memory_ids": [e["memory_id"] for e in merged_cohort],
        }
        append_jsonl(self.retrieval_log_path, log)
        return {"global": merged_global, "cohort": merged_cohort}


def _dedupe_by_id(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for e in events:
        mid = e.get("memory_id")
        if mid in seen:
            continue
        seen.add(mid)
        out.append(e)
    return out
