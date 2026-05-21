from rest_framework import serializers

from .models import GovernanceEvaluation


class GovernanceCrossModuleSerializer(serializers.Serializer):
    itr_assessment_context = serializers.CharField(required=False, default="AY_2026_27")
    corporate_assessment_context = serializers.CharField(required=False, default="TY_2026_27")
    governance_assessment_context = serializers.CharField(required=False, default="GOV_2026_27")
    itr_profile = serializers.JSONField()
    corporate_profile = serializers.JSONField()


class GovernanceEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceEvaluation
        fields = "__all__"
