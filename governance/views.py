from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_evaluation_log
from core_rules.models import AssessmentContext, ModuleVersion

from .models import GovernanceEvaluation
from .serializers import GovernanceCrossModuleSerializer, GovernanceEvaluationSerializer
from .services import evaluate_cross_module_governance


class GovernanceHealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class GovernanceCrossModuleEvaluationView(APIView):
    def post(self, request):
        serializer = GovernanceCrossModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = evaluate_cross_module_governance(**serializer.validated_data)
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
        module_version_obj = (
            ModuleVersion.objects.get(pk=result["module_version_id"])
            if result["module_version_id"]
            else None
        )
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
        return Response(
            {
                "evaluation_id": record.pk,
                "audit_event_id": audit_log.event_id,
                "audit_entry_hash": audit_log.entry_hash,
                **result,
            }
        )


class GovernanceRecentEvaluationsView(APIView):
    def get(self, request):
        evaluations = GovernanceEvaluation.objects.all()[:20]
        serializer = GovernanceEvaluationSerializer(evaluations, many=True)
        return Response(serializer.data)
