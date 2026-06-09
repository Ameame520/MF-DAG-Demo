from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from mfdag.utils.io import append_jsonl


@dataclass
class LLMUsageTracker:
    log_path: Optional[Path] = None
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_latency_s: float = 0.0
    records: List[Dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        method: str,
        model: str,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        latency_s: float,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        call_id = str(uuid.uuid4())
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_latency_s += latency_s
        rec = {
            "call_id": call_id,
            "method": method,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_s": round(latency_s, 4),
            "prompt_chars": len(prompt),
            "response_chars": len(response),
            **(meta or {}),
        }
        self.records.append(rec)
        if self.log_path:
            append_jsonl(self.log_path, rec)
        return call_id

    def summary(self) -> Dict[str, Any]:
        return {
            "llm_calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "total_latency_s": round(self.total_latency_s, 4),
            "avg_latency_s": round(self.total_latency_s / self.calls, 4) if self.calls else 0.0,
        }


def extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"无法从 LLM 响应中解析 JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


class DeepSeekClient:
    def __init__(self, cfg: Dict[str, Any], tracker: LLMUsageTracker):
        llm_cfg = cfg["llm"]
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("未设置环境变量 DEEPSEEK_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url=llm_cfg.get("api_base", "https://api.deepseek.com"))
        self.model = llm_cfg["model"]
        self.temperature = llm_cfg.get("temperature", 0.2)
        self.max_tokens = llm_cfg.get("max_tokens", 800)
        self.tracker = tracker

    def complete_json(
        self,
        *,
        method: str,
        system_prompt: str,
        user_prompt: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        latency = time.time() - t0
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
        out_tok = int(getattr(usage, "completion_tokens", 0) or 0)
        self.tracker.record(
            method=method,
            model=self.model,
            prompt=system_prompt + "\n" + user_prompt,
            response=content,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_s=latency,
            meta=meta,
        )
        return extract_json_object(content)
