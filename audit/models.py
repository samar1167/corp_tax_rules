from django.db import models

from core_rules.models import AssessmentContext, ModuleVersion, TimestampedModel


class EvaluationLog(TimestampedModel):
    event_id = models.CharField(max_length=100, unique=True)
    assessment_context = models.ForeignKey(
        AssessmentContext,
        on_delete=models.PROTECT,
        related_name="evaluation_logs",
    )
    module_version = models.ForeignKey(
        ModuleVersion,
        on_delete=models.PROTECT,
        related_name="evaluation_logs",
        null=True,
        blank=True,
    )
    taxpayer_hash = models.CharField(max_length=128)
    input_payload_hash = models.CharField(max_length=128)
    primitive_trace = models.JSONField(default=list, blank=True)
    decision_table_trace = models.JSONField(default=dict, blank=True)
    outcome_payload = models.JSONField(default=dict)
    rule_trace = models.JSONField(default=list, blank=True)
    previous_entry_hash = models.CharField(max_length=128, blank=True)
    entry_hash = models.CharField(max_length=128)

    class Meta:
        ordering = ["-created_at", "event_id"]

    def __str__(self) -> str:
        return self.event_id
