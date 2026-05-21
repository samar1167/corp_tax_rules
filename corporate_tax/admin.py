from django.contrib import admin

from .models import CorporateTaxEvaluation, CorporateTaxPlaceholder


@admin.register(CorporateTaxPlaceholder)
class CorporateTaxPlaceholderAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(CorporateTaxEvaluation)
class CorporateTaxEvaluationAdmin(admin.ModelAdmin):
    list_display = ("id", "entity_type", "regime_track", "filing_route", "created_at")
    list_filter = ("entity_type", "regime_track", "filing_route")
    readonly_fields = ("created_at", "profile", "decision_trace")
    search_fields = ("entity_type", "regime_track", "filing_route")
