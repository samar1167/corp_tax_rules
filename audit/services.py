from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from core_rules.models import AssessmentContext, ModuleVersion

from .models import EvaluationLog


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_evaluation_log(
    *,
    assessment_context: AssessmentContext,
    module_version: ModuleVersion | None,
    taxpayer_reference: dict[str, Any],
    input_payload: dict[str, Any],
    primitive_trace: list[str],
    decision_table_trace: dict[str, Any],
    outcome_payload: dict[str, Any],
    rule_trace: list[dict[str, Any]],
) -> EvaluationLog:
    taxpayer_hash = _stable_hash(taxpayer_reference)
    input_payload_hash = _stable_hash(input_payload)

    previous_log = EvaluationLog.objects.order_by("-created_at", "-id").first()
    previous_entry_hash = previous_log.entry_hash if previous_log else ""

    chain_payload = {
        "event_id": str(uuid.uuid4()),
        "assessment_context": assessment_context.code,
        "module_version": str(module_version) if module_version else None,
        "taxpayer_hash": taxpayer_hash,
        "input_payload_hash": input_payload_hash,
        "primitive_trace": primitive_trace,
        "decision_table_trace": decision_table_trace,
        "outcome_payload": outcome_payload,
        "rule_trace": rule_trace,
        "previous_entry_hash": previous_entry_hash,
    }
    entry_hash = _stable_hash(chain_payload)

    return EvaluationLog.objects.create(
        event_id=chain_payload["event_id"],
        assessment_context=assessment_context,
        module_version=module_version,
        taxpayer_hash=taxpayer_hash,
        input_payload_hash=input_payload_hash,
        primitive_trace=primitive_trace,
        decision_table_trace=decision_table_trace,
        outcome_payload=outcome_payload,
        rule_trace=rule_trace,
        previous_entry_hash=previous_entry_hash,
        entry_hash=entry_hash,
    )
