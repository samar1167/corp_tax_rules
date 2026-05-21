from django.contrib import admin

from .models import CrossModuleRule, GovernanceEvaluation


@admin.register(CrossModuleRule)
class CrossModuleRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "version", "status", "approved_by")
    list_filter = ("status",)
    filter_horizontal = ("depends_on_modules",)
    search_fields = ("rule_id", "name", "source_reference")


@admin.register(GovernanceEvaluation)
class GovernanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ("id", "assessment_context", "governance_status", "created_at")
    list_filter = ("assessment_context", "governance_status")
    readonly_fields = (
        "assessment_context",
        "input_payload",
        "itr_summary",
        "corporate_summary",
        "governance_status",
        "governance_actions",
        "governance_summary",
        "rule_trace",
        "created_at",
        "updated_at",
    )
