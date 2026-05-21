from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core_rules.models import AssessmentContext, ModuleVersion
from corporate_tax.services import evaluate_corporate_tax_concept
from itr.services import evaluate_itr1_form_eligibility

from .models import CrossModuleRule

ACTION_SEVERITY = {
    "RELATED_DIRECTOR_DISCLOSURE_REVIEW": "REVIEW_REQUIRED",
    "RECONCILE_INDIVIDUAL_COMPANY_DISCLOSURES": "REVIEW_REQUIRED",
    "CROSS_BORDER_DISCLOSURE_REVIEW": "CRITICAL_REVIEW",
    "DTAA_AND_FOREIGN_ASSET_ALIGNMENT_REVIEW": "CRITICAL_REVIEW",
}


@dataclass
class CrossRuleEvaluationResult:
    rule_id: str
    matched: bool
    effects: dict[str, Any]


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _match_condition(payload: dict[str, Any], condition: dict[str, Any]) -> bool:
    actual = _resolve_path(payload, condition["field"])
    operator = condition["operator"]
    expected = condition.get("value")

    if operator == "equals":
        return actual == expected
    if operator == "in":
        return actual in expected
    return False


def _match_group(payload: dict[str, Any], group: dict[str, Any]) -> bool:
    operator = group.get("operator", "all")
    conditions = group.get("conditions", [])
    if operator == "all":
        return all(_match_condition(payload, item) for item in conditions)
    if operator == "any":
        return any(_match_condition(payload, item) for item in conditions)
    return False


def _get_active_governance_module(assessment_context_code: str) -> tuple[AssessmentContext, ModuleVersion | None]:
    context = AssessmentContext.objects.get(code=assessment_context_code)
    module_version = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .filter(
            module__code="INDIA_TAX_GOVERNANCE",
            assessment_context=context,
            status="ACTIVE",
        )
        .first()
    )
    return context, module_version


def _summarize_itr_posture(itr_result: dict[str, Any], itr_profile: dict[str, Any]) -> dict[str, Any]:
    signals: list[str] = []
    if itr_result["selected_form"] != "ITR1":
        signals.append("NON_SIMPLE_ITR_PATH")
    if itr_profile.get("is_director_in_company"):
        signals.append("DIRECTOR_DISCLOSURE_PRESENT")
    if itr_profile.get("has_foreign_assets"):
        signals.append("FOREIGN_ASSET_DISCLOSURE_PRESENT")
    status = "STANDARD" if not signals else "ELEVATED"
    return {
        "status": status,
        "selected_form": itr_result["selected_form"],
        "signals": signals,
    }


def _summarize_corporate_posture(corporate_result: dict[str, Any]) -> dict[str, Any]:
    signals: list[str] = []
    if corporate_result["entity_type"] in {"FOREIGN_COMPANY", "DEEMED_DOMESTIC"}:
        signals.append("CROSS_BORDER_ENTITY_CLASSIFICATION")
    if corporate_result["pe_status"] == "PE_EXISTS":
        signals.append("PE_REVIEW_REQUIRED")
    if corporate_result["filing_route"] != "ITR6_DOMESTIC_COMPANY":
        signals.append("NON_STANDARD_CORPORATE_ROUTE")
    status = "STANDARD" if not signals else "ELEVATED"
    return {
        "status": status,
        "filing_route": corporate_result["filing_route"],
        "signals": signals,
    }


def _build_governance_summary(
    *,
    governance_actions: list[str],
    itr_result: dict[str, Any],
    itr_profile: dict[str, Any],
    corporate_result: dict[str, Any],
) -> dict[str, Any]:
    severity_buckets = {"WATCH": [], "REVIEW_REQUIRED": [], "CRITICAL_REVIEW": []}
    for action in governance_actions:
        bucket = ACTION_SEVERITY.get(action, "WATCH")
        severity_buckets[bucket].append(action)

    if severity_buckets["CRITICAL_REVIEW"]:
        overall_posture = "CRITICAL_REVIEW"
    elif severity_buckets["REVIEW_REQUIRED"]:
        overall_posture = "REVIEW_REQUIRED"
    elif governance_actions:
        overall_posture = "WATCH"
    else:
        overall_posture = "CLEAR"

    return {
        "overall_posture": overall_posture,
        "action_count": len(governance_actions),
        "severity_buckets": severity_buckets,
        "modules": {
            "itr": _summarize_itr_posture(itr_result, itr_profile),
            "corporate": _summarize_corporate_posture(corporate_result),
        },
    }


def evaluate_cross_module_governance(
    *,
    itr_profile: dict[str, Any],
    corporate_profile: dict[str, Any],
    itr_assessment_context: str = "AY_2026_27",
    corporate_assessment_context: str = "TY_2026_27",
    governance_assessment_context: str = "GOV_2026_27",
) -> dict[str, Any]:
    governance_context, governance_module = _get_active_governance_module(governance_assessment_context)
    itr_result = evaluate_itr1_form_eligibility(itr_profile, itr_assessment_context)
    corporate_result = evaluate_corporate_tax_concept(corporate_profile, corporate_assessment_context)

    combined_payload = {
        "itr": {
            "selected_form": itr_result["selected_form"],
            "is_director_in_company": itr_profile.get("is_director_in_company", False),
            "has_foreign_assets": itr_profile.get("has_foreign_assets", False),
        },
        "corporate": {
            "entity_type": corporate_result["entity_type"],
            "filing_route": corporate_result["filing_route"],
            "pe_status": corporate_result["pe_status"],
            "regime_track": corporate_result["regime_track"],
        },
    }

    rules = list(
        CrossModuleRule.objects.prefetch_related("depends_on_modules")
        .filter(status="ACTIVE")
        .order_by("rule_id")
    )
    trace: list[dict[str, Any]] = []
    actions: set[str] = set()
    for rule in rules:
        structured_logic = rule.structured_logic or {}
        groups = structured_logic.get("when", [])
        matched = any(_match_group(combined_payload, group) for group in groups)
        effects = structured_logic.get("then", {}) if matched else {}
        if matched:
            actions.update(effects.get("governance_actions", []))
        trace.append(
            {
                "rule_id": rule.rule_id,
                "matched": matched,
                "effects": effects,
            }
        )

    governance_actions = sorted(actions)
    governance_summary = _build_governance_summary(
        governance_actions=governance_actions,
        itr_result=itr_result,
        itr_profile=itr_profile,
        corporate_result=corporate_result,
    )
    governance_status = governance_summary["overall_posture"]

    return {
        "assessment_context_id": governance_context.id,
        "assessment_context": governance_context.code,
        "module_version_id": governance_module.id if governance_module else None,
        "module_version": str(governance_module) if governance_module else None,
        "depends_on_modules": [
            itr_result["module_version"],
            corporate_result["module_version"],
        ],
        "itr_result": {
            "assessment_context": itr_result["assessment_context"],
            "module_version": itr_result["module_version"],
            "selected_form": itr_result["selected_form"],
            "suggested_forms": itr_result["suggested_forms"],
        },
        "corporate_result": {
            "assessment_context": corporate_result["assessment_context"],
            "module_version": corporate_result["module_version"],
            "entity_type": corporate_result["entity_type"],
            "pe_status": corporate_result["pe_status"],
            "regime_track": corporate_result["regime_track"],
            "filing_route": corporate_result["filing_route"],
        },
        "governance_status": governance_status,
        "governance_actions": governance_actions,
        "governance_summary": governance_summary,
        "rule_trace": trace,
        "input_payload": combined_payload,
    }
