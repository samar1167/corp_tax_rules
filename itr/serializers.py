from rest_framework import serializers

from .models import ITREvaluation, ITRRegimeEvaluation, ITRTaxComputationEvaluation


class TaxpayerProfileSerializer(serializers.Serializer):
    assessment_context = serializers.CharField(required=False, default="AY_2026_27")
    residential_status = serializers.CharField()
    total_income = serializers.IntegerField()
    category = serializers.CharField()
    is_director_in_company = serializers.BooleanField()
    has_unlisted_equity_investment = serializers.BooleanField()
    has_foreign_assets = serializers.BooleanField()
    has_foreign_account_signing_authority = serializers.BooleanField()
    income_sources = serializers.ListField(child=serializers.CharField())
    has_capital_gains = serializers.BooleanField()
    capital_gain_type = serializers.CharField(required=False, allow_blank=True, default="")
    ltcg_112a_amount = serializers.IntegerField(required=False, default=0)
    has_carried_forward_capital_loss = serializers.BooleanField(required=False, default=False)
    house_property_count = serializers.IntegerField()
    has_brought_forward_house_property_loss = serializers.BooleanField()
    tds_deducted_under_194N = serializers.BooleanField()
    has_esop_tax_deferred = serializers.BooleanField()
    has_business_profession_income = serializers.BooleanField(required=False, default=False)


class ITREvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ITREvaluation
        fields = "__all__"


class RegimeSelectionSerializer(serializers.Serializer):
    assessment_context = serializers.CharField(required=False, default="AY_2026_27")
    has_business_profession_income = serializers.BooleanField()
    regime_selection = serializers.CharField(required=False, allow_blank=True, default="NOT_SPECIFIED")
    filing_date = serializers.DateField()
    due_date_139_1 = serializers.DateField()


class ITRRegimeEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ITRRegimeEvaluation
        fields = "__all__"


class TaxComputationSerializer(serializers.Serializer):
    assessment_context = serializers.CharField(required=False, default="AY_2026_27")
    applicable_regime = serializers.CharField()
    taxable_income = serializers.IntegerField()
    special_rate_income = serializers.IntegerField(required=False, default=0)


class ITRTaxComputationEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ITRTaxComputationEvaluation
        fields = "__all__"
