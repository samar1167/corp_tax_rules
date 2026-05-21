from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableDefinition,
    DecisionTableVersion,
    ModuleDefinition,
    ModuleVersion,
    PrimitiveVersion,
    RuleDefinition,
    RuleVersion,
)
from .services import (
    activate_change_set,
    approve_change_set,
    approve_primitive_version,
    approve_rule_version,
    build_change_set_activation_report,
    build_module_readiness_report,
    create_or_update_draft_change_set_bundle,
    submit_change_set_for_review,
    submit_primitive_version_for_review,
    submit_rule_version_for_review,
    supersede_primitive_version,
    supersede_rule_version,
)
from .serializers import (
    ActivationActionSerializer,
    ApprovalActionSerializer,
    AssessmentContextSerializer,
    ChangeSetActivationResultSerializer,
    ChangeSetActivationReportSerializer,
    DraftChangeSetBundleSerializer,
    DraftChangeSetBundleResultSerializer,
    ChangeSetSerializer,
    LifecycleTransitionResultSerializer,
    DecisionTableDefinitionSerializer,
    DecisionTableVersionSerializer,
    ModuleDefinitionSerializer,
    ModuleReadinessReportSerializer,
    ModuleVersionSerializer,
    PrimitiveVersionSupersedeResultSerializer,
    PrimitiveVersionSupersedeSerializer,
    DeleteResultSerializer,
    RuleDefinitionSerializer,
    RuleVersionSupersedeResultSerializer,
    RuleVersionSupersedeSerializer,
    RuleVersionSerializer,
)


class CoreRulesIndexView(APIView):
    def get(self, request):
        return Response(
            {
                "assessment_contexts": AssessmentContext.objects.count(),
                "rule_definitions": RuleDefinition.objects.count(),
                "rule_versions": RuleVersion.objects.count(),
                "decision_table_definitions": DecisionTableDefinition.objects.count(),
                "decision_table_versions": DecisionTableVersion.objects.count(),
                "module_definitions": ModuleDefinition.objects.count(),
                "module_versions": ModuleVersion.objects.count(),
                "change_sets": ChangeSet.objects.count(),
            }
        )


class AssessmentContextListView(APIView):
    def get(self, request):
        serializer = AssessmentContextSerializer(AssessmentContext.objects.all(), many=True)
        return Response(serializer.data)


class RuleDefinitionListView(APIView):
    def get(self, request):
        serializer = RuleDefinitionSerializer(RuleDefinition.objects.all(), many=True)
        return Response(serializer.data)


class RuleVersionListView(APIView):
    def get(self, request):
        serializer = RuleVersionSerializer(RuleVersion.objects.select_related("rule").all(), many=True)
        return Response(serializer.data)


class DecisionTableDefinitionListView(APIView):
    def get(self, request):
        serializer = DecisionTableDefinitionSerializer(DecisionTableDefinition.objects.all(), many=True)
        return Response(serializer.data)


class DecisionTableVersionListView(APIView):
    def get(self, request):
        serializer = DecisionTableVersionSerializer(
            DecisionTableVersion.objects.select_related("decision_table").all(),
            many=True,
        )
        return Response(serializer.data)


class ModuleDefinitionListView(APIView):
    def get(self, request):
        serializer = ModuleDefinitionSerializer(ModuleDefinition.objects.all(), many=True)
        return Response(serializer.data)


class ModuleVersionListView(APIView):
    def get(self, request):
        serializer = ModuleVersionSerializer(ModuleVersion.objects.all(), many=True)
        return Response(serializer.data)


class ModuleReadinessView(APIView):
    def get(self, request, module_code):
        assessment_context = request.query_params.get("assessment_context", "AY_2026_27").strip()
        report = build_module_readiness_report(
            module_code=module_code,
            assessment_context=assessment_context,
        )
        serializer = ModuleReadinessReportSerializer(report)
        return Response(serializer.data)


class ChangeSetListView(APIView):
    def get(self, request):
        serializer = ChangeSetSerializer(ChangeSet.objects.all(), many=True)
        return Response(serializer.data)


class ChangeSetDetailView(APIView):
    def get(self, request, code):
        serializer = ChangeSetSerializer(ChangeSet.objects.get(code=code))
        return Response(serializer.data)


class ChangeSetActivationReadinessView(APIView):
    def get(self, request, code):
        change_set = ChangeSet.objects.get(code=code)
        report = build_change_set_activation_report(change_set=change_set)
        serializer = ChangeSetActivationReportSerializer(report)
        return Response(serializer.data)


class DraftChangeSetBundleView(APIView):
    def post(self, request):
        serializer = DraftChangeSetBundleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = create_or_update_draft_change_set_bundle(
                code=serializer.validated_data["code"].strip(),
                name=serializer.validated_data["name"].strip(),
                description=serializer.validated_data.get("description", "").strip(),
                assessment_context_code=serializer.validated_data["assessment_context"].strip(),
                rule_version_ids=serializer.validated_data.get("rule_version_ids", []),
                primitive_version_ids=serializer.validated_data.get("primitive_version_ids", []),
                decision_table_version_ids=serializer.validated_data.get("decision_table_version_ids", []),
                module_version_ids=serializer.validated_data.get("module_version_ids", []),
            )
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)

        response = DraftChangeSetBundleResultSerializer(result)
        return Response(response.data, status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK)


class RuleVersionSupersedeView(APIView):
    def post(self, request):
        serializer = RuleVersionSupersedeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = supersede_rule_version(
            source_rule_version_id=serializer.validated_data["source_rule_version_id"],
        )
        response = RuleVersionSupersedeResultSerializer(result)
        return Response(response.data)


class RuleVersionSubmitReviewView(APIView):
    def post(self, request, pk):
        try:
            result = submit_rule_version_for_review(rule_version_id=pk)
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class RuleVersionApproveView(APIView):
    def post(self, request, pk):
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = approve_rule_version(
                rule_version_id=pk,
                approved_by=serializer.validated_data.get("approved_by", "system").strip() or "system",
            )
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class PrimitiveVersionSupersedeView(APIView):
    def post(self, request):
        serializer = PrimitiveVersionSupersedeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = supersede_primitive_version(
            source_primitive_version_id=serializer.validated_data["source_primitive_version_id"],
            replacement_rule_version_ids=serializer.validated_data.get("replacement_rule_version_ids", []),
        )
        response = PrimitiveVersionSupersedeResultSerializer(result)
        return Response(response.data)


class PrimitiveVersionSubmitReviewView(APIView):
    def post(self, request, pk):
        try:
            result = submit_primitive_version_for_review(primitive_version_id=pk)
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class PrimitiveVersionApproveView(APIView):
    def post(self, request, pk):
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = approve_primitive_version(
                primitive_version_id=pk,
                approved_by=serializer.validated_data.get("approved_by", "system").strip() or "system",
            )
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class ChangeSetSubmitReviewView(APIView):
    def post(self, request, code):
        try:
            result = submit_change_set_for_review(change_set_code=code)
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class ChangeSetApproveView(APIView):
    def post(self, request, code):
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = approve_change_set(
                change_set_code=code,
                approved_by=serializer.validated_data.get("approved_by", "system").strip() or "system",
            )
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = LifecycleTransitionResultSerializer(result)
        return Response(response.data)


class ChangeSetActivateView(APIView):
    def post(self, request, code):
        serializer = ActivationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = activate_change_set(
                change_set_code=code,
                activated_by=serializer.validated_data.get("activated_by", "system").strip() or "system",
            )
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
        response = ChangeSetActivationResultSerializer(result)
        return Response(response.data)


class RuleVersionDeleteView(APIView):
    def delete(self, request, pk):
        try:
            rule_version = RuleVersion.objects.get(pk=pk)
            label = str(rule_version)
            rule_version.delete()
            response = DeleteResultSerializer(
                {"deleted": True, "message": f"Deleted draft rule version {label}."}
            )
            return Response(response.data)
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)


class PrimitiveVersionDeleteView(APIView):
    def delete(self, request, pk):
        try:
            primitive_version = PrimitiveVersion.objects.get(pk=pk)
            label = str(primitive_version)
            primitive_version.delete()
            response = DeleteResultSerializer(
                {"deleted": True, "message": f"Deleted draft primitive version {label}."}
            )
            return Response(response.data)
        except ValidationError as exc:
            response = DeleteResultSerializer({"deleted": False, "message": exc.messages[0]})
            return Response(response.data, status=status.HTTP_400_BAD_REQUEST)
