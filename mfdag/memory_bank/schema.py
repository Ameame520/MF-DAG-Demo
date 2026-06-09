from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def new_memory_event(
    *,
    memory_type: str,
    memory_subtype: str,
    feed_name: str,
    thread_id: str,
    root_time: str,
    step_id: int,
    cohort_id: Optional[str],
    state_summary: Dict[str, Any],
    decision_signal: Optional[Dict[str, Any]] = None,
    real_next_state: Optional[Dict[str, Any]] = None,
    simulated_next_state: Optional[Dict[str, Any]] = None,
    prediction_error: Optional[Dict[str, Any]] = None,
    text_summary: str = "",
) -> Dict[str, Any]:
    return {
        "memory_id": str(uuid.uuid4()),
        "memory_type": memory_type,
        "memory_subtype": memory_subtype,
        "feed_name": feed_name,
        "thread_id": thread_id,
        "root_time": root_time,
        "step_id": step_id,
        "cohort_id": cohort_id,
        "state_summary": state_summary,
        "decision_signal": decision_signal or {},
        "real_next_state": real_next_state or {},
        "simulated_next_state": simulated_next_state or {},
        "prediction_error": prediction_error or {},
        "text_summary": text_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
