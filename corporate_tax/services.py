from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core_rules.models import AssessmentContext, ModuleVersion, PrimitiveVersion, RuleVersion
from core_rules.services import evaluate_decision_table_rows


@dataclass
class RuleEvaluationResult:
    rule_id: str
    matched: bool
    effects: dict[str, Any]
    consequence: dict[str, Any]


def _resolve_path(profile: dict[str, Any], path: str) -> Any:
    value: Any = profile
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _match_condition(profile: dict[str, Any], condition: dict[str, Any]) -> bool:
    actual = _resolve_path(profile, condition["field"])
    operator = condition["operator"]
    expected = condition.get("value")

    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "in":
        return actual in expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    return False


def _match_group(profile: dict[str, Any], group: dict[str, Any]) -> bool:
    operator = group.get("operator", "all")
    conditions = group.get("conditions", [])
    if operator == "all":
        return all(_match_condition(profile, item) for item in conditions)
    if operator == "any":
        return any(_match_condition(profile, item) for item in conditions)
    return False


def _get_active_corporate_module_version(
    assessment_context_code: str,
) -> tuple[AssessmentContext, ModuleVersion | None]:
    context = AssessmentContext.objects.get(code=assessment_context_code)
    module_version = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related(
            "decision_tables__decision_table",
            "primitives__primitive",
            "primitives__rules__rule",
        )
        .filter(
            module__code="INDIA_CORPORATE_TAX",
            assessment_context=context,
            status="ACTIVE",
        )
        .first()
    )
    return context, module_version


def _get_module_primitive_versions(module_version: ModuleVersion | None) -> list[PrimitiveVersion]:
    if not module_version:
        return []
    return list(
        module_version.primitives.filter(status="ACTIVE")
        .prefetch_related("rules__rule")
        .order_by("primitive__code")
    )


def _get_module_rule_versions(
    primitive_versions: list[PrimitiveVersion],
    assessment_context_code: str,
    *,
    primitive_code: str,
) -> list[RuleVersion]:
    rule_versions: dict[int, RuleVersion] = {}
    for primitive_version in primitive_versions:
        if primitive_version.primitive.code != primitive_code:
            continue
        for rule_version in primitive_version.rules.filter(
            status="ACTIVE",
            metadata__assessment_context=assessment_context_code,
        ).select_related("rule"):
            rule_versions[rule_version.id] = rule_version
    return sorted(rule_versions.values(), key=lambda item: item.rule.rule_id)


def _get_module_decision_table(module_version: ModuleVersion | None, decision_table_code: str):
    return (
        module_version.decision_tables.select_related("decision_table")
        .filter(decision_table__code=decision_table_code, status="ACTIVE")
        .first()
        if module_version
        else None
    )


def _evaluate_rule_set(profile: dict[str, Any], rules: list[RuleVersion]) -> list[RuleEvaluationResult]:
    results: list[RuleEvaluationResult] = []
    for rule in rules:
        structured_logic = rule.structured_logic or {}
        groups = structured_logic.get("when", [])
        matched = any(_match_group(profile, group) for group in groups)
        results.append(
            RuleEvaluationResult(
                rule_id=rule.rule.rule_id,
                matched=matched,
                effects=structured_logic.get("then", {}) if matched else {},
                consequence=rule.consequence if matched else {},
            )
        )
    return results


def _last_effect(results: list[RuleEvaluationResult], key: str, default: Any) -> Any:
    for result in reversed(results):
        if result.matched and key in result.effects:
            return result.effects[key]
    return default


def evaluate_corporate_tax_concept(
    profile: dict[str, Any],
    assessment_context_code: str = "TY_2026_27",
) -> dict[str, Any]:
    context, module_version = _get_active_corporate_module_version(assessment_context_code)
    primitive_versions = _get_module_primitive_versions(module_version)

    entity_results = _evaluate_rule_set(
        profile,
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.ENTITY_TYPE",
        ),
    )
    entity_type = _last_effect(entity_results, "entity_type", "FOREIGN_COMPANY")

    pe_profile = {**profile, "entity_type": entity_type}
    pe_results = _evaluate_rule_set(
        pe_profile,
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.PE_STATUS",
        ),
    )
    pe_status = _last_effect(pe_results, "pe_status", "NO_PE")

    turnover_profile = {**profile, "entity_type": entity_type}
    turnover_results = _evaluate_rule_set(
        turnover_profile,
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.TURNOVER_CATEGORY",
        ),
    )
    turnover_category = _last_effect(turnover_results, "turnover_category", "FOREIGN")

    incorporation_profile = {**profile, "entity_type": entity_type}
    incorporation_results = _evaluate_rule_set(
        incorporation_profile,
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.INCORPORATION_DATE_STATUS",
        ),
    )
    incorporation_date_status = _last_effect(
        incorporation_results,
        "incorporation_date_status",
        "NOT_ELIGIBLE_115BAB",
    )

    regime_results = _evaluate_rule_set(
        {
            **profile,
            "entity_type": entity_type,
            "turnover_category": turnover_category,
            "incorporation_date_status": incorporation_date_status,
        },
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.REGIME_TRACK",
        ),
    )
    regime_inputs = {
        "entity_type": entity_type,
        "turnover_category": turnover_category,
        "incorporation_date_status": incorporation_date_status,
        "wants_115baa": _last_effect(regime_results, "wants_115baa", False),
        "wants_115bab": _last_effect(regime_results, "wants_115bab", False),
    }
    regime_decision_table = _get_module_decision_table(module_version, "CORP.REGIME_SELECTION")
    regime_decision = (
        evaluate_decision_table_rows(rows=regime_decision_table.rows, inputs=regime_inputs)
        if regime_decision_table
        else None
    )
    regime_track = (
        regime_decision.outcome.get("regime_track", "DEFAULT_30")
        if regime_decision and regime_decision.matched
        else "DEFAULT_30"
    )

    route_results = _evaluate_rule_set(
        {
            **profile,
            "entity_type": entity_type,
            "pe_status": pe_status,
            "regime_track": regime_track,
        },
        _get_module_rule_versions(
            primitive_versions,
            assessment_context_code,
            primitive_code="CORP.FILING_ROUTE",
        ),
    )
    route_inputs = {
        "entity_type": entity_type,
        "pe_status": pe_status,
        "regime_track": regime_track,
        "audit_flag": _last_effect(route_results, "audit_flag", False),
    }
    route_decision_table = _get_module_decision_table(module_version, "CORP.FILING_ROUTE")
    route_decision = (
        evaluate_decision_table_rows(rows=route_decision_table.rows, inputs=route_inputs)
        if route_decision_table
        else None
    )
    filing_route = (
        route_decision.outcome.get("filing_route", "CORP_REVIEW_REQUIRED")
        if route_decision and route_decision.matched
        else "CORP_REVIEW_REQUIRED"
    )

    decision_trace = [
        {
            "rule_id": result.rule_id,
            "matched": result.matched,
            "effects": result.effects,
            "consequence": result.consequence,
        }
        for result in (
            entity_results
            + pe_results
            + turnover_results
            + incorporation_results
            + regime_results
            + route_results
        )
    ]

    compliance_alerts = sorted(
        {
            action
            for result in (regime_results + route_results)
            if result.matched
            for action in result.consequence.get("action", [])
        }
    )

    return {
        "assessment_context_id": context.id,
        "assessment_context": assessment_context_code,
        "module_version_id": module_version.id if module_version else None,
        "module_version": str(module_version) if module_version else None,
        "primitive_versions": [str(item) for item in primitive_versions],
        "entity_type": entity_type,
        "pe_status": pe_status,
        "turnover_category": turnover_category,
        "incorporation_date_status": incorporation_date_status,
        "regime_track": regime_track,
        "filing_route": filing_route,
        "compliance_alerts": compliance_alerts,
        "decision_tables": {
            "regime_selection": str(regime_decision_table) if regime_decision_table else None,
            "filing_route": str(route_decision_table) if route_decision_table else None,
        },
        "decision_table_matches": {
            "regime_selection": (
                {
                    "matched": regime_decision.matched,
                    "matched_row_index": regime_decision.matched_row_index,
                    "outcome": regime_decision.outcome,
                    "inputs": regime_inputs,
                }
                if regime_decision
                else None
            ),
            "filing_route": (
                {
                    "matched": route_decision.matched,
                    "matched_row_index": route_decision.matched_row_index,
                    "outcome": route_decision.outcome,
                    "inputs": route_inputs,
                }
                if route_decision
                else None
            ),
        },
        "decision_trace": decision_trace,
    }
