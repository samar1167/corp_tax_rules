from rest_framework import serializers

from .models import CorporateTaxEvaluation


class CorporateTaxProfileSerializer(serializers.Serializer):
    assessment_context = serializers.CharField(required=False, default="TY_2026_27")
    registration_country = serializers.CharField()
    registration_act = serializers.CharField()
    management_control_in_india = serializers.BooleanField(required=False, default=False)
    office_fixed_place_in_india = serializers.BooleanField(required=False, default=False)
    agents_dependent_in_india = serializers.BooleanField(required=False, default=False)
    construction_project_duration_days = serializers.IntegerField(required=False, default=0)
    previous_year_turnover = serializers.IntegerField(required=False, default=0)
    incorporation_date = serializers.DateField()
    business_activity = serializers.CharField()
    regime_option = serializers.CharField(required=False, allow_blank=True, default="DEFAULT")


class CorporateTaxEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorporateTaxEvaluation
        fields = "__all__"
