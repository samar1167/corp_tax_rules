from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_evaluation_log
from core_rules.models import AssessmentContext, ModuleVersion

from .models import ITREvaluation, ITRRegimeEvaluation
from .serializers import (
    ITREvaluationSerializer,
    ITRRegimeEvaluationSerializer,
    ITRTaxComputationEvaluationSerializer,
    RegimeSelectionSerializer,
    TaxComputationSerializer,
    TaxpayerProfileSerializer,
)
from .services import (
    evaluate_itr1_form_eligibility,
    evaluate_itr_regime_selection,
    evaluate_itr_tax_computation,
)
from .models import ITRTaxComputationEvaluation


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class ITRHealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class ITRFormEligibilityView(APIView):
    def post(self, request):
        serializer = TaxpayerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr1_form_eligibility(payload, assessment_context)
        record = ITREvaluation.objects.create(
            profile=payload,
            selected_form=result["selected_form"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = (
            ModuleVersion.objects.get(pk=result["module_version_id"])
            if result["module_version_id"]
            else None
        )
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
                "decision_table_version": result["decision_table_version"],
                "decision_table_match": result["decision_table_match"],
            },
            rule_trace=result["decision_trace"],
        )
        response = {
            "evaluation_id": record.pk,
            "audit_event_id": audit_log.event_id,
            "audit_entry_hash": audit_log.entry_hash,
            "assessment_context": result["assessment_context"],
            "module_version": result["module_version"],
            "primitive_versions": result["primitive_versions"],
            "decision_table_version": result["decision_table_version"],
            "decision_table_inputs": result["decision_table_inputs"],
            "decision_table_match": result["decision_table_match"],
            "selected_form": result["selected_form"],
            "suggested_forms": result["suggested_forms"],
            "decision_trace": result["decision_trace"],
        }
        return Response(response)


class ITRRecentEvaluationsView(APIView):
    def get(self, request):
        evaluations = ITREvaluation.objects.all()[:20]
        serializer = ITREvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)


class ITRRegimeSelectionView(APIView):
    def post(self, request):
        serializer = RegimeSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr_regime_selection(payload, assessment_context)
        record = ITRRegimeEvaluation.objects.create(
            profile=payload,
            applicable_regime=result["applicable_regime"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = (
            ModuleVersion.objects.get(pk=result["module_version_id"])
            if result["module_version_id"]
            else None
        )
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
                "decision_table_version": result["decision_table_version"],
                "decision_table_match": result["decision_table_match"],
            },
            rule_trace=result["decision_trace"],
        )
        return Response(
            {
                "evaluation_id": record.pk,
                "audit_event_id": audit_log.event_id,
                "audit_entry_hash": audit_log.entry_hash,
                "assessment_context": result["assessment_context"],
                "module_version": result["module_version"],
                "primitive_versions": result["primitive_versions"],
                "decision_table_version": result["decision_table_version"],
                "decision_table_inputs": result["decision_table_inputs"],
                "decision_table_match": result["decision_table_match"],
                "applicable_regime": result["applicable_regime"],
                "alerts": result["alerts"],
                "decision_trace": result["decision_trace"],
            }
        )


class ITRRecentRegimeEvaluationsView(APIView):
    def get(self, request):
        evaluations = ITRRegimeEvaluation.objects.all()[:20]
        serializer = ITRRegimeEvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)


class ITRTaxComputationView(APIView):
    def post(self, request):
        serializer = TaxComputationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "AY_2026_27")
        result = evaluate_itr_tax_computation(payload, assessment_context)
        record = ITRTaxComputationEvaluation.objects.create(
            profile=payload,
            applicable_regime=result["applicable_regime"],
            total_liability=result["total_liability"],
            decision_trace=result["decision_trace"],
        )
        assessment_context_obj = AssessmentContext.objects.get(pk=result["assessment_context_id"])
        module_version_obj = (
            ModuleVersion.objects.get(pk=result["module_version_id"])
            if result["module_version_id"]
            else None
        )
        audit_log = create_evaluation_log(
            assessment_context=assessment_context_obj,
            module_version=module_version_obj,
            taxpayer_reference=payload,
            input_payload=payload,
            primitive_trace=result["primitive_versions"],
            decision_table_trace={},
            outcome_payload={
                "applicable_regime": result["applicable_regime"],
                "base_tax": result["base_tax"],
                "rebate_87a": result["rebate_87a"],
                "cess": result["cess"],
                "total_liability": result["total_liability"],
                "alerts": result["alerts"],
            },
            rule_trace=result["decision_trace"],
        )
        return Response(
            {
                "evaluation_id": record.pk,
                "audit_event_id": audit_log.event_id,
                "audit_entry_hash": audit_log.entry_hash,
                "assessment_context": result["assessment_context"],
                "module_version": result["module_version"],
                "primitive_versions": result["primitive_versions"],
                "applicable_regime": result["applicable_regime"],
                "base_tax": result["base_tax"],
                "rebate_87a": result["rebate_87a"],
                "surcharge": result["surcharge"],
                "cess": result["cess"],
                "total_liability": result["total_liability"],
                "alerts": result["alerts"],
                "decision_trace": result["decision_trace"],
            }
        )


class ITRRecentTaxComputationEvaluationsView(APIView):
    def get(self, request):
        evaluations = ITRTaxComputationEvaluation.objects.all()[:20]
        serializer = ITRTaxComputationEvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)
