from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_evaluation_log
from core_rules.models import AssessmentContext, ModuleVersion

from .models import CorporateTaxEvaluation
from .serializers import CorporateTaxEvaluationSerializer, CorporateTaxProfileSerializer
from .services import evaluate_corporate_tax_concept


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class CorporateTaxHealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class CorporateTaxConceptEvaluationView(APIView):
    def post(self, request):
        serializer = CorporateTaxProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = _json_safe(dict(serializer.validated_data))
        assessment_context = payload.pop("assessment_context", "TY_2026_27")
        result = evaluate_corporate_tax_concept(payload, assessment_context)
        record = CorporateTaxEvaluation.objects.create(
            profile=payload,
            entity_type=result["entity_type"],
            regime_track=result["regime_track"],
            filing_route=result["filing_route"],
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
        return Response(
            {
                "evaluation_id": record.pk,
                "audit_event_id": audit_log.event_id,
                "audit_entry_hash": audit_log.entry_hash,
                **result,
            }
        )


class CorporateTaxRecentEvaluationsView(APIView):
    def get(self, request):
        evaluations = CorporateTaxEvaluation.objects.all()[:20]
        serializer = CorporateTaxEvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)
