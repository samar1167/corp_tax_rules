from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from audit.services import create_evaluation_log
from corporate_tax.models import CorporateTaxEvaluation
from corporate_tax.serializers import CorporateTaxProfileSerializer
from corporate_tax.services import evaluate_corporate_tax_concept
from governance.models import GovernanceEvaluation
from governance.services import evaluate_cross_module_governance
from itr.models import ITREvaluation, ITRRegimeEvaluation, ITRTaxComputationEvaluation
from itr.serializers import RegimeSelectionSerializer, TaxComputationSerializer, TaxpayerProfileSerializer
from itr.services import (
    evaluate_itr_regime_selection,
    evaluate_itr_tax_computation,
    evaluate_itr1_form_eligibility,
)

from .models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableVersion,
    ModuleStatusChoices,
    ModuleVersion,
    PrimitiveVersion,
    RuleVersion,
    StatusChoices,
)
from .services import (
    activate_change_set,
    attach_artifacts_to_module_draft,
    attach_primitive_to_decision_table_draft,
    attach_rule_to_primitive_draft,
    approve_change_set,
    approve_decision_table_version,
    approve_module_version,
    approve_primitive_version,
    approve_rule_version,
    build_change_set_activation_report,
    build_module_readiness_report,
    clone_decision_table_version_to_new_definition,
    clone_primitive_version_to_new_definition,
    clone_rule_version_to_new_definition,
    create_decision_table_draft,
    create_module_draft,
    create_primitive_draft,
    create_rule_draft,
    create_or_update_draft_change_set_bundle,
    evaluate_module_version_readiness,
    submit_change_set_for_review,
    submit_decision_table_version_for_review,
    submit_module_version_for_review,
    submit_primitive_version_for_review,
    submit_rule_version_for_review,
    supersede_decision_table_version,
    supersede_module_version,
    supersede_primitive_version,
    supersede_rule_version,
    update_decision_table_draft,
    update_module_draft,
    update_primitive_draft,
    update_rule_draft,
)


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _bool_from_post(request: HttpRequest, key: str) -> bool:
    return request.POST.get(key) in {"on", "true", "True", "1"}


def _json_input(raw_value: str, default):
    value = (raw_value or "").strip()
    if not value:
        return default
    return json.loads(value)


def _int_list(values: list[str]) -> list[int]:
    return [int(value) for value in values if value]


def _load_todo_sections() -> list[dict]:
    todo_path = Path(settings.BASE_DIR) / "todo.md"
    if not todo_path.exists():
        return []

    sections: list[dict] = []
    current: dict | None = None
    for raw_line in todo_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            current = {"title": line[3:].strip(), "items": []}
            sections.append(current)
            continue
        if line.startswith("- ") and current is not None:
            current["items"].append(line[2:].strip())
    return sections


def _store_latest_result(request: HttpRequest, *, title: str, payload: dict) -> None:
    request.session["workflow_latest_result"] = {
        "title": title,
        "payload": _json_safe(payload),
    }


def _pop_latest_result(request: HttpRequest) -> dict | None:
    return request.session.pop("workflow_latest_result", None)


def _build_dashboard_context(request: HttpRequest) -> dict:
    latest_result = _pop_latest_result(request)
    active_module = ModuleVersion.objects.select_related("module", "assessment_context").filter(
        module__code="INDIA_INDIVIDUAL_TAX",
        status="ACTIVE",
    ).first()
    active_corporate_module = ModuleVersion.objects.select_related("module", "assessment_context").filter(
        module__code="INDIA_CORPORATE_TAX",
        status="ACTIVE",
    ).first()
    readiness = (
        build_module_readiness_report(
            module_code="INDIA_INDIVIDUAL_TAX",
            assessment_context=active_module.assessment_context.code,
        )
        if active_module
        else None
    )
    corporate_readiness = (
        build_module_readiness_report(
            module_code="INDIA_CORPORATE_TAX",
            assessment_context=active_corporate_module.assessment_context.code,
        )
        if active_corporate_module
        else None
    )

    approved_change_sets = ChangeSet.objects.select_related("assessment_context").filter(
        status=StatusChoices.APPROVED
    )
    latest_approved_change_set = approved_change_sets.first()
    latest_activation_readiness = (
        build_change_set_activation_report(change_set=latest_approved_change_set)
        if latest_approved_change_set
        else None
    )

    return {
        "stats": {
            "rule_versions": RuleVersion.objects.count(),
            "primitive_versions": PrimitiveVersion.objects.count(),
            "module_versions": ModuleVersion.objects.count(),
            "change_sets": ChangeSet.objects.count(),
            "audit_ready_modules": ModuleVersion.objects.filter(status="ACTIVE").count(),
            "itr_runs": ITREvaluation.objects.count()
            + ITRRegimeEvaluation.objects.count()
            + ITRTaxComputationEvaluation.objects.count(),
            "corporate_runs": CorporateTaxEvaluation.objects.count(),
            "governance_runs": GovernanceEvaluation.objects.count(),
        },
        "todo_sections": _load_todo_sections(),
        "latest_result": latest_result,
        "latest_result_pretty": (
            json.dumps(latest_result["payload"], indent=2) if latest_result else ""
        ),
        "assessment_contexts": AssessmentContext.objects.order_by("-effective_from"),
        "rule_version_options": RuleVersion.objects.select_related("rule").order_by("rule__rule_id", "-id"),
        "primitive_version_options": PrimitiveVersion.objects.select_related("primitive").order_by(
            "primitive__code",
            "-id",
        ),
        "decision_table_version_options": DecisionTableVersion.objects.select_related(
            "decision_table"
        ).order_by("decision_table__code", "-id"),
        "module_version_options": ModuleVersion.objects.select_related("module", "assessment_context").order_by(
            "module__code",
            "-id",
        ),
        "draft_rules": RuleVersion.objects.select_related("rule").filter(status=StatusChoices.DRAFT)[:20],
        "draft_primitives": PrimitiveVersion.objects.select_related("primitive").filter(
            status=StatusChoices.DRAFT
        )[:20],
        "draft_change_sets": ChangeSet.objects.select_related("assessment_context").filter(
            status=StatusChoices.DRAFT
        )[:20],
        "draft_decision_tables": DecisionTableVersion.objects.select_related("decision_table").filter(
            status=StatusChoices.DRAFT
        )[:20],
        "draft_modules": ModuleVersion.objects.select_related("module", "assessment_context").filter(
            status=ModuleStatusChoices.DRAFT
        )[:20],
        "under_review_rules": RuleVersion.objects.select_related("rule").filter(
            status=StatusChoices.UNDER_REVIEW
        )[:20],
        "under_review_primitives": PrimitiveVersion.objects.select_related("primitive").filter(
            status=StatusChoices.UNDER_REVIEW
        )[:20],
        "under_review_decision_tables": DecisionTableVersion.objects.select_related(
            "decision_table"
        ).filter(status=StatusChoices.UNDER_REVIEW)[:20],
        "under_review_modules": ModuleVersion.objects.select_related("module", "assessment_context").filter(
            status=ModuleStatusChoices.UNDER_REVIEW
        )[:20],
        "under_review_change_sets": ChangeSet.objects.select_related("assessment_context").filter(
            status=StatusChoices.UNDER_REVIEW
        )[:20],
        "approved_modules": ModuleVersion.objects.select_related("module", "assessment_context").filter(
            status=ModuleStatusChoices.APPROVED
        )[:20],
        "approved_change_sets": approved_change_sets[:20],
        "active_change_sets": ChangeSet.objects.select_related("assessment_context").filter(
            status=StatusChoices.ACTIVE
        )[:20],
        "catalog_rule_versions": RuleVersion.objects.select_related("rule").all()[:30],
        "catalog_primitive_versions": PrimitiveVersion.objects.select_related("primitive").all()[:30],
        "catalog_decision_table_versions": DecisionTableVersion.objects.select_related(
            "decision_table"
        ).all()[:30],
        "catalog_module_versions": ModuleVersion.objects.select_related("module", "assessment_context").all()[:30],
        "recent_form_evaluations": ITREvaluation.objects.all()[:5],
        "recent_regime_evaluations": ITRRegimeEvaluation.objects.all()[:5],
        "recent_tax_evaluations": ITRTaxComputationEvaluation.objects.all()[:5],
        "recent_corporate_evaluations": CorporateTaxEvaluation.objects.all()[:5],
        "recent_governance_evaluations": GovernanceEvaluation.objects.all()[:5],
        "module_readiness": readiness,
        "corporate_module_readiness": corporate_readiness,
        "latest_activation_readiness": latest_activation_readiness,
        "active_module": active_module,
        "active_corporate_module": active_corporate_module,
        "sample_payloads": {
            "form": {
                "assessment_context": "AY_2026_27",
                "residential_status": "RESIDENT_ORDINARY",
                "total_income": 1200000,
                "category": "INDIVIDUAL",
                "is_director_in_company": False,
                "has_unlisted_equity_investment": False,
                "has_foreign_assets": False,
                "has_foreign_account_signing_authority": False,
                "income_sources": ["SALARY"],
                "has_capital_gains": False,
                "capital_gain_type": "",
                "ltcg_112a_amount": 0,
                "has_carried_forward_capital_loss": False,
                "house_property_count": 1,
                "has_brought_forward_house_property_loss": False,
                "tds_deducted_under_194N": False,
                "has_esop_tax_deferred": False,
                "has_business_profession_income": False,
            },
            "regime": {
                "assessment_context": "AY_2026_27",
                "has_business_profession_income": False,
                "regime_selection": "OLD_REGIME",
                "filing_date": "2026-07-20",
                "due_date_139_1": "2026-07-31",
            },
            "tax": {
                "assessment_context": "AY_2026_27",
                "applicable_regime": "NEW_REGIME",
                "taxable_income": 1500000,
                "special_rate_income": 0,
            },
            "corporate": {
                "assessment_context": "TY_2026_27",
                "registration_country": "INDIA",
                "registration_act": "COMPANIES_ACT",
                "incorporation_date": "2020-01-15",
                "business_activity": "MANUFACTURING",
                "previous_year_turnover": 3500000000,
                "construction_project_duration_days": 0,
                "regime_option": "OPT_115BAB",
            },
            "governance": {
                "itr_assessment_context": "AY_2026_27",
                "corporate_assessment_context": "TY_2026_27",
                "governance_assessment_context": "GOV_2026_27",
            },
        },
    }


def _query_int(request: HttpRequest, key: str) -> int | None:
    value = request.GET.get(key) or request.POST.get(key)
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _promotion_redirect(
    *,
    rule_id: int | None,
    primitive_id: int | None,
    decision_table_id: int | None,
    module_id: int | None,
    change_set_code: str | None,
) -> str:
    params = []
    if rule_id:
        params.append(f"rule={rule_id}")
    if primitive_id:
        params.append(f"primitive={primitive_id}")
    if decision_table_id:
        params.append(f"decision_table={decision_table_id}")
    if module_id:
        params.append(f"module={module_id}")
    if change_set_code:
        params.append(f"change_set={change_set_code}")
    suffix = f"?{'&'.join(params)}" if params else ""
    return f"/workflow/promotion/{suffix}"


def _build_promotion_context(request: HttpRequest) -> dict:
    selected_rule = None
    selected_primitive = None
    selected_decision_table = None
    selected_module = None
    selected_change_set = None

    rule_id = _query_int(request, "rule")
    primitive_id = _query_int(request, "primitive")
    decision_table_id = _query_int(request, "decision_table")
    module_id = _query_int(request, "module")
    change_set_code = request.GET.get("change_set") or request.POST.get("change_set_code")

    if rule_id:
        selected_rule = RuleVersion.objects.select_related("rule").filter(pk=rule_id).first()
    if primitive_id:
        selected_primitive = (
            PrimitiveVersion.objects.select_related("primitive")
            .prefetch_related("rules__rule")
            .filter(pk=primitive_id)
            .first()
        )
    if decision_table_id:
        selected_decision_table = (
            DecisionTableVersion.objects.select_related("decision_table")
            .prefetch_related("input_primitives__primitive")
            .filter(pk=decision_table_id)
            .first()
        )
    if module_id:
        selected_module = (
            ModuleVersion.objects.select_related("module", "assessment_context")
            .prefetch_related("primitives__primitive", "decision_tables__decision_table")
            .filter(pk=module_id)
            .first()
        )
    if change_set_code:
        selected_change_set = ChangeSet.objects.select_related("assessment_context").filter(
            code=change_set_code
        ).first()

    module_readiness = (
        evaluate_module_version_readiness(module_version=selected_module)
        if selected_module
        else None
    )
    change_set_readiness = (
        build_change_set_activation_report(change_set=selected_change_set)
        if selected_change_set
        else None
    )

    step_state = {
        "rule_ready": bool(selected_rule and selected_rule.status in {StatusChoices.APPROVED, StatusChoices.ACTIVE}),
        "primitive_contains_rule": bool(
            selected_rule and selected_primitive and selected_primitive.rules.filter(pk=selected_rule.pk).exists()
        ),
        "primitive_ready": bool(
            selected_primitive and selected_primitive.status in {StatusChoices.APPROVED, StatusChoices.ACTIVE}
        ),
        "decision_contains_primitive": bool(
            selected_primitive
            and selected_decision_table
            and selected_decision_table.input_primitives.filter(pk=selected_primitive.pk).exists()
        ),
        "decision_ready": bool(
            selected_decision_table
            and selected_decision_table.status in {StatusChoices.APPROVED, StatusChoices.ACTIVE}
        ),
        "module_contains_decision": bool(
            selected_decision_table
            and selected_module
            and selected_module.decision_tables.filter(pk=selected_decision_table.pk).exists()
        ),
        "module_contains_primitive": bool(
            selected_primitive
            and selected_module
            and selected_module.primitives.filter(pk=selected_primitive.pk).exists()
        ),
        "module_ready": bool(selected_module and module_readiness and module_readiness.is_ready),
        "change_set_contains_module": bool(
            selected_module
            and selected_change_set
            and selected_change_set.module_versions.filter(pk=selected_module.pk).exists()
        ),
        "change_set_ready": bool(selected_change_set and change_set_readiness and change_set_readiness.is_ready),
        "change_set_active": bool(selected_change_set and selected_change_set.status == StatusChoices.ACTIVE),
    }

    return {
        "selection": {
            "rule": selected_rule,
            "primitive": selected_primitive,
            "decision_table": selected_decision_table,
            "module": selected_module,
            "change_set": selected_change_set,
        },
        "selection_redirect": _promotion_redirect(
            rule_id=selected_rule.id if selected_rule else None,
            primitive_id=selected_primitive.id if selected_primitive else None,
            decision_table_id=selected_decision_table.id if selected_decision_table else None,
            module_id=selected_module.id if selected_module else None,
            change_set_code=selected_change_set.code if selected_change_set else None,
        ),
        "rule_version_options": RuleVersion.objects.select_related("rule").order_by("rule__rule_id", "-id"),
        "primitive_version_options": PrimitiveVersion.objects.select_related("primitive").order_by(
            "primitive__code",
            "-id",
        ),
        "decision_table_version_options": DecisionTableVersion.objects.select_related(
            "decision_table"
        ).order_by("decision_table__code", "-id"),
        "module_version_options": ModuleVersion.objects.select_related("module", "assessment_context").order_by(
            "module__code",
            "-id",
        ),
        "change_set_options": ChangeSet.objects.select_related("assessment_context").order_by("-created_at"),
        "module_readiness": module_readiness,
        "change_set_readiness": change_set_readiness,
        "step_state": step_state,
    }


class WorkflowDashboardView(View):
    template_name = "workflow/dashboard.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, _build_dashboard_context(request))


class PromotionGuideView(View):
    template_name = "workflow/promotion_guide.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, _build_promotion_context(request))


class RuleVersionDetailView(View):
    template_name = "workflow/rule_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        rule_version = RuleVersion.objects.select_related("rule").get(pk=pk)
        return render(
            request,
            self.template_name,
            {
                "artifact": rule_version,
                "assessment_contexts": AssessmentContext.objects.order_by("-effective_from"),
                "rule_version_options": RuleVersion.objects.select_related("rule").order_by("rule__rule_id", "-id"),
                "structured_logic_pretty": json.dumps(rule_version.structured_logic, indent=2),
                "trigger_pretty": json.dumps(rule_version.trigger, indent=2),
                "consequence_pretty": json.dumps(rule_version.consequence, indent=2),
                "metadata_pretty": json.dumps(rule_version.metadata, indent=2),
            },
        )


class PrimitiveVersionDetailView(View):
    template_name = "workflow/primitive_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        primitive_version = (
            PrimitiveVersion.objects.select_related("primitive")
            .prefetch_related("rules__rule")
            .get(pk=pk)
        )
        return render(
            request,
            self.template_name,
            {
                "artifact": primitive_version,
                "rule_version_options": RuleVersion.objects.select_related("rule").order_by("rule__rule_id", "-id"),
                "input_schema_pretty": json.dumps(primitive_version.input_schema, indent=2),
                "output_schema_pretty": json.dumps(primitive_version.output_schema, indent=2),
                "completeness_pretty": json.dumps(primitive_version.completeness_report, indent=2),
            },
        )


class DecisionTableVersionDetailView(View):
    template_name = "workflow/decision_table_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        decision_table_version = (
            DecisionTableVersion.objects.select_related("decision_table")
            .prefetch_related("input_primitives__primitive")
            .get(pk=pk)
        )
        return render(
            request,
            self.template_name,
            {
                "artifact": decision_table_version,
                "primitive_version_options": PrimitiveVersion.objects.select_related("primitive").order_by(
                    "primitive__code",
                    "-id",
                ),
                "input_columns_pretty": json.dumps(decision_table_version.input_columns, indent=2),
                "output_columns_pretty": json.dumps(decision_table_version.output_columns, indent=2),
                "rows_pretty": json.dumps(decision_table_version.rows, indent=2),
                "completeness_pretty": json.dumps(
                    decision_table_version.completeness_report,
                    indent=2,
                ),
            },
        )


class ModuleVersionDetailView(View):
    template_name = "workflow/module_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        module_version = (
            ModuleVersion.objects.select_related("module", "assessment_context")
            .prefetch_related("primitives__primitive", "decision_tables__decision_table")
            .get(pk=pk)
        )
        readiness = evaluate_module_version_readiness(module_version=module_version)
        return render(
            request,
            self.template_name,
            {
                "artifact": module_version,
                "assessment_contexts": AssessmentContext.objects.order_by("-effective_from"),
                "primitive_version_options": PrimitiveVersion.objects.select_related("primitive").order_by(
                    "primitive__code",
                    "-id",
                ),
                "decision_table_version_options": DecisionTableVersion.objects.select_related(
                    "decision_table"
                ).order_by("decision_table__code", "-id"),
                "contract_provides_pretty": json.dumps(module_version.contract_provides, indent=2),
                "contract_consumes_pretty": json.dumps(module_version.contract_consumes, indent=2),
                "fallback_pretty": json.dumps(module_version.fallback_behaviour, indent=2),
                "readiness": readiness,
            },
        )


class WorkflowActionView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action")
        handlers = {
            "create_rule_draft": self._create_rule_draft,
            "clone_rule_to_new_definition": self._clone_rule_to_new_definition,
            "supersede_rule": self._supersede_rule,
            "update_rule_draft": self._update_rule_draft,
            "create_primitive_draft": self._create_primitive_draft,
            "clone_primitive_to_new_definition": self._clone_primitive_to_new_definition,
            "supersede_primitive": self._supersede_primitive,
            "update_primitive_draft": self._update_primitive_draft,
            "create_decision_table_draft": self._create_decision_table_draft,
            "clone_decision_table_to_new_definition": self._clone_decision_table_to_new_definition,
            "supersede_decision_table": self._supersede_decision_table,
            "update_decision_table_draft": self._update_decision_table_draft,
            "create_module_draft": self._create_module_draft,
            "supersede_module": self._supersede_module,
            "update_module_draft": self._update_module_draft,
            "bundle_change_set": self._bundle_change_set,
            "submit_rule_review": self._submit_rule_review,
            "approve_rule": self._approve_rule,
            "submit_primitive_review": self._submit_primitive_review,
            "approve_primitive": self._approve_primitive,
            "submit_decision_table_review": self._submit_decision_table_review,
            "approve_decision_table": self._approve_decision_table,
            "guided_attach_rule_to_primitive": self._guided_attach_rule_to_primitive,
            "guided_attach_primitive_to_decision_table": self._guided_attach_primitive_to_decision_table,
            "guided_attach_artifacts_to_module": self._guided_attach_artifacts_to_module,
            "guided_bundle_change_set": self._guided_bundle_change_set,
            "submit_module_review": self._submit_module_review,
            "approve_module": self._approve_module,
            "submit_change_set_review": self._submit_change_set_review,
            "approve_change_set": self._approve_change_set,
            "activate_change_set": self._activate_change_set,
            "evaluate_itr_form": self._evaluate_itr_form,
            "evaluate_itr_regime": self._evaluate_itr_regime,
            "evaluate_itr_tax": self._evaluate_itr_tax,
            "evaluate_corporate_concept": self._evaluate_corporate_concept,
            "evaluate_governance_cross_module": self._evaluate_governance_cross_module,
        }

        handler = handlers.get(action)
        if not handler:
            messages.error(request, "Unknown workflow action.")
            return redirect("workflow-dashboard")

        try:
            redirect_target = handler(request) or request.POST.get("redirect_to") or "workflow-dashboard"
        except Exception as exc:
            messages.error(request, str(exc))
            redirect_target = request.POST.get("redirect_to") or "workflow-dashboard"
        return redirect(redirect_target)

    def _create_rule_draft(self, request: HttpRequest) -> None:
        result = create_rule_draft(
            rule_id=request.POST["rule_id"].strip(),
            name=request.POST["rule_name"].strip(),
            scope=request.POST["scope"].strip(),
            description=request.POST.get("rule_description", "").strip(),
            version=request.POST["version"].strip(),
            source_reference=request.POST["source_reference"].strip(),
            natural_language=request.POST["natural_language"].strip(),
            structured_logic=_json_input(request.POST.get("structured_logic", ""), {}),
            mode=request.POST["mode"].strip(),
            trigger=_json_input(request.POST.get("trigger", ""), {}),
            consequence=_json_input(request.POST.get("consequence", ""), {}),
            severity=request.POST["severity"].strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
        )
        messages.success(request, f"Created {result.object_label}.")
        _store_latest_result(request, title="Rule Draft Created", payload=result.__dict__)

    def _clone_rule_to_new_definition(self, request: HttpRequest) -> None:
        result = clone_rule_version_to_new_definition(
            source_rule_version_id=int(request.POST["source_rule_version_id"]),
            new_rule_id=request.POST["new_rule_id"].strip(),
            name=request.POST["rule_name"].strip(),
            scope=request.POST["scope"].strip(),
            description=request.POST.get("rule_description", "").strip(),
            version=request.POST["version"].strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
        )
        messages.success(request, f"Cloned into {result.object_label}.")
        _store_latest_result(request, title="Rule Cloned", payload=result.__dict__)

    def _supersede_rule(self, request: HttpRequest) -> None:
        result = supersede_rule_version(
            source_rule_version_id=int(request.POST["source_rule_version_id"])
        )
        messages.success(request, f"Created draft rule version {result.new_rule_version}.")
        _store_latest_result(request, title="Rule Superseded", payload=result.__dict__)

    def _update_rule_draft(self, request: HttpRequest) -> None:
        result = update_rule_draft(
            rule_version_id=int(request.POST["rule_version_id"]),
            version=request.POST["version"].strip(),
            source_reference=request.POST["source_reference"].strip(),
            natural_language=request.POST["natural_language"].strip(),
            structured_logic=_json_input(request.POST.get("structured_logic", ""), {}),
            mode=request.POST["mode"].strip(),
            trigger=_json_input(request.POST.get("trigger", ""), {}),
            consequence=_json_input(request.POST.get("consequence", ""), {}),
            severity=request.POST["severity"].strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
        )
        messages.success(request, f"Updated {result.object_label}.")
        _store_latest_result(request, title="Rule Draft Updated", payload=result.__dict__)

    def _create_primitive_draft(self, request: HttpRequest) -> None:
        result = create_primitive_draft(
            code=request.POST["primitive_code"].strip(),
            name=request.POST["primitive_name"].strip(),
            module_scope=request.POST["module_scope"].strip(),
            question=request.POST["question"].strip(),
            description=request.POST.get("primitive_description", "").strip(),
            version=request.POST["version"].strip(),
            input_schema=_json_input(request.POST.get("input_schema", ""), {}),
            output_schema=_json_input(request.POST.get("output_schema", ""), {}),
            rule_version_ids=_int_list(request.POST.getlist("rule_version_ids")),
        )
        messages.success(request, f"Created {result.object_label}.")
        _store_latest_result(request, title="Primitive Draft Created", payload=result.__dict__)

    def _clone_primitive_to_new_definition(self, request: HttpRequest) -> None:
        result = clone_primitive_version_to_new_definition(
            source_primitive_version_id=int(request.POST["source_primitive_version_id"]),
            new_code=request.POST["primitive_code"].strip(),
            name=request.POST["primitive_name"].strip(),
            module_scope=request.POST["module_scope"].strip(),
            question=request.POST["question"].strip(),
            description=request.POST.get("primitive_description", "").strip(),
            version=request.POST["version"].strip(),
        )
        messages.success(request, f"Cloned into {result.object_label}.")
        _store_latest_result(request, title="Primitive Cloned", payload=result.__dict__)

    def _supersede_primitive(self, request: HttpRequest) -> None:
        replacement_rule_ids = _int_list(request.POST.getlist("replacement_rule_version_ids"))
        result = supersede_primitive_version(
            source_primitive_version_id=int(request.POST["source_primitive_version_id"]),
            replacement_rule_version_ids=replacement_rule_ids,
        )
        messages.success(request, f"Created draft primitive version {result.new_primitive_version}.")
        _store_latest_result(request, title="Primitive Superseded", payload=result.__dict__)

    def _update_primitive_draft(self, request: HttpRequest) -> None:
        result = update_primitive_draft(
            primitive_version_id=int(request.POST["primitive_version_id"]),
            version=request.POST["version"].strip(),
            input_schema=_json_input(request.POST.get("input_schema", ""), {}),
            output_schema=_json_input(request.POST.get("output_schema", ""), {}),
            rule_version_ids=_int_list(request.POST.getlist("rule_version_ids")),
        )
        messages.success(request, f"Updated {result.object_label}.")
        _store_latest_result(request, title="Primitive Draft Updated", payload=result.__dict__)

    def _create_decision_table_draft(self, request: HttpRequest) -> None:
        result = create_decision_table_draft(
            code=request.POST["decision_table_code"].strip(),
            name=request.POST["decision_table_name"].strip(),
            scope=request.POST["scope"].strip(),
            description=request.POST.get("decision_table_description", "").strip(),
            version=request.POST["version"].strip(),
            input_primitive_ids=_int_list(request.POST.getlist("input_primitive_ids")),
            input_columns=_json_input(request.POST.get("input_columns", ""), []),
            output_columns=_json_input(request.POST.get("output_columns", ""), []),
            rows=_json_input(request.POST.get("rows", ""), []),
        )
        messages.success(request, f"Created {result.object_label}.")
        _store_latest_result(request, title="Decision Table Draft Created", payload=result.__dict__)

    def _clone_decision_table_to_new_definition(self, request: HttpRequest) -> None:
        result = clone_decision_table_version_to_new_definition(
            source_decision_table_version_id=int(request.POST["source_decision_table_version_id"]),
            new_code=request.POST["decision_table_code"].strip(),
            name=request.POST["decision_table_name"].strip(),
            scope=request.POST["scope"].strip(),
            description=request.POST.get("decision_table_description", "").strip(),
            version=request.POST["version"].strip(),
        )
        messages.success(request, f"Cloned into {result.object_label}.")
        _store_latest_result(request, title="Decision Table Cloned", payload=result.__dict__)

    def _supersede_decision_table(self, request: HttpRequest) -> None:
        result = supersede_decision_table_version(
            source_decision_table_version_id=int(request.POST["source_decision_table_version_id"]),
            replacement_input_primitive_ids=_int_list(request.POST.getlist("replacement_input_primitive_ids")),
        )
        messages.success(request, f"Created draft decision table version {result.new_decision_table_version}.")
        _store_latest_result(request, title="Decision Table Superseded", payload=result.__dict__)

    def _update_decision_table_draft(self, request: HttpRequest) -> None:
        result = update_decision_table_draft(
            decision_table_version_id=int(request.POST["decision_table_version_id"]),
            version=request.POST["version"].strip(),
            input_primitive_ids=_int_list(request.POST.getlist("input_primitive_ids")),
            input_columns=_json_input(request.POST.get("input_columns", ""), []),
            output_columns=_json_input(request.POST.get("output_columns", ""), []),
            rows=_json_input(request.POST.get("rows", ""), []),
        )
        messages.success(request, f"Updated {result.object_label}.")
        _store_latest_result(request, title="Decision Table Draft Updated", payload=result.__dict__)

    def _create_module_draft(self, request: HttpRequest) -> None:
        result = create_module_draft(
            code=request.POST["module_code"].strip(),
            name=request.POST["module_name"].strip(),
            scope=request.POST["scope"].strip(),
            description=request.POST.get("module_description", "").strip(),
            version=request.POST["version"].strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
            primitive_version_ids=_int_list(request.POST.getlist("primitive_version_ids")),
            decision_table_version_ids=_int_list(request.POST.getlist("decision_table_version_ids")),
            contract_provides=_json_input(request.POST.get("contract_provides", ""), []),
            contract_consumes=_json_input(request.POST.get("contract_consumes", ""), []),
            fallback_behaviour=_json_input(request.POST.get("fallback_behaviour", ""), {}),
        )
        messages.success(request, f"Created {result.object_label}.")
        _store_latest_result(request, title="Module Draft Created", payload=result.__dict__)

    def _supersede_module(self, request: HttpRequest) -> None:
        result = supersede_module_version(
            source_module_version_id=int(request.POST["source_module_version_id"]),
            replacement_primitive_version_ids=_int_list(request.POST.getlist("replacement_primitive_version_ids")),
            replacement_decision_table_version_ids=_int_list(
                request.POST.getlist("replacement_decision_table_version_ids")
            ),
        )
        messages.success(request, f"Created draft module version {result.new_module_version}.")
        _store_latest_result(request, title="Module Superseded", payload=result.__dict__)

    def _update_module_draft(self, request: HttpRequest) -> None:
        result = update_module_draft(
            module_version_id=int(request.POST["module_version_id"]),
            version=request.POST["version"].strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
            primitive_version_ids=_int_list(request.POST.getlist("primitive_version_ids")),
            decision_table_version_ids=_int_list(request.POST.getlist("decision_table_version_ids")),
            contract_provides=_json_input(request.POST.get("contract_provides", ""), []),
            contract_consumes=_json_input(request.POST.get("contract_consumes", ""), []),
            fallback_behaviour=_json_input(request.POST.get("fallback_behaviour", ""), {}),
        )
        messages.success(request, f"Updated {result.object_label}.")
        _store_latest_result(request, title="Module Draft Updated", payload=result.__dict__)

    def _bundle_change_set(self, request: HttpRequest) -> None:
        result = create_or_update_draft_change_set_bundle(
            code=request.POST["change_set_code"].strip(),
            name=request.POST["change_set_name"].strip(),
            description=request.POST.get("change_set_description", "").strip(),
            assessment_context_code=request.POST["assessment_context"].strip(),
            rule_version_ids=[int(value) for value in request.POST.getlist("rule_version_ids") if value],
            primitive_version_ids=[
                int(value) for value in request.POST.getlist("primitive_version_ids") if value
            ],
            decision_table_version_ids=[
                int(value) for value in request.POST.getlist("decision_table_version_ids") if value
            ],
            module_version_ids=[int(value) for value in request.POST.getlist("module_version_ids") if value],
        )
        verb = "Created" if result.created else "Updated"
        messages.success(request, f"{verb} draft change set {result.code}.")
        _store_latest_result(request, title="Draft Change Set Bundled", payload=result.__dict__)

    def _submit_rule_review(self, request: HttpRequest) -> None:
        result = submit_rule_version_for_review(rule_version_id=int(request.POST["rule_version_id"]))
        messages.success(request, f"{result.object_label} moved to {result.to_status}.")
        _store_latest_result(request, title="Rule Submitted For Review", payload=result.__dict__)

    def _approve_rule(self, request: HttpRequest) -> None:
        result = approve_rule_version(
            rule_version_id=int(request.POST["rule_version_id"]),
            approved_by=request.POST.get("approved_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.object_label} approved.")
        _store_latest_result(request, title="Rule Approved", payload=result.__dict__)

    def _submit_primitive_review(self, request: HttpRequest) -> None:
        result = submit_primitive_version_for_review(
            primitive_version_id=int(request.POST["primitive_version_id"])
        )
        messages.success(request, f"{result.object_label} moved to {result.to_status}.")
        _store_latest_result(request, title="Primitive Submitted For Review", payload=result.__dict__)

    def _approve_primitive(self, request: HttpRequest) -> None:
        result = approve_primitive_version(
            primitive_version_id=int(request.POST["primitive_version_id"]),
            approved_by=request.POST.get("approved_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.object_label} approved.")
        _store_latest_result(request, title="Primitive Approved", payload=result.__dict__)

    def _submit_decision_table_review(self, request: HttpRequest) -> None:
        result = submit_decision_table_version_for_review(
            decision_table_version_id=int(request.POST["decision_table_version_id"])
        )
        messages.success(request, f"{result.object_label} moved to {result.to_status}.")
        _store_latest_result(request, title="Decision Table Submitted For Review", payload=result.__dict__)

    def _approve_decision_table(self, request: HttpRequest) -> None:
        result = approve_decision_table_version(
            decision_table_version_id=int(request.POST["decision_table_version_id"]),
            approved_by=request.POST.get("approved_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.object_label} approved.")
        _store_latest_result(request, title="Decision Table Approved", payload=result.__dict__)

    def _guided_attach_rule_to_primitive(self, request: HttpRequest) -> None:
        result = attach_rule_to_primitive_draft(
            primitive_version_id=int(request.POST["primitive_version_id"]),
            rule_version_id=int(request.POST["rule_version_id"]),
        )
        messages.success(request, f"Attached rule into {result.object_label}.")
        _store_latest_result(request, title="Rule Attached To Primitive", payload=result.__dict__)

    def _guided_attach_primitive_to_decision_table(self, request: HttpRequest) -> None:
        result = attach_primitive_to_decision_table_draft(
            decision_table_version_id=int(request.POST["decision_table_version_id"]),
            primitive_version_id=int(request.POST["primitive_version_id"]),
        )
        messages.success(request, f"Attached primitive into {result.object_label}.")
        _store_latest_result(request, title="Primitive Attached To Decision Table", payload=result.__dict__)

    def _guided_attach_artifacts_to_module(self, request: HttpRequest) -> None:
        result = attach_artifacts_to_module_draft(
            module_version_id=int(request.POST["module_version_id"]),
            primitive_version_ids=_int_list(request.POST.getlist("primitive_version_ids")),
            decision_table_version_ids=_int_list(request.POST.getlist("decision_table_version_ids")),
        )
        messages.success(request, f"Attached artifacts into {result.object_label}.")
        _store_latest_result(request, title="Artifacts Attached To Module", payload=result.__dict__)

    def _guided_bundle_change_set(self, request: HttpRequest) -> None:
        code = request.POST["change_set_code"].strip()
        assessment_context = request.POST["assessment_context"].strip()
        result = create_or_update_draft_change_set_bundle(
            code=code,
            name=request.POST.get("change_set_name", code).strip() or code,
            description=request.POST.get("change_set_description", "").strip(),
            assessment_context_code=assessment_context,
            rule_version_ids=_int_list(request.POST.getlist("rule_version_ids")),
            primitive_version_ids=_int_list(request.POST.getlist("primitive_version_ids")),
            decision_table_version_ids=_int_list(request.POST.getlist("decision_table_version_ids")),
            module_version_ids=_int_list(request.POST.getlist("module_version_ids")),
        )
        messages.success(request, f"Bundled guided promotion into {result.code}.")
        _store_latest_result(request, title="Promotion Change Set Bundled", payload=result.__dict__)

    def _submit_module_review(self, request: HttpRequest) -> None:
        result = submit_module_version_for_review(module_version_id=int(request.POST["module_version_id"]))
        messages.success(request, f"{result.object_label} moved to {result.to_status}.")
        _store_latest_result(request, title="Module Submitted For Review", payload=result.__dict__)

    def _approve_module(self, request: HttpRequest) -> None:
        result = approve_module_version(
            module_version_id=int(request.POST["module_version_id"]),
            approved_by=request.POST.get("approved_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.object_label} approved.")
        _store_latest_result(request, title="Module Approved", payload=result.__dict__)

    def _submit_change_set_review(self, request: HttpRequest) -> None:
        result = submit_change_set_for_review(change_set_code=request.POST["change_set_code"])
        messages.success(request, f"{result.object_label} moved to {result.to_status}.")
        _store_latest_result(request, title="Change Set Submitted For Review", payload=result.__dict__)

    def _approve_change_set(self, request: HttpRequest) -> None:
        result = approve_change_set(
            change_set_code=request.POST["change_set_code"],
            approved_by=request.POST.get("approved_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.object_label} approved.")
        _store_latest_result(request, title="Change Set Approved", payload=result.__dict__)

    def _activate_change_set(self, request: HttpRequest) -> None:
        result = activate_change_set(
            change_set_code=request.POST["change_set_code"],
            activated_by=request.POST.get("activated_by", "system").strip() or "system",
        )
        messages.success(request, f"{result.change_set_code} activated.")
        _store_latest_result(request, title="Change Set Activated", payload=result.__dict__)

    def _evaluate_itr_form(self, request: HttpRequest) -> None:
        serializer = TaxpayerProfileSerializer(
            data={
                "assessment_context": request.POST.get("assessment_context", "AY_2026_27"),
                "residential_status": request.POST.get("residential_status"),
                "total_income": request.POST.get("total_income"),
                "category": request.POST.get("category"),
                "is_director_in_company": _bool_from_post(request, "is_director_in_company"),
                "has_unlisted_equity_investment": _bool_from_post(
                    request,
                    "has_unlisted_equity_investment",
                ),
                "has_foreign_assets": _bool_from_post(request, "has_foreign_assets"),
                "has_foreign_account_signing_authority": _bool_from_post(
                    request,
                    "has_foreign_account_signing_authority",
                ),
                "income_sources": request.POST.getlist("income_sources"),
                "has_capital_gains": _bool_from_post(request, "has_capital_gains"),
                "capital_gain_type": request.POST.get("capital_gain_type", ""),
                "ltcg_112a_amount": request.POST.get("ltcg_112a_amount") or 0,
                "has_carried_forward_capital_loss": _bool_from_post(
                    request,
                    "has_carried_forward_capital_loss",
                ),
                "house_property_count": request.POST.get("house_property_count"),
                "has_brought_forward_house_property_loss": _bool_from_post(
                    request,
                    "has_brought_forward_house_property_loss",
                ),
                "tds_deducted_under_194N": _bool_from_post(request, "tds_deducted_under_194N"),
                "has_esop_tax_deferred": _bool_from_post(request, "has_esop_tax_deferred"),
                "has_business_profession_income": _bool_from_post(
                    request,
                    "has_business_profession_income",
                ),
            }
        )
        serializer.is_valid(raise_exception=True)
        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr1_form_eligibility(payload, assessment_context)
        ITREvaluation.objects.create(
            profile=payload,
            selected_form=result["selected_form"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = ModuleVersion.objects.get(pk=result["module_version_id"])
        audit_log = create_evaluation_log(
            assessment_context=assessment_context_obj,
            module_version=module_version_obj,
            taxpayer_reference=payload,
            input_payload=payload,
            primitive_trace=result["primitive_versions"],
            decision_table_trace={
                "decision_table_version": result["decision_table_version"],
                "decision_table_inputs": result["decision_table_inputs"],
                "decision_table_match": result["decision_table_match"],
            },
            outcome_payload={
                "selected_form": result["selected_form"],
                "suggested_forms": result["suggested_forms"],
            },
            rule_trace=result["decision_trace"],
        )
        result["audit_event_id"] = audit_log.event_id
        result["audit_entry_hash"] = audit_log.entry_hash
        messages.success(request, f"Form evaluation completed with result {result['selected_form']}.")
        _store_latest_result(request, title="ITR Form Evaluation", payload=result)

    def _evaluate_itr_regime(self, request: HttpRequest) -> None:
        serializer = RegimeSelectionSerializer(
            data={
                "assessment_context": request.POST.get("assessment_context", "AY_2026_27"),
                "has_business_profession_income": _bool_from_post(
                    request,
                    "has_business_profession_income",
                ),
                "regime_selection": request.POST.get("regime_selection", "NOT_SPECIFIED"),
                "filing_date": request.POST.get("filing_date"),
                "due_date_139_1": request.POST.get("due_date_139_1"),
            }
        )
        serializer.is_valid(raise_exception=True)
        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr_regime_selection(payload, assessment_context)
        ITRRegimeEvaluation.objects.create(
            profile=payload,
            applicable_regime=result["applicable_regime"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = ModuleVersion.objects.get(pk=result["module_version_id"])
        audit_log = create_evaluation_log(
            assessment_context=assessment_context_obj,
            module_version=module_version_obj,
            taxpayer_reference=payload,
            input_payload=payload,
            primitive_trace=result["primitive_versions"],
            decision_table_trace={
                "decision_table_version": result["decision_table_version"],
                "decision_table_inputs": result["decision_table_inputs"],
                "decision_table_match": result["decision_table_match"],
            },
            outcome_payload={
                "applicable_regime": result["applicable_regime"],
                "alerts": result["alerts"],
            },
            rule_trace=result["decision_trace"],
        )
        result["audit_event_id"] = audit_log.event_id
        result["audit_entry_hash"] = audit_log.entry_hash
        messages.success(request, f"Regime evaluation completed with {result['applicable_regime']}.")
        _store_latest_result(request, title="ITR Regime Evaluation", payload=result)

    def _evaluate_itr_tax(self, request: HttpRequest) -> None:
        serializer = TaxComputationSerializer(
            data={
                "assessment_context": request.POST.get("assessment_context", "AY_2026_27"),
                "applicable_regime": request.POST.get("applicable_regime"),
                "taxable_income": request.POST.get("taxable_income"),
                "special_rate_income": request.POST.get("special_rate_income") or 0,
            }
        )
        serializer.is_valid(raise_exception=True)
        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr_tax_computation(payload, assessment_context)
        ITRTaxComputationEvaluation.objects.create(
            profile=payload,
            applicable_regime=result["applicable_regime"],
            total_liability=result["total_liability"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = ModuleVersion.objects.get(pk=result["module_version_id"])
        audit_log = create_evaluation_log(
            assessment_context=assessment_context_obj,
            module_version=module_version_obj,
            taxpayer_reference=payload,
            input_payload=payload,
            primitive_trace=result["primitive_versions"],
            decision_table_trace={},
            outcome_payload={
                "applicable_regime": result["applicable_regime"],
                "total_liability": result["total_liability"],
                "alerts": result["alerts"],
            },
            rule_trace=result["decision_trace"],
        )
        result["audit_event_id"] = audit_log.event_id
        result["audit_entry_hash"] = audit_log.entry_hash
        messages.success(
            request,
            f"Tax computation completed with liability {result['total_liability']}.",
        )
        _store_latest_result(request, title="ITR Tax Computation", payload=result)

    def _evaluate_corporate_concept(self, request: HttpRequest) -> None:
        serializer = CorporateTaxProfileSerializer(
            data={
                "assessment_context": request.POST.get("assessment_context", "TY_2026_27"),
                "registration_country": request.POST.get("registration_country"),
                "registration_act": request.POST.get("registration_act"),
                "management_control_in_india": _bool_from_post(request, "management_control_in_india"),
                "office_fixed_place_in_india": _bool_from_post(request, "office_fixed_place_in_india"),
                "agents_dependent_in_india": _bool_from_post(request, "agents_dependent_in_india"),
                "construction_project_duration_days": request.POST.get("construction_project_duration_days") or 0,
                "previous_year_turnover": request.POST.get("previous_year_turnover") or 0,
                "incorporation_date": request.POST.get("incorporation_date"),
                "business_activity": request.POST.get("business_activity"),
                "regime_option": request.POST.get("regime_option", "DEFAULT"),
            }
        )
        serializer.is_valid(raise_exception=True)
        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "TY_2026_27")
        result = evaluate_corporate_tax_concept(payload, assessment_context)
        CorporateTaxEvaluation.objects.create(
            profile=payload,
            entity_type=result["entity_type"],
            regime_track=result["regime_track"],
            filing_route=result["filing_route"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = ModuleVersion.objects.get(pk=result["module_version_id"])
        audit_log = create_evaluation_log(
            assessment_context=assessment_context_obj,
            module_version=module_version_obj,
            taxpayer_reference=payload,
            input_payload=payload,
            primitive_trace=result["primitive_versions"],
            decision_table_trace=result["decision_table_matches"],
            outcome_payload={
                "entity_type": result["entity_type"],
                "pe_status": result["pe_status"],
                "turnover_category": result["turnover_category"],
                "incorporation_date_status": result["incorporation_date_status"],
                "regime_track": result["regime_track"],
                "filing_route": result["filing_route"],
                "compliance_alerts": result["compliance_alerts"],
            },
            rule_trace=result["decision_trace"],
        )
        result["audit_event_id"] = audit_log.event_id
        result["audit_entry_hash"] = audit_log.entry_hash
        messages.success(
            request,
            f"Corporate evaluation completed with route {result['filing_route']}.",
        )
        _store_latest_result(request, title="Corporate Tax Concept Evaluation", payload=result)

    def _evaluate_governance_cross_module(self, request: HttpRequest) -> None:
        itr_serializer = TaxpayerProfileSerializer(
            data={
                "assessment_context": request.POST.get("g_itr_assessment_context", "AY_2026_27"),
                "residential_status": request.POST.get("g_itr_residential_status", "RESIDENT_ORDINARY"),
                "total_income": request.POST.get("g_itr_total_income") or 1200000,
                "category": "INDIVIDUAL",
                "is_director_in_company": _bool_from_post(request, "g_itr_is_director_in_company"),
                "has_unlisted_equity_investment": False,
                "has_foreign_assets": _bool_from_post(request, "g_itr_has_foreign_assets"),
                "has_foreign_account_signing_authority": False,
                "income_sources": ["SALARY"],
                "has_capital_gains": False,
                "capital_gain_type": "",
                "ltcg_112a_amount": 0,
                "has_carried_forward_capital_loss": False,
                "house_property_count": 1,
                "has_brought_forward_house_property_loss": False,
                "tds_deducted_under_194N": False,
                "has_esop_tax_deferred": False,
                "has_business_profession_income": False,
            }
        )
        itr_serializer.is_valid(raise_exception=True)
        itr_payload = _json_safe(dict(itr_serializer.validated_data))
        itr_assessment_context = itr_payload.pop("assessment_context", "AY_2026_27")

        corporate_serializer = CorporateTaxProfileSerializer(
            data={
                "assessment_context": request.POST.get("g_corp_assessment_context", "TY_2026_27"),
                "registration_country": request.POST.get("g_corp_registration_country", "INDIA"),
                "registration_act": request.POST.get("g_corp_registration_act", "COMPANIES_ACT"),
                "management_control_in_india": _bool_from_post(request, "g_corp_management_control_in_india"),
                "office_fixed_place_in_india": _bool_from_post(request, "g_corp_office_fixed_place_in_india"),
                "agents_dependent_in_india": False,
                "construction_project_duration_days": request.POST.get("g_corp_construction_project_duration_days") or 0,
                "previous_year_turnover": request.POST.get("g_corp_previous_year_turnover") or 3500000000,
                "incorporation_date": request.POST.get("g_corp_incorporation_date", "2020-01-15"),
                "business_activity": request.POST.get("g_corp_business_activity", "MANUFACTURING"),
                "regime_option": request.POST.get("g_corp_regime_option", "DEFAULT"),
            }
        )
        corporate_serializer.is_valid(raise_exception=True)
        corporate_payload = _json_safe(dict(corporate_serializer.validated_data))
        corporate_assessment_context = corporate_payload.pop("assessment_context", "TY_2026_27")

        result = evaluate_cross_module_governance(
            itr_profile=itr_payload,
            corporate_profile=corporate_payload,
            itr_assessment_context=itr_assessment_context,
            corporate_assessment_context=corporate_assessment_context,
            governance_assessment_context=request.POST.get("g_governance_assessment_context", "GOV_2026_27"),
        )
        record = GovernanceEvaluation.objects.create(
            assessment_context=AssessmentContext.objects.get(pk=result["assessment_context_id"]),
            input_payload=result["input_payload"],
            itr_summary=result["itr_result"],
            corporate_summary=result["corporate_result"],
            governance_status=result["governance_status"],
            governance_actions=result["governance_actions"],
            governance_summary=result["governance_summary"],
            rule_trace=result["rule_trace"],
        )
        module_version_obj = ModuleVersion.objects.get(pk=result["module_version_id"])
        audit_log = create_evaluation_log(
            assessment_context=record.assessment_context,
            module_version=module_version_obj,
            taxpayer_reference=result["input_payload"],
            input_payload=result["input_payload"],
            primitive_trace=[],
            decision_table_trace={},
            outcome_payload={
                "governance_status": result["governance_status"],
                "governance_actions": result["governance_actions"],
                "governance_summary": result["governance_summary"],
                "depends_on_modules": result["depends_on_modules"],
            },
            rule_trace=result["rule_trace"],
        )
        result["audit_event_id"] = audit_log.event_id
        result["audit_entry_hash"] = audit_log.entry_hash
        result["evaluation_id"] = record.pk
        messages.success(
            request,
            f"Governance evaluation completed with status {result['governance_status']}.",
        )
        _store_latest_result(request, title="Cross-Module Governance Evaluation", payload=result)
