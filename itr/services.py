from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core_rules.models import AssessmentContext, ModuleVersion, PrimitiveVersion, RuleVersion
from core_rules.services import evaluate_decision_table_rows


@dataclass
class RuleEvaluationResult:
    rule_id: str
    matched: bool
    effects: dict[str, Any]
    consequence: dict[str, Any]


def _contains_any(actual: Any, expected: list[Any]) -> bool:
    if not isinstance(actual, (list, tuple, set)):
        return False
    return any(item in actual for item in expected)


def _resolve_path(profile: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    value: Any = profile
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _match_condition(profile: dict[str, Any], condition: dict[str, Any]) -> bool:
    field_value = _resolve_path(profile, condition["field"])
    operator = condition["operator"]
    expected = condition.get("value")
    if expected == "DUE_DATE_FIELD":
        expected = _resolve_path(profile, "due_date_139_1")

    if operator == "in":
        return field_value in expected
    if operator == "not_in":
        return field_value not in expected
    if operator == "equals":
        return field_value == expected
    if operator == "not_equals":
        return field_value != expected
    if operator == "gt":
        return field_value is not None and field_value > expected
    if operator == "lte":
        return field_value is not None and field_value <= expected
    if operator == "contains_any":
        return _contains_any(field_value, expected)
    return False


def _match_group(profile: dict[str, Any], group: dict[str, Any]) -> bool:
    operator = group.get("operator", "all")
    conditions = group.get("conditions", [])

    if operator == "all":
        return all(_match_condition(profile, condition) for condition in conditions)
    if operator == "any":
        return any(_match_condition(profile, condition) for condition in conditions)
    if operator == "not":
        return not _match_group(profile, {"operator": "all", "conditions": conditions})
    return False


def _get_active_itr_module_version(assessment_context_code: str) -> tuple[AssessmentContext, ModuleVersion | None]:
    context = AssessmentContext.objects.get(code=assessment_context_code)
    module_version = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related(
            "decision_tables__decision_table",
            "primitives__primitive",
            "primitives__rules__rule",
        )
        .filter(
            module__code="INDIA_INDIVIDUAL_TAX",
            assessment_context=context,
            status="ACTIVE",
        )
        .first()
    )
    return context, module_version


def _get_module_primitive_versions(module_version: ModuleVersion | None) -> list[PrimitiveVersion]:
    if not module_version:
        return []

    primitive_versions = list(
        module_version.primitives.filter(status="ACTIVE")
        .prefetch_related("rules__rule")
        .order_by("primitive__code")
    )
    return primitive_versions


def _get_module_rule_versions(
    primitive_versions: list[PrimitiveVersion],
    assessment_context_code: str,
    *,
    primitive_code: str | None = None,
) -> list[RuleVersion]:
    rule_versions: dict[int, RuleVersion] = {}
    for primitive_version in primitive_versions:
        if primitive_code and primitive_version.primitive.code != primitive_code:
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


def evaluate_itr1_form_eligibility(
    profile: dict[str, Any],
    assessment_context_code: str = "AY_2026_27",
) -> dict[str, Any]:
    results: list[RuleEvaluationResult] = []
    suggestions: set[str] = set()
    itr1_disqualified = False
    redirect_to_itr3_or_itr4 = False

    context, module_version = _get_active_itr_module_version(assessment_context_code)
    primitive_versions = _get_module_primitive_versions(module_version)
    decision_table_version = _get_module_decision_table(module_version, "ITR.FORM_SELECTION")
    rules = _get_module_rule_versions(
        primitive_versions,
        assessment_context_code,
        primitive_code="ITR.FORM_ELIGIBILITY",
    )

    for rule in rules:
        structured_logic = rule.structured_logic or {}
        groups = structured_logic.get("when", [])
        matched = any(_match_group(profile, group) for group in groups)

        effects = structured_logic.get("then", {}) if matched else {}
        consequence = rule.consequence if matched else {}

        if matched:
            actions = consequence.get("action", [])
            if effects.get("form_eligibility", {}).get("ITR1") == "DISQUALIFIED":
                itr1_disqualified = True
            suggestion = effects.get("form_eligibility", {}).get("ITR2")
            if suggestion == "ELIGIBLE":
                suggestions.add("ITR2")
            if "REDIRECT_TO_ITR3_OR_ITR4" in actions:
                redirect_to_itr3_or_itr4 = True
                suggestions.add("ITR3_OR_ITR4")

        results.append(
            RuleEvaluationResult(
                rule_id=rule.rule.rule_id,
                matched=matched,
                effects=effects,
                consequence=consequence,
            )
        )

    decision_inputs = {
        "itr1_disqualified": itr1_disqualified,
        "itr2_suggested": "ITR2" in suggestions,
        "redirect_to_itr3_or_itr4": redirect_to_itr3_or_itr4,
    }
    decision_result = (
        evaluate_decision_table_rows(
            rows=decision_table_version.rows,
            inputs=decision_inputs,
        )
        if decision_table_version
        else None
    )

    if decision_result and decision_result.matched:
        selected_form = decision_result.outcome.get("selected_form", "ITR1")
        suggested_forms = decision_result.outcome.get("suggested_forms", sorted(suggestions))
    else:
        selected_form = "ITR1"
        suggested_forms = sorted(suggestions)

    return {
        "assessment_context_id": context.id,
        "assessment_context": assessment_context_code,
        "module_version_id": module_version.id if module_version else None,
        "module_version": str(module_version) if module_version else None,
        "primitive_versions": [str(item) for item in primitive_versions],
        "decision_table_version": str(decision_table_version) if decision_table_version else None,
        "decision_table_inputs": decision_inputs,
        "decision_table_match": (
            {
                "matched": decision_result.matched,
                "matched_row_index": decision_result.matched_row_index,
                "outcome": decision_result.outcome,
            }
            if decision_result
            else None
        ),
        "selected_form": selected_form,
        "suggested_forms": suggested_forms,
        "decision_trace": [
            {
                "rule_id": result.rule_id,
                "matched": result.matched,
                "effects": result.effects,
                "consequence": result.consequence,
            }
            for result in results
        ],
    }


def evaluate_itr_regime_selection(
    profile: dict[str, Any],
    assessment_context_code: str = "AY_2026_27",
) -> dict[str, Any]:
    results: list[RuleEvaluationResult] = []
    alerts: list[str] = []
    default_applied = False
    old_regime_allowed = False
    old_regime_requested = profile.get("regime_selection") == "OLD_REGIME"
    new_regime_requested = profile.get("regime_selection") == "NEW_REGIME"

    context, module_version = _get_active_itr_module_version(assessment_context_code)
    primitive_versions = _get_module_primitive_versions(module_version)
    decision_table_version = _get_module_decision_table(module_version, "ITR.REGIME_SELECTION")
    rules = _get_module_rule_versions(
        primitive_versions,
        assessment_context_code,
        primitive_code="ITR.REGIME_SELECTION",
    )

    for rule in rules:
        structured_logic = rule.structured_logic or {}
        groups = structured_logic.get("when", [])
        matched = any(_match_group(profile, group) for group in groups)

        effects = structured_logic.get("then", {}) if matched else {}
        consequence = rule.consequence if matched else {}

        if matched:
            applicable_regime = effects.get("taxpayer", {}).get("applicable_regime")
            actions = consequence.get("action", [])
            if applicable_regime == "NEW_REGIME" and profile.get("regime_selection") in {"", "NOT_SPECIFIED"}:
                default_applied = True
            if applicable_regime == "OLD_REGIME":
                old_regime_allowed = True
            alerts.extend(actions)

        results.append(
            RuleEvaluationResult(
                rule_id=rule.rule.rule_id,
                matched=matched,
                effects=effects,
                consequence=consequence,
            )
        )

    decision_inputs = {
        "default_applied": default_applied,
        "new_regime_requested": new_regime_requested,
        "old_regime_allowed": old_regime_allowed,
        "old_regime_requested": old_regime_requested,
    }
    decision_result = (
        evaluate_decision_table_rows(
            rows=decision_table_version.rows,
            inputs=decision_inputs,
        )
        if decision_table_version
        else None
    )

    if decision_result and decision_result.matched:
        applicable_regime = decision_result.outcome.get("applicable_regime", "NEW_REGIME")
    else:
        applicable_regime = "NEW_REGIME"

    return {
        "assessment_context_id": context.id,
        "assessment_context": assessment_context_code,
        "module_version_id": module_version.id if module_version else None,
        "module_version": str(module_version) if module_version else None,
        "primitive_versions": [str(item) for item in primitive_versions if item.primitive.code == "ITR.REGIME_SELECTION"],
        "decision_table_version": str(decision_table_version) if decision_table_version else None,
        "decision_table_inputs": decision_inputs,
        "decision_table_match": (
            {
                "matched": decision_result.matched,
                "matched_row_index": decision_result.matched_row_index,
                "outcome": decision_result.outcome,
            }
            if decision_result
            else None
        ),
        "applicable_regime": applicable_regime,
        "alerts": sorted(set(alerts)),
        "decision_trace": [
            {
                "rule_id": result.rule_id,
                "matched": result.matched,
                "effects": result.effects,
                "consequence": result.consequence,
            }
            for result in results
        ],
    }


def _calculate_progressive_tax(taxable_income: int, slabs: list[dict[str, Any]]) -> Decimal:
    income = Decimal(str(taxable_income))
    total = Decimal("0")
    for slab in slabs:
        lower = Decimal(str(slab["from"]))
        upper = None if slab["to"] == "MAX" else Decimal(str(slab["to"]))
        rate = Decimal(str(slab["rate"]))

        if income <= lower:
            continue

        taxable_portion = income - lower if upper is None else min(income, upper) - lower
        if taxable_portion > 0:
            total += taxable_portion * rate

    return total.quantize(Decimal("0.01"))


def evaluate_itr_tax_computation(
    profile: dict[str, Any],
    assessment_context_code: str = "AY_2026_27",
) -> dict[str, Any]:
    results: list[RuleEvaluationResult] = []
    alerts: list[str] = []

    context, module_version = _get_active_itr_module_version(assessment_context_code)
    primitive_versions = _get_module_primitive_versions(module_version)
    rules = _get_module_rule_versions(
        primitive_versions,
        assessment_context_code,
        primitive_code="ITR.TAX_COMPUTATION",
    )

    applicable_regime = profile.get("applicable_regime")
    taxable_income = profile.get("taxable_income", 0)
    special_rate_income = profile.get("special_rate_income", 0)

    base_tax = Decimal("0.00")
    rebate_87a = Decimal("0.00")
    surcharge = Decimal("0.00")
    cess = Decimal("0.00")
    total_liability = Decimal("0.00")

    new_regime_slabs = [
        {"from": 0, "to": 400000, "rate": "0.00"},
        {"from": 400000, "to": 800000, "rate": "0.05"},
        {"from": 800000, "to": 1200000, "rate": "0.10"},
        {"from": 1200000, "to": 1600000, "rate": "0.15"},
        {"from": 1600000, "to": 2000000, "rate": "0.20"},
        {"from": 2000000, "to": 2400000, "rate": "0.25"},
        {"from": 2400000, "to": "MAX", "rate": "0.30"},
    ]

    for rule in rules:
        structured_logic = rule.structured_logic or {}
        groups = structured_logic.get("when", [])
        matched = any(_match_group(profile, group) for group in groups)

        effects = structured_logic.get("then", {}) if matched else {}
        consequence = rule.consequence if matched else {}

        if matched and rule.rule.rule_id == "ITR.COMP.003":
            base_tax = _calculate_progressive_tax(taxable_income, new_regime_slabs)
        if matched and rule.rule.rule_id == "ITR.COMP.007":
            rebate_87a = min(base_tax, Decimal("60000.00"))
        if matched and rule.rule.rule_id == "ITR.COMP.010":
            after_rebate = base_tax - rebate_87a
            cess = ((after_rebate + surcharge) * Decimal("0.04")).quantize(Decimal("0.01"))
            total_liability = (after_rebate + surcharge + cess).quantize(Decimal("0.01"))

        if matched:
            alerts.extend(consequence.get("action", []))

        results.append(
            RuleEvaluationResult(
                rule_id=rule.rule.rule_id,
                matched=matched,
                effects=effects,
                consequence=consequence,
            )
        )

    if applicable_regime != "NEW_REGIME":
        alerts.append("OLD_REGIME_COMPUTATION_NOT_IMPLEMENTED_IN_THIS_SLICE")

    return {
        "assessment_context_id": context.id,
        "assessment_context": assessment_context_code,
        "module_version_id": module_version.id if module_version else None,
        "module_version": str(module_version) if module_version else None,
        "primitive_versions": [str(item) for item in primitive_versions if item.primitive.code == "ITR.TAX_COMPUTATION"],
        "applicable_regime": applicable_regime,
        "base_tax": f"{base_tax:.2f}",
        "rebate_87a": f"{rebate_87a:.2f}",
        "surcharge": f"{surcharge:.2f}",
        "cess": f"{cess:.2f}",
        "total_liability": f"{total_liability:.2f}",
        "alerts": sorted(set(alerts)),
        "decision_trace": [
            {
                "rule_id": result.rule_id,
                "matched": result.matched,
                "effects": result.effects,
                "consequence": result.consequence,
            }
            for result in results
        ],
    }
