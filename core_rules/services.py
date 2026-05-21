from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableDefinition,
    DecisionTableVersion,
    ModuleDefinition,
    ModuleStatusChoices,
    ModuleVersion,
    PrimitiveDefinition,
    PrimitiveVersion,
    RuleDefinition,
    RuleModeChoices,
    RuleVersion,
    ScopeChoices,
    SeverityChoices,
    StatusChoices,
)


@dataclass
class ValidationIssue:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class DecisionTableEvaluationResult:
    matched: bool
    matched_row_index: int | None
    outcome: dict[str, Any]
    evaluated_inputs: dict[str, Any]


@dataclass
class ModuleReadinessReport:
    module_code: str
    assessment_context: str
    is_ready: bool
    module_version: str | None
    summary: dict[str, Any]
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class ChangeSetActivationReport:
    change_set_code: str
    assessment_context: str
    is_ready: bool
    summary: dict[str, Any]
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class SupersedeResult:
    created: bool
    source_rule_version: str
    new_rule_version: str
    status: str


@dataclass
class PrimitiveSupersedeResult:
    created: bool
    source_primitive_version: str
    new_primitive_version: str
    status: str
    rule_versions: list[str] = field(default_factory=list)


@dataclass
class DraftChangeSetBundleResult:
    created: bool
    code: str
    name: str
    status: str
    assessment_context: str
    summary: dict[str, Any]


@dataclass
class LifecycleTransitionResult:
    transitioned: bool
    object_type: str
    object_label: str
    from_status: str
    to_status: str
    readiness: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeSetActivationResult:
    activated: bool
    change_set_code: str
    from_status: str
    to_status: str
    activated_at: str
    summary: dict[str, Any]


@dataclass
class DraftArtifactResult:
    created: bool
    object_type: str
    object_label: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleSupersedeResult:
    created: bool
    source_module_version: str
    new_module_version: str
    status: str
    primitive_versions: list[str] = field(default_factory=list)
    decision_table_versions: list[str] = field(default_factory=list)


@dataclass
class DecisionTableSupersedeResult:
    created: bool
    source_decision_table_version: str
    new_decision_table_version: str
    status: str
    input_primitives: list[str] = field(default_factory=list)


def validate_rule_version_payload(payload: dict[str, Any]) -> ValidationResult:
    required_fields = [
        "source_reference",
        "natural_language",
        "structured_logic",
        "mode",
        "severity",
    ]
    issues: list[ValidationIssue] = []
    for field_name in required_fields:
        if payload.get(field_name) in (None, "", {}):
            issues.append(
                ValidationIssue(
                    code="missing_field",
                    message=f"Missing required rule field: {field_name}",
                    details={"field": field_name},
                )
            )
    return ValidationResult(is_valid=not issues, issues=issues)


def validate_primitive_completeness(
    *,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    rule_count: int,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if not input_schema:
        issues.append(
            ValidationIssue(
                code="missing_input_schema",
                message="Primitive version must declare an input schema.",
            )
        )
    if not output_schema:
        issues.append(
            ValidationIssue(
                code="missing_output_schema",
                message="Primitive version must declare an output schema.",
            )
        )
    if rule_count == 0:
        issues.append(
            ValidationIssue(
                code="missing_rules",
                message="Primitive version must contain at least one rule version.",
            )
        )
    return ValidationResult(is_valid=not issues, issues=issues)


def detect_primitive_conflicts(rule_logic_items: list[dict[str, Any]]) -> ValidationResult:
    issues: list[ValidationIssue] = []
    seen_signatures: dict[str, dict[str, Any]] = {}

    for item in rule_logic_items:
        signature = str(item.get("when"))
        outcome = item.get("then")
        if signature in seen_signatures and seen_signatures[signature] != outcome:
            issues.append(
                ValidationIssue(
                    code="conflicting_rule_outcome",
                    message="Conflicting outcomes detected for the same primitive condition.",
                    details={
                        "when": item.get("when"),
                        "first_then": seen_signatures[signature],
                        "second_then": outcome,
                    },
                )
            )
            continue
        seen_signatures[signature] = outcome

    return ValidationResult(is_valid=not issues, issues=issues)


def validate_decision_table_completeness(
    *,
    input_columns: list[Any],
    output_columns: list[Any],
    row_count: int,
    input_primitive_count: int,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if input_primitive_count == 0:
        issues.append(
            ValidationIssue(
                code="missing_input_primitives",
                message="Decision table version must declare at least one input primitive.",
            )
        )
    if not input_columns:
        issues.append(
            ValidationIssue(
                code="missing_input_columns",
                message="Decision table version must declare input columns.",
            )
        )
    if not output_columns:
        issues.append(
            ValidationIssue(
                code="missing_output_columns",
                message="Decision table version must declare output columns.",
            )
        )
    if row_count == 0:
        issues.append(
            ValidationIssue(
                code="missing_rows",
                message="Decision table version must contain at least one row.",
            )
        )
    return ValidationResult(is_valid=not issues, issues=issues)


def evaluate_decision_table_rows(
    *,
    rows: list[dict[str, Any]],
    inputs: dict[str, Any],
) -> DecisionTableEvaluationResult:
    for index, row in enumerate(rows):
        when = row.get("when", {})
        if all(inputs.get(key) == value for key, value in when.items()):
            return DecisionTableEvaluationResult(
                matched=True,
                matched_row_index=index,
                outcome=row.get("then", {}),
                evaluated_inputs=inputs,
            )

    return DecisionTableEvaluationResult(
        matched=False,
        matched_row_index=None,
        outcome={},
        evaluated_inputs=inputs,
    )


def build_module_readiness_report(
    *,
    module_code: str,
    assessment_context: str,
) -> ModuleReadinessReport:
    module_version = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related("primitives__primitive", "primitives__rules", "decision_tables__decision_table")
        .filter(
            module__code=module_code,
            assessment_context__code=assessment_context,
            status="ACTIVE",
        )
        .first()
    )

    issues: list[ValidationIssue] = []
    if not module_version:
        issues.append(
            ValidationIssue(
                code="missing_active_module_version",
                message="No active module version found for the requested assessment context.",
                details={"module_code": module_code, "assessment_context": assessment_context},
            )
        )
        return ModuleReadinessReport(
            module_code=module_code,
            assessment_context=assessment_context,
            is_ready=False,
            module_version=None,
            summary={
                "primitive_count": 0,
                "decision_table_count": 0,
                "rule_count": 0,
                "contract_provides_count": 0,
                "contract_consumes_count": 0,
            },
            issues=issues,
        )

    return evaluate_module_version_readiness(module_version=module_version)


def evaluate_module_version_readiness(*, module_version: ModuleVersion) -> ModuleReadinessReport:
    module_version = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related(
            "primitives__primitive",
            "primitives__rules__rule",
            "decision_tables__decision_table",
            "decision_tables__input_primitives__primitive",
        )
        .get(pk=module_version.pk)
    )

    issues: list[ValidationIssue] = []
    primitive_versions = list(module_version.primitives.all())
    decision_tables = list(module_version.decision_tables.all())

    if not primitive_versions:
        issues.append(
            ValidationIssue(
                code="missing_primitives",
                message="Module version has no attached primitive versions.",
            )
        )

    if not decision_tables:
        issues.append(
            ValidationIssue(
                code="missing_decision_tables",
                message="Module version has no attached decision table versions.",
            )
        )

    if not module_version.contract_provides:
        issues.append(
            ValidationIssue(
                code="missing_contract_provides",
                message="Module version has no declared PROVIDES outputs.",
            )
        )

    module_primitive_ids = {item.id for item in primitive_versions}
    for primitive_version in primitive_versions:
        primitive_rule_count = primitive_version.rules.count()
        if primitive_rule_count == 0:
            issues.append(
                ValidationIssue(
                    code="primitive_without_rules",
                    message="Primitive version has no attached rule versions.",
                    details={"primitive_version": str(primitive_version)},
                )
            )
        if not primitive_version.input_schema:
            issues.append(
                ValidationIssue(
                    code="primitive_missing_input_schema",
                    message="Primitive version is missing an input schema.",
                    details={"primitive_version": str(primitive_version)},
                )
            )
        if not primitive_version.output_schema:
            issues.append(
                ValidationIssue(
                    code="primitive_missing_output_schema",
                    message="Primitive version is missing an output schema.",
                    details={"primitive_version": str(primitive_version)},
                )
            )
        if primitive_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
            issues.append(
                ValidationIssue(
                    code="primitive_not_ready_for_module",
                    message="Module version references a primitive version that is not approved or active.",
                    details={
                        "primitive_version": str(primitive_version),
                        "status": primitive_version.status,
                    },
                )
            )

    for decision_table_version in decision_tables:
        if decision_table_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
            issues.append(
                ValidationIssue(
                    code="decision_table_not_ready_for_module",
                    message="Module version references a decision table version that is not approved or active.",
                    details={
                        "decision_table_version": str(decision_table_version),
                        "status": decision_table_version.status,
                    },
                )
            )
        for input_primitive in decision_table_version.input_primitives.all():
            if input_primitive.id not in module_primitive_ids:
                issues.append(
                    ValidationIssue(
                        code="decision_table_input_missing_from_module",
                        message="Decision table input primitive is not attached to the module version.",
                        details={
                            "decision_table_version": str(decision_table_version),
                            "primitive_version": str(input_primitive),
                        },
                    )
                )
            if input_primitive.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
                issues.append(
                    ValidationIssue(
                        code="decision_table_input_not_ready",
                        message="Decision table input primitive is not approved or active.",
                        details={
                            "decision_table_version": str(decision_table_version),
                            "primitive_version": str(input_primitive),
                            "status": input_primitive.status,
                        },
                    )
                )

    total_rule_count = sum(primitive.rules.count() for primitive in primitive_versions)

    return ModuleReadinessReport(
        module_code=module_version.module.code,
        assessment_context=module_version.assessment_context.code,
        is_ready=not issues,
        module_version=str(module_version),
        summary={
            "primitive_count": len(primitive_versions),
            "decision_table_count": len(decision_tables),
            "rule_count": total_rule_count,
            "contract_provides_count": len(module_version.contract_provides or []),
            "contract_consumes_count": len(module_version.contract_consumes or []),
            "primitive_versions": [str(item) for item in primitive_versions],
            "decision_table_versions": [str(item) for item in decision_tables],
        },
        issues=issues,
    )


def build_change_set_activation_report(*, change_set) -> ChangeSetActivationReport:
    issues: list[ValidationIssue] = []

    rule_versions = list(change_set.rule_versions.select_related("rule"))
    primitive_versions = list(change_set.primitive_versions.select_related("primitive"))
    decision_table_versions = list(change_set.decision_table_versions.select_related("decision_table"))
    module_versions = list(change_set.module_versions.select_related("module", "assessment_context"))

    if not any([rule_versions, primitive_versions, decision_table_versions, module_versions]):
        issues.append(
            ValidationIssue(
                code="empty_change_set",
                message="Change set has no attached versions to activate.",
            )
        )

    for rule_version in rule_versions:
        if rule_version.status not in {"APPROVED", "ACTIVE"}:
            issues.append(
                ValidationIssue(
                    code="rule_not_ready",
                    message="Rule version is not approved or active.",
                    details={"rule_version": str(rule_version), "status": rule_version.status},
                )
            )
        if rule_version.metadata.get("assessment_context") not in {"", None, change_set.assessment_context.code}:
            issues.append(
                ValidationIssue(
                    code="rule_context_mismatch",
                    message="Rule version assessment context does not match change set.",
                    details={
                        "rule_version": str(rule_version),
                        "rule_context": rule_version.metadata.get("assessment_context"),
                        "change_set_context": change_set.assessment_context.code,
                    },
                )
            )

    for primitive_version in primitive_versions:
        if primitive_version.status not in {"APPROVED", "ACTIVE"}:
            issues.append(
                ValidationIssue(
                    code="primitive_not_ready",
                    message="Primitive version is not approved or active.",
                    details={"primitive_version": str(primitive_version), "status": primitive_version.status},
                )
            )
        if not any(
            primitive_version.id in {item.id for item in module_version.primitives.all()}
            for module_version in module_versions
        ):
            issues.append(
                ValidationIssue(
                    code="primitive_not_rolled_into_module",
                    message="Primitive version is not attached to any module version in the change set.",
                    details={"primitive_version": str(primitive_version)},
                )
            )

    for decision_table_version in decision_table_versions:
        if decision_table_version.status not in {"APPROVED", "ACTIVE"}:
            issues.append(
                ValidationIssue(
                    code="decision_table_not_ready",
                    message="Decision table version is not approved or active.",
                    details={
                        "decision_table_version": str(decision_table_version),
                        "status": decision_table_version.status,
                    },
                )
            )
        if not any(
            decision_table_version.id in {item.id for item in module_version.decision_tables.all()}
            for module_version in module_versions
        ):
            issues.append(
                ValidationIssue(
                    code="decision_table_not_rolled_into_module",
                    message="Decision table version is not attached to any module version in the change set.",
                    details={"decision_table_version": str(decision_table_version)},
                )
            )

    for module_version in module_versions:
        if module_version.status not in {ModuleStatusChoices.APPROVED, ModuleStatusChoices.ACTIVE}:
            issues.append(
                ValidationIssue(
                    code="module_not_ready",
                    message="Module version is not approved or active.",
                    details={"module_version": str(module_version), "status": module_version.status},
                )
            )
        if module_version.assessment_context_id != change_set.assessment_context_id:
            issues.append(
                ValidationIssue(
                    code="module_context_mismatch",
                    message="Module version assessment context does not match change set.",
                    details={
                        "module_version": str(module_version),
                        "module_context": module_version.assessment_context.code,
                        "change_set_context": change_set.assessment_context.code,
                    },
                )
            )
        if not module_version.contract_provides:
            issues.append(
                ValidationIssue(
                    code="module_missing_contract_provides",
                    message="Module version has no contract_provides declaration.",
                    details={"module_version": str(module_version)},
                )
            )
        module_primitive_ids = {item.id for item in module_version.primitives.all()}
        module_decision_table_ids = {item.id for item in module_version.decision_tables.all()}
        for primitive_version in module_version.primitives.all():
            if primitive_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
                issues.append(
                    ValidationIssue(
                        code="module_has_unapproved_primitive",
                        message="Module version references a primitive version that is not approved or active.",
                        details={
                            "module_version": str(module_version),
                            "primitive_version": str(primitive_version),
                            "status": primitive_version.status,
                        },
                    )
                )
        for decision_table_version in module_version.decision_tables.all():
            if decision_table_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
                issues.append(
                    ValidationIssue(
                        code="module_has_unapproved_decision_table",
                        message="Module version references a decision table version that is not approved or active.",
                        details={
                            "module_version": str(module_version),
                            "decision_table_version": str(decision_table_version),
                            "status": decision_table_version.status,
                        },
                    )
                )
        for primitive_version in primitive_versions:
            if primitive_version.id not in module_primitive_ids:
                continue
            for rule_version in primitive_version.rules.all():
                if rule_version.id in {item.id for item in rule_versions}:
                    continue
                if rule_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
                    issues.append(
                        ValidationIssue(
                            code="primitive_contains_unapproved_rule",
                            message="Primitive version contains a rule version that is not approved or active.",
                            details={
                                "primitive_version": str(primitive_version),
                                "rule_version": str(rule_version),
                                "status": rule_version.status,
                            },
                        )
                    )
        for decision_table_version in decision_table_versions:
            if decision_table_version.id not in module_decision_table_ids:
                continue
            for input_primitive in decision_table_version.input_primitives.all():
                if input_primitive.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}:
                    issues.append(
                        ValidationIssue(
                            code="decision_table_input_not_ready",
                            message="Decision table input primitive is not approved or active.",
                            details={
                                "decision_table_version": str(decision_table_version),
                                "primitive_version": str(input_primitive),
                                "status": input_primitive.status,
                            },
                        )
                    )
                if input_primitive.id not in module_primitive_ids:
                    issues.append(
                        ValidationIssue(
                            code="decision_table_input_missing_from_module",
                            message="Decision table input primitive is not attached to the same module version.",
                            details={
                                "decision_table_version": str(decision_table_version),
                                "primitive_version": str(input_primitive),
                                "module_version": str(module_version),
                            },
                        )
                    )

    primitive_rule_ids = {item.id for primitive_version in primitive_versions for item in primitive_version.rules.all()}
    for rule_version in rule_versions:
        if rule_version.id not in primitive_rule_ids:
            issues.append(
                ValidationIssue(
                    code="rule_not_rolled_into_primitive",
                    message="Rule version is not attached to any primitive version in the change set.",
                    details={"rule_version": str(rule_version)},
                )
            )

    return ChangeSetActivationReport(
        change_set_code=change_set.code,
        assessment_context=change_set.assessment_context.code,
        is_ready=not issues,
        summary={
            "rule_version_count": len(rule_versions),
            "primitive_version_count": len(primitive_versions),
            "decision_table_version_count": len(decision_table_versions),
            "module_version_count": len(module_versions),
            "rule_versions": [str(item) for item in rule_versions],
            "primitive_versions": [str(item) for item in primitive_versions],
            "decision_table_versions": [str(item) for item in decision_table_versions],
            "module_versions": [str(item) for item in module_versions],
        },
        issues=issues,
    )


def _increment_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) == 1:
        try:
            return str(int(parts[0]) + 1)
        except ValueError:
            return f"{version}.1"

    head = parts[:-1]
    tail = parts[-1]
    try:
        incremented_tail = str(int(tail) + 1)
        return ".".join(head + [incremented_tail])
    except ValueError:
        return f"{version}.1"


@transaction.atomic
def create_rule_draft(
    *,
    rule_id: str,
    name: str,
    scope: str,
    description: str,
    version: str,
    source_reference: str,
    natural_language: str,
    structured_logic: dict[str, Any],
    mode: str,
    trigger: dict[str, Any],
    consequence: dict[str, Any],
    severity: str,
    assessment_context_code: str,
) -> DraftArtifactResult:
    if scope not in ScopeChoices.values:
        raise ValidationError("Invalid scope for rule definition.")
    if mode not in RuleModeChoices.values:
        raise ValidationError("Invalid rule mode.")
    if severity not in SeverityChoices.values:
        raise ValidationError("Invalid severity.")

    rule_definition, _ = RuleDefinition.objects.get_or_create(
        rule_id=rule_id,
        defaults={"name": name, "scope": scope, "description": description},
    )
    if RuleVersion.objects.filter(rule=rule_definition, version=version).exists():
        raise ValidationError(f"{rule_id}@{version} already exists.")

    rule_version = RuleVersion.objects.create(
        rule=rule_definition,
        version=version,
        status=StatusChoices.DRAFT,
        source_reference=source_reference,
        natural_language=natural_language,
        structured_logic=structured_logic,
        mode=mode,
        trigger=trigger,
        consequence=consequence,
        severity=severity,
        metadata={"assessment_context": assessment_context_code},
    )
    return DraftArtifactResult(
        created=True,
        object_type="rule_version",
        object_label=str(rule_version),
        status=rule_version.status,
        details={"rule_definition": rule_definition.rule_id},
    )


@transaction.atomic
def clone_rule_version_to_new_definition(
    *,
    source_rule_version_id: int,
    new_rule_id: str,
    name: str,
    scope: str,
    description: str,
    version: str,
    assessment_context_code: str,
) -> DraftArtifactResult:
    source = RuleVersion.objects.select_related("rule").get(pk=source_rule_version_id)
    if RuleDefinition.objects.filter(rule_id=new_rule_id).exists():
        raise ValidationError(f"Rule definition {new_rule_id} already exists.")

    rule_definition = RuleDefinition.objects.create(
        rule_id=new_rule_id,
        name=name,
        scope=scope,
        description=description,
    )
    rule_version = RuleVersion.objects.create(
        rule=rule_definition,
        version=version,
        status=StatusChoices.DRAFT,
        source_reference=source.source_reference,
        natural_language=source.natural_language,
        structured_logic=source.structured_logic,
        mode=source.mode,
        trigger=source.trigger,
        consequence=source.consequence,
        severity=source.severity,
        metadata={
            **(source.metadata or {}),
            "assessment_context": assessment_context_code,
            "cloned_from": str(source),
        },
    )
    return DraftArtifactResult(
        created=True,
        object_type="rule_version",
        object_label=str(rule_version),
        status=rule_version.status,
        details={"cloned_from": str(source)},
    )


@transaction.atomic
def update_rule_draft(
    *,
    rule_version_id: int,
    version: str,
    source_reference: str,
    natural_language: str,
    structured_logic: dict[str, Any],
    mode: str,
    trigger: dict[str, Any],
    consequence: dict[str, Any],
    severity: str,
    assessment_context_code: str,
) -> DraftArtifactResult:
    rule_version = RuleVersion.objects.select_related("rule").get(pk=rule_version_id)
    if rule_version.status != StatusChoices.DRAFT:
        raise ValidationError("Only draft rule versions can be edited.")
    validation = validate_rule_version_payload(
        {
            "source_reference": source_reference,
            "natural_language": natural_language,
            "structured_logic": structured_logic,
            "mode": mode,
            "severity": severity,
        }
    )
    if not validation.is_valid:
        raise ValidationError(validation.issues[0].message)
    if RuleVersion.objects.filter(rule=rule_version.rule, version=version).exclude(pk=rule_version.pk).exists():
        raise ValidationError(f"{rule_version.rule.rule_id}@{version} already exists.")

    rule_version.version = version
    rule_version.source_reference = source_reference
    rule_version.natural_language = natural_language
    rule_version.structured_logic = structured_logic
    rule_version.mode = mode
    rule_version.trigger = trigger
    rule_version.consequence = consequence
    rule_version.severity = severity
    rule_version.metadata = {
        **(rule_version.metadata or {}),
        "assessment_context": assessment_context_code,
    }
    rule_version.save()
    return DraftArtifactResult(
        created=False,
        object_type="rule_version",
        object_label=str(rule_version),
        status=rule_version.status,
    )


@transaction.atomic
def create_primitive_draft(
    *,
    code: str,
    name: str,
    module_scope: str,
    question: str,
    description: str,
    version: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    rule_version_ids: list[int],
) -> DraftArtifactResult:
    primitive_definition, _ = PrimitiveDefinition.objects.get_or_create(
        code=code,
        defaults={
            "name": name,
            "module_scope": module_scope,
            "question": question,
            "description": description,
        },
    )
    if PrimitiveVersion.objects.filter(primitive=primitive_definition, version=version).exists():
        raise ValidationError(f"{code}@{version} already exists.")
    primitive_version = PrimitiveVersion.objects.create(
        primitive=primitive_definition,
        version=version,
        status=StatusChoices.DRAFT,
        input_schema=input_schema,
        output_schema=output_schema,
        completeness_report={},
    )
    primitive_version.rules.set(RuleVersion.objects.filter(id__in=rule_version_ids))
    return DraftArtifactResult(
        created=True,
        object_type="primitive_version",
        object_label=str(primitive_version),
        status=primitive_version.status,
        details={"rule_count": primitive_version.rules.count()},
    )


@transaction.atomic
def clone_primitive_version_to_new_definition(
    *,
    source_primitive_version_id: int,
    new_code: str,
    name: str,
    module_scope: str,
    question: str,
    description: str,
    version: str,
) -> DraftArtifactResult:
    source = (
        PrimitiveVersion.objects.select_related("primitive")
        .prefetch_related("rules__rule")
        .get(pk=source_primitive_version_id)
    )
    if PrimitiveDefinition.objects.filter(code=new_code).exists():
        raise ValidationError(f"Primitive definition {new_code} already exists.")
    primitive_definition = PrimitiveDefinition.objects.create(
        code=new_code,
        name=name,
        module_scope=module_scope,
        question=question,
        description=description,
    )
    primitive_version = PrimitiveVersion.objects.create(
        primitive=primitive_definition,
        version=version,
        status=StatusChoices.DRAFT,
        input_schema=source.input_schema,
        output_schema=source.output_schema,
        completeness_report={
            **(source.completeness_report or {}),
            "cloned_from": str(source),
        },
    )
    primitive_version.rules.set(source.rules.all())
    return DraftArtifactResult(
        created=True,
        object_type="primitive_version",
        object_label=str(primitive_version),
        status=primitive_version.status,
        details={"cloned_from": str(source)},
    )


@transaction.atomic
def update_primitive_draft(
    *,
    primitive_version_id: int,
    version: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    rule_version_ids: list[int],
) -> DraftArtifactResult:
    primitive_version = PrimitiveVersion.objects.select_related("primitive").get(pk=primitive_version_id)
    if primitive_version.status != StatusChoices.DRAFT:
        raise ValidationError("Only draft primitive versions can be edited.")
    if PrimitiveVersion.objects.filter(primitive=primitive_version.primitive, version=version).exclude(pk=primitive_version.pk).exists():
        raise ValidationError(f"{primitive_version.primitive.code}@{version} already exists.")
    primitive_version.version = version
    primitive_version.input_schema = input_schema
    primitive_version.output_schema = output_schema
    primitive_version.save()
    primitive_version.rules.set(RuleVersion.objects.filter(id__in=rule_version_ids))
    return DraftArtifactResult(
        created=False,
        object_type="primitive_version",
        object_label=str(primitive_version),
        status=primitive_version.status,
        details={"rule_count": primitive_version.rules.count()},
    )


@transaction.atomic
def create_decision_table_draft(
    *,
    code: str,
    name: str,
    scope: str,
    description: str,
    version: str,
    input_primitive_ids: list[int],
    input_columns: list[Any],
    output_columns: list[Any],
    rows: list[dict[str, Any]],
) -> DraftArtifactResult:
    if scope not in ScopeChoices.values:
        raise ValidationError("Invalid scope for decision table definition.")
    decision_table_definition, _ = DecisionTableDefinition.objects.get_or_create(
        code=code,
        defaults={"name": name, "scope": scope, "description": description},
    )
    if DecisionTableVersion.objects.filter(decision_table=decision_table_definition, version=version).exists():
        raise ValidationError(f"{code}@{version} already exists.")
    decision_table_version = DecisionTableVersion.objects.create(
        decision_table=decision_table_definition,
        version=version,
        status=StatusChoices.DRAFT,
        module_scope=scope,
        input_columns=input_columns,
        output_columns=output_columns,
        rows=rows,
        completeness_report={},
    )
    decision_table_version.input_primitives.set(
        PrimitiveVersion.objects.filter(id__in=input_primitive_ids)
    )
    return DraftArtifactResult(
        created=True,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        status=decision_table_version.status,
        details={"input_primitive_count": decision_table_version.input_primitives.count()},
    )


@transaction.atomic
def clone_decision_table_version_to_new_definition(
    *,
    source_decision_table_version_id: int,
    new_code: str,
    name: str,
    scope: str,
    description: str,
    version: str,
) -> DraftArtifactResult:
    source = (
        DecisionTableVersion.objects.select_related("decision_table")
        .prefetch_related("input_primitives__primitive")
        .get(pk=source_decision_table_version_id)
    )
    if DecisionTableDefinition.objects.filter(code=new_code).exists():
        raise ValidationError(f"Decision table definition {new_code} already exists.")
    decision_table_definition = DecisionTableDefinition.objects.create(
        code=new_code,
        name=name,
        scope=scope,
        description=description,
    )
    decision_table_version = DecisionTableVersion.objects.create(
        decision_table=decision_table_definition,
        version=version,
        status=StatusChoices.DRAFT,
        module_scope=scope,
        input_columns=source.input_columns,
        output_columns=source.output_columns,
        rows=source.rows,
        completeness_report={
            **(source.completeness_report or {}),
            "cloned_from": str(source),
        },
    )
    decision_table_version.input_primitives.set(source.input_primitives.all())
    return DraftArtifactResult(
        created=True,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        status=decision_table_version.status,
        details={"cloned_from": str(source)},
    )


@transaction.atomic
def update_decision_table_draft(
    *,
    decision_table_version_id: int,
    version: str,
    input_primitive_ids: list[int],
    input_columns: list[Any],
    output_columns: list[Any],
    rows: list[dict[str, Any]],
) -> DraftArtifactResult:
    decision_table_version = DecisionTableVersion.objects.select_related("decision_table").get(
        pk=decision_table_version_id
    )
    if decision_table_version.status != StatusChoices.DRAFT:
        raise ValidationError("Only draft decision table versions can be edited.")
    if (
        DecisionTableVersion.objects.filter(
            decision_table=decision_table_version.decision_table,
            version=version,
        )
        .exclude(pk=decision_table_version.pk)
        .exists()
    ):
        raise ValidationError(
            f"{decision_table_version.decision_table.code}@{version} already exists."
        )
    decision_table_version.version = version
    decision_table_version.input_columns = input_columns
    decision_table_version.output_columns = output_columns
    decision_table_version.rows = rows
    decision_table_version.save()
    decision_table_version.input_primitives.set(
        PrimitiveVersion.objects.filter(id__in=input_primitive_ids)
    )
    return DraftArtifactResult(
        created=False,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        status=decision_table_version.status,
        details={"input_primitive_count": decision_table_version.input_primitives.count()},
    )


@transaction.atomic
def attach_rule_to_primitive_draft(*, primitive_version_id: int, rule_version_id: int) -> DraftArtifactResult:
    primitive_version = PrimitiveVersion.objects.get(pk=primitive_version_id)
    rule_version = RuleVersion.objects.get(pk=rule_version_id)
    if primitive_version.status != StatusChoices.DRAFT:
        raise ValidationError("Only draft primitive versions can be updated through the promotion guide.")
    primitive_version.rules.add(rule_version)
    return DraftArtifactResult(
        created=False,
        object_type="primitive_version",
        object_label=str(primitive_version),
        status=primitive_version.status,
        details={"attached_rule": str(rule_version)},
    )


@transaction.atomic
def attach_primitive_to_decision_table_draft(
    *,
    decision_table_version_id: int,
    primitive_version_id: int,
) -> DraftArtifactResult:
    decision_table_version = DecisionTableVersion.objects.get(pk=decision_table_version_id)
    primitive_version = PrimitiveVersion.objects.get(pk=primitive_version_id)
    if decision_table_version.status != StatusChoices.DRAFT:
        raise ValidationError("Only draft decision table versions can be updated through the promotion guide.")
    decision_table_version.input_primitives.add(primitive_version)
    return DraftArtifactResult(
        created=False,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        status=decision_table_version.status,
        details={"attached_primitive": str(primitive_version)},
    )


@transaction.atomic
def attach_artifacts_to_module_draft(
    *,
    module_version_id: int,
    primitive_version_ids: list[int] | None = None,
    decision_table_version_ids: list[int] | None = None,
) -> DraftArtifactResult:
    module_version = ModuleVersion.objects.get(pk=module_version_id)
    if module_version.status != ModuleStatusChoices.DRAFT:
        raise ValidationError("Only draft module versions can be updated through the promotion guide.")
    if primitive_version_ids:
        module_version.primitives.add(*PrimitiveVersion.objects.filter(id__in=primitive_version_ids))
    if decision_table_version_ids:
        module_version.decision_tables.add(*DecisionTableVersion.objects.filter(id__in=decision_table_version_ids))
    return DraftArtifactResult(
        created=False,
        object_type="module_version",
        object_label=str(module_version),
        status=module_version.status,
        details={
            "primitive_count": module_version.primitives.count(),
            "decision_table_count": module_version.decision_tables.count(),
        },
    )


def supersede_decision_table_version(
    *,
    source_decision_table_version_id: int,
    replacement_input_primitive_ids: list[int] | None = None,
) -> DecisionTableSupersedeResult:
    source = (
        DecisionTableVersion.objects.select_related("decision_table")
        .prefetch_related("input_primitives__primitive")
        .get(pk=source_decision_table_version_id)
    )
    next_version = _increment_version(source.version)
    while DecisionTableVersion.objects.filter(
        decision_table=source.decision_table,
        version=next_version,
    ).exists():
        next_version = _increment_version(next_version)
    decision_table_version = DecisionTableVersion.objects.create(
        decision_table=source.decision_table,
        version=next_version,
        status=StatusChoices.DRAFT,
        module_scope=source.module_scope,
        input_columns=source.input_columns,
        output_columns=source.output_columns,
        rows=source.rows,
        completeness_report={
            **(source.completeness_report or {}),
            "supersedes": source.version,
            "source_decision_table_version_id": source.id,
        },
    )
    input_primitives = list(source.input_primitives.all())
    if replacement_input_primitive_ids:
        input_primitives = list(PrimitiveVersion.objects.filter(id__in=replacement_input_primitive_ids))
    decision_table_version.input_primitives.set(input_primitives)
    return DecisionTableSupersedeResult(
        created=True,
        source_decision_table_version=str(source),
        new_decision_table_version=str(decision_table_version),
        status=decision_table_version.status,
        input_primitives=[str(item) for item in input_primitives],
    )


@transaction.atomic
def create_module_draft(
    *,
    code: str,
    name: str,
    scope: str,
    description: str,
    version: str,
    assessment_context_code: str,
    primitive_version_ids: list[int],
    decision_table_version_ids: list[int],
    contract_provides: list[Any],
    contract_consumes: list[Any],
    fallback_behaviour: dict[str, Any],
) -> DraftArtifactResult:
    if scope not in ScopeChoices.values:
        raise ValidationError("Invalid scope for module definition.")
    assessment_context = AssessmentContext.objects.get(code=assessment_context_code)
    module_definition, _ = ModuleDefinition.objects.get_or_create(
        code=code,
        defaults={"name": name, "scope": scope, "description": description},
    )
    if ModuleVersion.objects.filter(module=module_definition, version=version).exists():
        raise ValidationError(f"{code}@{version} already exists.")
    module_version = ModuleVersion.objects.create(
        module=module_definition,
        version=version,
        status=ModuleStatusChoices.DRAFT,
        assessment_context=assessment_context,
        contract_provides=contract_provides,
        contract_consumes=contract_consumes,
        fallback_behaviour=fallback_behaviour,
    )
    module_version.primitives.set(PrimitiveVersion.objects.filter(id__in=primitive_version_ids))
    module_version.decision_tables.set(DecisionTableVersion.objects.filter(id__in=decision_table_version_ids))
    return DraftArtifactResult(
        created=True,
        object_type="module_version",
        object_label=str(module_version),
        status=module_version.status,
        details={"assessment_context": assessment_context.code},
    )


@transaction.atomic
def update_module_draft(
    *,
    module_version_id: int,
    version: str,
    assessment_context_code: str,
    primitive_version_ids: list[int],
    decision_table_version_ids: list[int],
    contract_provides: list[Any],
    contract_consumes: list[Any],
    fallback_behaviour: dict[str, Any],
) -> DraftArtifactResult:
    module_version = ModuleVersion.objects.select_related("module").get(pk=module_version_id)
    if module_version.status != ModuleStatusChoices.DRAFT:
        raise ValidationError("Only draft module versions can be edited.")
    assessment_context = AssessmentContext.objects.get(code=assessment_context_code)
    if ModuleVersion.objects.filter(module=module_version.module, version=version).exclude(pk=module_version.pk).exists():
        raise ValidationError(f"{module_version.module.code}@{version} already exists.")
    module_version.version = version
    module_version.assessment_context = assessment_context
    module_version.contract_provides = contract_provides
    module_version.contract_consumes = contract_consumes
    module_version.fallback_behaviour = fallback_behaviour
    module_version.save()
    module_version.primitives.set(PrimitiveVersion.objects.filter(id__in=primitive_version_ids))
    module_version.decision_tables.set(DecisionTableVersion.objects.filter(id__in=decision_table_version_ids))
    return DraftArtifactResult(
        created=False,
        object_type="module_version",
        object_label=str(module_version),
        status=module_version.status,
        details={"assessment_context": assessment_context.code},
    )


def supersede_rule_version(*, source_rule_version_id: int) -> SupersedeResult:
    source = RuleVersion.objects.select_related("rule").get(pk=source_rule_version_id)
    next_version = _increment_version(source.version)

    while RuleVersion.objects.filter(rule=source.rule, version=next_version).exists():
        next_version = _increment_version(next_version)

    copied_metadata = dict(source.metadata or {})
    copied_metadata["supersedes"] = source.version
    copied_metadata["source_rule_version_id"] = source.id

    new_rule_version = RuleVersion.objects.create(
        rule=source.rule,
        version=next_version,
        status=StatusChoices.DRAFT,
        source_reference=source.source_reference,
        natural_language=source.natural_language,
        structured_logic=source.structured_logic,
        mode=source.mode,
        trigger=source.trigger,
        consequence=source.consequence,
        severity=source.severity,
        metadata=copied_metadata,
    )

    return SupersedeResult(
        created=True,
        source_rule_version=str(source),
        new_rule_version=str(new_rule_version),
        status=new_rule_version.status,
    )


def supersede_primitive_version(
    *,
    source_primitive_version_id: int,
    replacement_rule_version_ids: list[int] | None = None,
) -> PrimitiveSupersedeResult:
    source = (
        PrimitiveVersion.objects.select_related("primitive")
        .prefetch_related("rules__rule")
        .get(pk=source_primitive_version_id)
    )
    next_version = _increment_version(source.version)

    while PrimitiveVersion.objects.filter(primitive=source.primitive, version=next_version).exists():
        next_version = _increment_version(next_version)

    new_primitive_version = PrimitiveVersion.objects.create(
        primitive=source.primitive,
        version=next_version,
        status=StatusChoices.DRAFT,
        input_schema=source.input_schema,
        output_schema=source.output_schema,
        completeness_report={
            **(source.completeness_report or {}),
            "supersedes": source.version,
            "source_primitive_version_id": source.id,
        },
    )

    source_rules = list(source.rules.select_related("rule").all())
    replacement_map: dict[int, RuleVersion] = {}
    if replacement_rule_version_ids:
        replacement_versions = RuleVersion.objects.select_related("rule").filter(id__in=replacement_rule_version_ids)
        replacement_map = {item.rule_id: item for item in replacement_versions}

    attached_rules: list[RuleVersion] = []
    for source_rule in source_rules:
        attached_rules.append(replacement_map.get(source_rule.rule_id, source_rule))

    new_primitive_version.rules.set(attached_rules)

    return PrimitiveSupersedeResult(
        created=True,
        source_primitive_version=str(source),
        new_primitive_version=str(new_primitive_version),
        status=new_primitive_version.status,
        rule_versions=[str(item) for item in attached_rules],
    )


def _validate_rule_context(*, rule_version: RuleVersion, assessment_context_code: str) -> None:
    rule_context = (rule_version.metadata or {}).get("assessment_context")
    if rule_context not in {"", None, assessment_context_code}:
        raise ValidationError(
            f"{rule_version} belongs to assessment context {rule_context}, "
            f"not {assessment_context_code}."
        )


def _validate_primitive_context(*, primitive_version: PrimitiveVersion, assessment_context_code: str) -> None:
    for rule_version in primitive_version.rules.all():
        _validate_rule_context(rule_version=rule_version, assessment_context_code=assessment_context_code)


def _validate_decision_table_context(
    *,
    decision_table_version: DecisionTableVersion,
    assessment_context_code: str,
) -> None:
    for primitive_version in decision_table_version.input_primitives.all():
        _validate_primitive_context(
            primitive_version=primitive_version,
            assessment_context_code=assessment_context_code,
        )


def _validate_draft_version(*, obj, assessment_context_code: str) -> None:
    if obj.status != StatusChoices.DRAFT:
        raise ValidationError(f"{obj} must be in DRAFT status to be bundled into a draft change set.")

    if isinstance(obj, RuleVersion):
        _validate_rule_context(rule_version=obj, assessment_context_code=assessment_context_code)
        return

    if isinstance(obj, PrimitiveVersion):
        _validate_primitive_context(
            primitive_version=obj,
            assessment_context_code=assessment_context_code,
        )
        return

    if isinstance(obj, DecisionTableVersion):
        _validate_decision_table_context(
            decision_table_version=obj,
            assessment_context_code=assessment_context_code,
        )
        return

    if isinstance(obj, ModuleVersion) and obj.assessment_context.code != assessment_context_code:
        raise ValidationError(
            f"{obj} belongs to assessment context {obj.assessment_context.code}, "
            f"not {assessment_context_code}."
        )


@transaction.atomic
def create_or_update_draft_change_set_bundle(
    *,
    code: str,
    name: str,
    description: str,
    assessment_context_code: str,
    rule_version_ids: list[int] | None = None,
    primitive_version_ids: list[int] | None = None,
    decision_table_version_ids: list[int] | None = None,
    module_version_ids: list[int] | None = None,
) -> DraftChangeSetBundleResult:
    assessment_context = AssessmentContext.objects.get(code=assessment_context_code)
    rule_version_ids = rule_version_ids or []
    primitive_version_ids = primitive_version_ids or []
    decision_table_version_ids = decision_table_version_ids or []
    module_version_ids = module_version_ids or []

    change_set = ChangeSet.objects.filter(code=code).first()
    created = change_set is None
    if change_set is None:
        change_set = ChangeSet.objects.create(
            code=code,
            name=name,
            description=description,
            assessment_context=assessment_context,
            status=StatusChoices.DRAFT,
        )
    else:
        if change_set.status != StatusChoices.DRAFT:
            raise ValidationError(
                f"Change set {change_set.code} is in status {change_set.status} and cannot be modified."
            )
        if change_set.assessment_context_id != assessment_context.id:
            raise ValidationError(
                f"Change set {change_set.code} belongs to assessment context "
                f"{change_set.assessment_context.code}, not {assessment_context_code}."
            )
        change_set.name = name
        change_set.description = description
        change_set.activation_report = {}
        change_set.save()

    explicit_rule_versions = list(RuleVersion.objects.select_related("rule").filter(id__in=rule_version_ids))
    explicit_primitive_versions = list(
        PrimitiveVersion.objects.select_related("primitive")
        .prefetch_related("rules__rule")
        .filter(id__in=primitive_version_ids)
    )
    explicit_decision_table_versions = list(
        DecisionTableVersion.objects.select_related("decision_table")
        .prefetch_related("input_primitives__rules")
        .filter(id__in=decision_table_version_ids)
    )
    explicit_module_versions = list(
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related("primitives__rules", "decision_tables__input_primitives")
        .filter(id__in=module_version_ids)
    )

    if len(explicit_rule_versions) != len(set(rule_version_ids)):
        raise ValidationError("One or more rule version ids were not found.")
    if len(explicit_primitive_versions) != len(set(primitive_version_ids)):
        raise ValidationError("One or more primitive version ids were not found.")
    if len(explicit_decision_table_versions) != len(set(decision_table_version_ids)):
        raise ValidationError("One or more decision table version ids were not found.")
    if len(explicit_module_versions) != len(set(module_version_ids)):
        raise ValidationError("One or more module version ids were not found.")

    for item in explicit_rule_versions + explicit_primitive_versions + explicit_decision_table_versions:
        _validate_draft_version(obj=item, assessment_context_code=assessment_context_code)
    for item in explicit_module_versions:
        _validate_draft_version(obj=item, assessment_context_code=assessment_context_code)

    bundled_rule_versions: dict[int, RuleVersion] = {item.id: item for item in explicit_rule_versions}
    bundled_primitive_versions: dict[int, PrimitiveVersion] = {item.id: item for item in explicit_primitive_versions}
    bundled_decision_tables: dict[int, DecisionTableVersion] = {
        item.id: item for item in explicit_decision_table_versions
    }
    bundled_modules: dict[int, ModuleVersion] = {item.id: item for item in explicit_module_versions}

    for primitive_version in list(bundled_primitive_versions.values()):
        for rule_version in primitive_version.rules.select_related("rule").all():
            if rule_version.status == StatusChoices.DRAFT:
                _validate_draft_version(obj=rule_version, assessment_context_code=assessment_context_code)
                bundled_rule_versions[rule_version.id] = rule_version

    for decision_table_version in list(bundled_decision_tables.values()):
        for primitive_version in decision_table_version.input_primitives.prefetch_related("rules__rule").all():
            if primitive_version.status == StatusChoices.DRAFT:
                _validate_draft_version(obj=primitive_version, assessment_context_code=assessment_context_code)
                bundled_primitive_versions[primitive_version.id] = primitive_version

    for module_version in list(bundled_modules.values()):
        for primitive_version in module_version.primitives.prefetch_related("rules__rule").all():
            if primitive_version.status == StatusChoices.DRAFT:
                _validate_draft_version(obj=primitive_version, assessment_context_code=assessment_context_code)
                bundled_primitive_versions[primitive_version.id] = primitive_version
        for decision_table_version in module_version.decision_tables.prefetch_related("input_primitives__rules").all():
            if decision_table_version.status == StatusChoices.DRAFT:
                _validate_draft_version(obj=decision_table_version, assessment_context_code=assessment_context_code)
                bundled_decision_tables[decision_table_version.id] = decision_table_version

    for primitive_version in list(bundled_primitive_versions.values()):
        for rule_version in primitive_version.rules.select_related("rule").all():
            if rule_version.status == StatusChoices.DRAFT:
                bundled_rule_versions[rule_version.id] = rule_version

    auto_included = {
        "rule_versions": sorted(
            str(item)
            for item in bundled_rule_versions.values()
            if item.id not in set(rule_version_ids)
        ),
        "primitive_versions": sorted(
            str(item)
            for item in bundled_primitive_versions.values()
            if item.id not in set(primitive_version_ids)
        ),
        "decision_table_versions": sorted(
            str(item)
            for item in bundled_decision_tables.values()
            if item.id not in set(decision_table_version_ids)
        ),
        "module_versions": sorted(
            str(item)
            for item in bundled_modules.values()
            if item.id not in set(module_version_ids)
        ),
    }

    change_set.rule_versions.set(sorted(bundled_rule_versions.values(), key=lambda item: item.id))
    change_set.primitive_versions.set(sorted(bundled_primitive_versions.values(), key=lambda item: item.id))
    change_set.decision_table_versions.set(sorted(bundled_decision_tables.values(), key=lambda item: item.id))
    change_set.module_versions.set(sorted(bundled_modules.values(), key=lambda item: item.id))
    change_set.impact_analysis = {
        "auto_included": auto_included,
        "requested_counts": {
            "rule_versions": len(rule_version_ids),
            "primitive_versions": len(primitive_version_ids),
            "decision_table_versions": len(decision_table_version_ids),
            "module_versions": len(module_version_ids),
        },
    }
    change_set.save()

    return DraftChangeSetBundleResult(
        created=created,
        code=change_set.code,
        name=change_set.name,
        status=change_set.status,
        assessment_context=change_set.assessment_context.code,
        summary={
            "rule_version_count": change_set.rule_versions.count(),
            "primitive_version_count": change_set.primitive_versions.count(),
            "decision_table_version_count": change_set.decision_table_versions.count(),
            "module_version_count": change_set.module_versions.count(),
            "rule_versions": [str(item) for item in change_set.rule_versions.select_related("rule").all()],
            "primitive_versions": [
                str(item) for item in change_set.primitive_versions.select_related("primitive").all()
            ],
            "decision_table_versions": [
                str(item)
                for item in change_set.decision_table_versions.select_related("decision_table").all()
            ],
            "module_versions": [
                str(item) for item in change_set.module_versions.select_related("module").all()
            ],
            "auto_included": auto_included,
        },
    )


def _ensure_transition_allowed(*, current_status: str, allowed_from: tuple[str, ...], object_label: str) -> None:
    if current_status not in allowed_from:
        allowed = ", ".join(allowed_from)
        raise ValidationError(f"{object_label} must be in one of [{allowed}] to perform this transition.")


@transaction.atomic
def submit_rule_version_for_review(*, rule_version_id: int) -> LifecycleTransitionResult:
    rule_version = RuleVersion.objects.select_related("rule").get(pk=rule_version_id)
    _ensure_transition_allowed(
        current_status=rule_version.status,
        allowed_from=(StatusChoices.DRAFT,),
        object_label=str(rule_version),
    )
    previous_status = rule_version.status
    rule_version.status = StatusChoices.UNDER_REVIEW
    rule_version.save(update_fields=["status", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="rule_version",
        object_label=str(rule_version),
        from_status=previous_status,
        to_status=rule_version.status,
    )


@transaction.atomic
def approve_rule_version(*, rule_version_id: int, approved_by: str) -> LifecycleTransitionResult:
    rule_version = RuleVersion.objects.select_related("rule").get(pk=rule_version_id)
    _ensure_transition_allowed(
        current_status=rule_version.status,
        allowed_from=(StatusChoices.UNDER_REVIEW,),
        object_label=str(rule_version),
    )
    validation = validate_rule_version_payload(
        {
            "source_reference": rule_version.source_reference,
            "natural_language": rule_version.natural_language,
            "structured_logic": rule_version.structured_logic,
            "mode": rule_version.mode,
            "severity": rule_version.severity,
        }
    )
    if not validation.is_valid:
        raise ValidationError(validation.issues[0].message)

    previous_status = rule_version.status
    rule_version.status = StatusChoices.APPROVED
    rule_version.approved_by = approved_by
    rule_version.approved_at = timezone.now()
    rule_version.full_clean()
    rule_version.save()
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="rule_version",
        object_label=str(rule_version),
        from_status=previous_status,
        to_status=rule_version.status,
    )


@transaction.atomic
def submit_primitive_version_for_review(*, primitive_version_id: int) -> LifecycleTransitionResult:
    primitive_version = PrimitiveVersion.objects.select_related("primitive").get(pk=primitive_version_id)
    _ensure_transition_allowed(
        current_status=primitive_version.status,
        allowed_from=(StatusChoices.DRAFT,),
        object_label=str(primitive_version),
    )
    previous_status = primitive_version.status
    primitive_version.status = StatusChoices.UNDER_REVIEW
    primitive_version.save(update_fields=["status", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="primitive_version",
        object_label=str(primitive_version),
        from_status=previous_status,
        to_status=primitive_version.status,
    )


@transaction.atomic
def approve_primitive_version(*, primitive_version_id: int, approved_by: str) -> LifecycleTransitionResult:
    primitive_version = (
        PrimitiveVersion.objects.select_related("primitive")
        .prefetch_related("rules__rule")
        .get(pk=primitive_version_id)
    )
    _ensure_transition_allowed(
        current_status=primitive_version.status,
        allowed_from=(StatusChoices.UNDER_REVIEW,),
        object_label=str(primitive_version),
    )

    completeness = validate_primitive_completeness(
        input_schema=primitive_version.input_schema,
        output_schema=primitive_version.output_schema,
        rule_count=primitive_version.rules.count(),
    )
    if not completeness.is_valid:
        raise ValidationError(completeness.issues[0].message)

    conflict_check = detect_primitive_conflicts(
        [item.structured_logic for item in primitive_version.rules.all()]
    )
    if not conflict_check.is_valid:
        raise ValidationError(conflict_check.issues[0].message)

    non_approved_rule_versions = [
        str(rule_version)
        for rule_version in primitive_version.rules.all()
        if rule_version.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}
    ]
    if non_approved_rule_versions:
        raise ValidationError(
            "Primitive version cannot be approved until all linked rule versions are approved or active."
        )

    previous_status = primitive_version.status
    primitive_version.status = StatusChoices.APPROVED
    primitive_version.approved_by = approved_by
    primitive_version.approved_at = timezone.now()
    primitive_version.full_clean()
    primitive_version.save()
    primitive_version.completeness_report = {
        **(primitive_version.completeness_report or {}),
        "approval_checks": {
            "rule_count": primitive_version.rules.count(),
            "completeness_valid": True,
            "conflict_free": True,
        },
    }
    primitive_version.save(update_fields=["completeness_report", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="primitive_version",
        object_label=str(primitive_version),
        from_status=previous_status,
        to_status=primitive_version.status,
        readiness={
            "rule_versions": [str(item) for item in primitive_version.rules.all()],
        },
    )


@transaction.atomic
def submit_decision_table_version_for_review(*, decision_table_version_id: int) -> LifecycleTransitionResult:
    decision_table_version = DecisionTableVersion.objects.select_related("decision_table").get(
        pk=decision_table_version_id
    )
    _ensure_transition_allowed(
        current_status=decision_table_version.status,
        allowed_from=(StatusChoices.DRAFT,),
        object_label=str(decision_table_version),
    )
    previous_status = decision_table_version.status
    decision_table_version.status = StatusChoices.UNDER_REVIEW
    decision_table_version.save(update_fields=["status", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        from_status=previous_status,
        to_status=decision_table_version.status,
    )


@transaction.atomic
def approve_decision_table_version(*, decision_table_version_id: int, approved_by: str) -> LifecycleTransitionResult:
    decision_table_version = (
        DecisionTableVersion.objects.select_related("decision_table")
        .prefetch_related("input_primitives__primitive")
        .get(pk=decision_table_version_id)
    )
    _ensure_transition_allowed(
        current_status=decision_table_version.status,
        allowed_from=(StatusChoices.UNDER_REVIEW,),
        object_label=str(decision_table_version),
    )
    completeness = validate_decision_table_completeness(
        input_columns=decision_table_version.input_columns,
        output_columns=decision_table_version.output_columns,
        row_count=len(decision_table_version.rows or []),
        input_primitive_count=decision_table_version.input_primitives.count(),
    )
    if not completeness.is_valid:
        raise ValidationError(completeness.issues[0].message)
    non_ready_inputs = [
        str(item)
        for item in decision_table_version.input_primitives.all()
        if item.status not in {StatusChoices.APPROVED, StatusChoices.ACTIVE}
    ]
    if non_ready_inputs:
        raise ValidationError(
            "Decision table version cannot be approved until all input primitives are approved or active."
        )
    previous_status = decision_table_version.status
    decision_table_version.status = StatusChoices.APPROVED
    decision_table_version.approved_by = approved_by
    decision_table_version.approved_at = timezone.now()
    decision_table_version.save()
    decision_table_version.completeness_report = {
        **(decision_table_version.completeness_report or {}),
        "approval_checks": {
            "input_primitive_count": decision_table_version.input_primitives.count(),
            "row_count": len(decision_table_version.rows or []),
            "completeness_valid": True,
        },
    }
    decision_table_version.save(update_fields=["completeness_report", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="decision_table_version",
        object_label=str(decision_table_version),
        from_status=previous_status,
        to_status=decision_table_version.status,
        readiness={
            "input_primitives": [str(item) for item in decision_table_version.input_primitives.all()],
        },
    )


def supersede_module_version(
    *,
    source_module_version_id: int,
    replacement_primitive_version_ids: list[int] | None = None,
    replacement_decision_table_version_ids: list[int] | None = None,
) -> ModuleSupersedeResult:
    source = (
        ModuleVersion.objects.select_related("module", "assessment_context")
        .prefetch_related("primitives", "decision_tables")
        .get(pk=source_module_version_id)
    )
    next_version = _increment_version(source.version)
    while ModuleVersion.objects.filter(module=source.module, version=next_version).exists():
        next_version = _increment_version(next_version)

    new_module_version = ModuleVersion.objects.create(
        module=source.module,
        version=next_version,
        status=ModuleStatusChoices.DRAFT,
        assessment_context=source.assessment_context,
        contract_provides=source.contract_provides,
        contract_consumes=source.contract_consumes,
        fallback_behaviour=source.fallback_behaviour,
    )
    primitives = list(source.primitives.all())
    decision_tables = list(source.decision_tables.all())
    if replacement_primitive_version_ids:
        primitives = list(PrimitiveVersion.objects.filter(id__in=replacement_primitive_version_ids))
    if replacement_decision_table_version_ids:
        decision_tables = list(DecisionTableVersion.objects.filter(id__in=replacement_decision_table_version_ids))
    new_module_version.primitives.set(primitives)
    new_module_version.decision_tables.set(decision_tables)
    return ModuleSupersedeResult(
        created=True,
        source_module_version=str(source),
        new_module_version=str(new_module_version),
        status=new_module_version.status,
        primitive_versions=[str(item) for item in primitives],
        decision_table_versions=[str(item) for item in decision_tables],
    )


@transaction.atomic
def submit_module_version_for_review(*, module_version_id: int) -> LifecycleTransitionResult:
    module_version = ModuleVersion.objects.select_related("module", "assessment_context").get(pk=module_version_id)
    _ensure_transition_allowed(
        current_status=module_version.status,
        allowed_from=(ModuleStatusChoices.DRAFT,),
        object_label=str(module_version),
    )
    previous_status = module_version.status
    module_version.status = ModuleStatusChoices.UNDER_REVIEW
    module_version.save(update_fields=["status", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="module_version",
        object_label=str(module_version),
        from_status=previous_status,
        to_status=module_version.status,
    )


@transaction.atomic
def approve_module_version(*, module_version_id: int, approved_by: str) -> LifecycleTransitionResult:
    module_version = ModuleVersion.objects.get(pk=module_version_id)
    _ensure_transition_allowed(
        current_status=module_version.status,
        allowed_from=(ModuleStatusChoices.UNDER_REVIEW,),
        object_label=str(module_version),
    )
    readiness = evaluate_module_version_readiness(module_version=module_version)
    if not readiness.is_ready:
        raise ValidationError("Module version cannot be approved until readiness checks pass.")
    previous_status = module_version.status
    module_version.status = ModuleStatusChoices.APPROVED
    module_version.approved_by = approved_by
    module_version.approved_at = timezone.now()
    module_version.full_clean()
    module_version.save()
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="module_version",
        object_label=str(module_version),
        from_status=previous_status,
        to_status=module_version.status,
        readiness={
            "summary": readiness.summary,
            "issues": [],
        },
    )


@transaction.atomic
def submit_change_set_for_review(*, change_set_code: str) -> LifecycleTransitionResult:
    change_set = ChangeSet.objects.get(code=change_set_code)
    _ensure_transition_allowed(
        current_status=change_set.status,
        allowed_from=(StatusChoices.DRAFT,),
        object_label=change_set.code,
    )
    previous_status = change_set.status
    change_set.status = StatusChoices.UNDER_REVIEW
    change_set.save(update_fields=["status", "updated_at"])
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="change_set",
        object_label=change_set.code,
        from_status=previous_status,
        to_status=change_set.status,
    )


@transaction.atomic
def approve_change_set(*, change_set_code: str, approved_by: str) -> LifecycleTransitionResult:
    change_set = ChangeSet.objects.get(code=change_set_code)
    _ensure_transition_allowed(
        current_status=change_set.status,
        allowed_from=(StatusChoices.UNDER_REVIEW,),
        object_label=change_set.code,
    )

    readiness_report = build_change_set_activation_report(change_set=change_set)
    change_set.activation_report = {
        "change_set_code": readiness_report.change_set_code,
        "assessment_context": readiness_report.assessment_context,
        "is_ready": readiness_report.is_ready,
        "summary": readiness_report.summary,
        "issues": [
            {"code": issue.code, "message": issue.message, "details": issue.details}
            for issue in readiness_report.issues
        ],
    }
    if not readiness_report.is_ready:
        change_set.save(update_fields=["activation_report", "updated_at"])
        raise ValidationError("Change set cannot be approved until activation readiness passes.")

    previous_status = change_set.status
    change_set.status = StatusChoices.APPROVED
    change_set.approved_by = approved_by
    change_set.approved_at = timezone.now()
    change_set.full_clean()
    change_set.save()
    return LifecycleTransitionResult(
        transitioned=True,
        object_type="change_set",
        object_label=change_set.code,
        from_status=previous_status,
        to_status=change_set.status,
        readiness=change_set.activation_report,
    )


def _activate_version_set(*, queryset, current_ids: set[int], active_status: str, superseded_status: str) -> tuple[int, int]:
    existing_active_ids = set(queryset.filter(status=active_status).values_list("id", flat=True))
    to_supersede_ids = existing_active_ids - current_ids
    superseded_count = queryset.filter(id__in=to_supersede_ids).update(status=superseded_status)
    activated_count = queryset.filter(id__in=current_ids).exclude(status=active_status).update(status=active_status)
    return activated_count, superseded_count


@transaction.atomic
def activate_change_set(*, change_set_code: str, activated_by: str) -> ChangeSetActivationResult:
    change_set = ChangeSet.objects.get(code=change_set_code)
    _ensure_transition_allowed(
        current_status=change_set.status,
        allowed_from=(StatusChoices.APPROVED,),
        object_label=change_set.code,
    )

    readiness_report = build_change_set_activation_report(change_set=change_set)
    if not readiness_report.is_ready:
        change_set.activation_report = {
            "change_set_code": readiness_report.change_set_code,
            "assessment_context": readiness_report.assessment_context,
            "is_ready": readiness_report.is_ready,
            "summary": readiness_report.summary,
            "issues": [
                {"code": issue.code, "message": issue.message, "details": issue.details}
                for issue in readiness_report.issues
            ],
        }
        change_set.save(update_fields=["activation_report", "updated_at"])
        raise ValidationError("Change set cannot be activated until activation readiness passes.")

    rule_versions = list(change_set.rule_versions.select_related("rule").all())
    primitive_versions = list(change_set.primitive_versions.select_related("primitive").all())
    decision_table_versions = list(
        change_set.decision_table_versions.select_related("decision_table").all()
    )
    module_versions = list(change_set.module_versions.select_related("module", "assessment_context").all())

    rule_current_ids = {item.id for item in rule_versions}
    primitive_current_ids = {item.id for item in primitive_versions}
    decision_table_current_ids = {item.id for item in decision_table_versions}
    module_current_ids = {item.id for item in module_versions}

    activated_rule_count = superseded_rule_count = 0
    if rule_versions:
        rule_ids = {item.rule_id for item in rule_versions}
        activated_rule_count, superseded_rule_count = _activate_version_set(
            queryset=RuleVersion.objects.filter(rule_id__in=rule_ids),
            current_ids=rule_current_ids,
            active_status=StatusChoices.ACTIVE,
            superseded_status=StatusChoices.SUPERSEDED,
        )

    activated_primitive_count = superseded_primitive_count = 0
    if primitive_versions:
        primitive_ids = {item.primitive_id for item in primitive_versions}
        activated_primitive_count, superseded_primitive_count = _activate_version_set(
            queryset=PrimitiveVersion.objects.filter(primitive_id__in=primitive_ids),
            current_ids=primitive_current_ids,
            active_status=StatusChoices.ACTIVE,
            superseded_status=StatusChoices.SUPERSEDED,
        )

    activated_decision_table_count = superseded_decision_table_count = 0
    if decision_table_versions:
        decision_table_ids = {item.decision_table_id for item in decision_table_versions}
        activated_decision_table_count, superseded_decision_table_count = _activate_version_set(
            queryset=DecisionTableVersion.objects.filter(decision_table_id__in=decision_table_ids),
            current_ids=decision_table_current_ids,
            active_status=StatusChoices.ACTIVE,
            superseded_status=StatusChoices.SUPERSEDED,
        )

    activated_module_count = superseded_module_count = 0
    if module_versions:
        module_keys = {(item.module_id, item.assessment_context_id) for item in module_versions}
        module_queryset = ModuleVersion.objects.none()
        for module_id, assessment_context_id in module_keys:
            module_queryset = module_queryset | ModuleVersion.objects.filter(
                module_id=module_id,
                assessment_context_id=assessment_context_id,
            )
        activated_module_count, superseded_module_count = _activate_version_set(
            queryset=module_queryset,
            current_ids=module_current_ids,
            active_status=ModuleStatusChoices.ACTIVE,
            superseded_status=ModuleStatusChoices.SUPERSEDED,
        )

    previous_status = change_set.status
    now = timezone.now()
    change_set.status = StatusChoices.ACTIVE
    change_set.activated_at = now
    change_set.activation_report = {
        "change_set_code": readiness_report.change_set_code,
        "assessment_context": readiness_report.assessment_context,
        "is_ready": readiness_report.is_ready,
        "summary": {
            **readiness_report.summary,
            "activated_by": activated_by,
            "activated_rule_count": activated_rule_count,
            "superseded_rule_count": superseded_rule_count,
            "activated_primitive_count": activated_primitive_count,
            "superseded_primitive_count": superseded_primitive_count,
            "activated_decision_table_count": activated_decision_table_count,
            "superseded_decision_table_count": superseded_decision_table_count,
            "activated_module_count": activated_module_count,
            "superseded_module_count": superseded_module_count,
        },
        "issues": [],
    }
    change_set.save(update_fields=["status", "activated_at", "activation_report", "updated_at"])

    return ChangeSetActivationResult(
        activated=True,
        change_set_code=change_set.code,
        from_status=previous_status,
        to_status=change_set.status,
        activated_at=now.isoformat(),
        summary=change_set.activation_report["summary"],
    )
