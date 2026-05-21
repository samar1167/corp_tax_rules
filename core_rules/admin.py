from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableDefinition,
    DecisionTableVersion,
    ModuleDefinition,
    ModuleVersion,
    PrimitiveDefinition,
    PrimitiveVersion,
    RuleDefinition,
    RuleVersion,
)


class ProtectedDeleteAdminMixin:
    def delete_model(self, request, obj):
        try:
            obj.delete()
        except ValidationError as exc:
            self.message_user(request, exc.messages[0], level=messages.ERROR)

    def delete_queryset(self, request, queryset):
        deleted_count = 0
        for obj in queryset:
            try:
                obj.delete()
                deleted_count += 1
            except ValidationError as exc:
                self.message_user(request, exc.messages[0], level=messages.ERROR)

        if deleted_count:
            self.message_user(
                request,
                f"Deleted {deleted_count} draft record(s).",
                level=messages.SUCCESS,
            )


@admin.register(AssessmentContext)
class AssessmentContextAdmin(admin.ModelAdmin):
    list_display = ("code", "assessment_year", "financial_year", "effective_from", "is_active")
    list_filter = ("assessment_year", "is_active")
    search_fields = ("code", "assessment_year", "financial_year")


@admin.register(RuleDefinition)
class RuleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "name", "scope")
    list_filter = ("scope",)
    search_fields = ("rule_id", "name")


@admin.register(RuleVersion)
class RuleVersionAdmin(ProtectedDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("rule", "version", "status", "mode", "severity", "approved_by")
    list_filter = ("status", "mode", "severity")
    search_fields = ("rule__rule_id", "rule__name", "source_reference")


@admin.register(PrimitiveDefinition)
class PrimitiveDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module_scope")
    list_filter = ("module_scope",)
    search_fields = ("code", "name")


@admin.register(PrimitiveVersion)
class PrimitiveVersionAdmin(ProtectedDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("primitive", "version", "status", "approved_by")
    list_filter = ("status",)
    filter_horizontal = ("rules",)
    search_fields = ("primitive__code", "primitive__name")


@admin.register(ModuleDefinition)
class ModuleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scope")
    list_filter = ("scope",)
    search_fields = ("code", "name")


@admin.register(DecisionTableDefinition)
class DecisionTableDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scope")
    list_filter = ("scope",)
    search_fields = ("code", "name")


@admin.register(DecisionTableVersion)
class DecisionTableVersionAdmin(ProtectedDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("decision_table", "version", "status", "module_scope", "approved_by")
    list_filter = ("status", "module_scope")
    filter_horizontal = ("input_primitives",)
    search_fields = ("decision_table__code", "decision_table__name")


@admin.register(ModuleVersion)
class ModuleVersionAdmin(ProtectedDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("module", "version", "assessment_context", "status", "approved_by")
    list_filter = ("status", "assessment_context")
    filter_horizontal = ("primitives", "decision_tables")
    search_fields = ("module__code", "module__name")


@admin.register(ChangeSet)
class ChangeSetAdmin(ProtectedDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "assessment_context", "status", "approved_by", "activated_at")
    list_filter = ("status", "assessment_context")
    search_fields = ("code", "name")
    filter_horizontal = (
        "rule_versions",
        "primitive_versions",
        "decision_table_versions",
        "module_versions",
    )
