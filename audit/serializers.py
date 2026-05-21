from rest_framework import serializers

from .models import EvaluationLog


class EvaluationLogSerializer(serializers.ModelSerializer):
    assessment_context_code = serializers.CharField(
        source="assessment_context.code",
        read_only=True,
    )
    module_version_label = serializers.SerializerMethodField()

    class Meta:
        model = EvaluationLog
        fields = [
            "id",
            "event_id",
            "assessment_context",
            "assessment_context_code",
            "module_version",
            "module_version_label",
            "taxpayer_hash",
            "input_payload_hash",
            "primitive_trace",
            "decision_table_trace",
            "outcome_payload",
            "rule_trace",
            "previous_entry_hash",
            "entry_hash",
            "created_at",
            "updated_at",
        ]

    def get_module_version_label(self, obj):
        return str(obj.module_version) if obj.module_version else None
