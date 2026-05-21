from django.contrib import admin

from .models import EvaluationLog


@admin.register(EvaluationLog)
class EvaluationLogAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "assessment_context",
        "module_version",
        "short_entry_hash",
        "created_at",
    )
    list_filter = ("assessment_context", "module_version")
    search_fields = ("event_id", "taxpayer_hash", "input_payload_hash")
    readonly_fields = (
        "event_id",
        "assessment_context",
        "module_version",
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
    )

    def short_entry_hash(self, obj):
        return obj.entry_hash[:12]

    short_entry_hash.short_description = "Entry Hash"
