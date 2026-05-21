from django.contrib import admin

from .models import CrossModuleRule


@admin.register(CrossModuleRule)
class CrossModuleRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "version", "status", "approved_by")
    list_filter = ("status",)
    filter_horizontal = ("depends_on_modules",)
    search_fields = ("rule_id", "name", "source_reference")
