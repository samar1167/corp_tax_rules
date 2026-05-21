from django.db import models

from core_rules.models import AssessmentContext, ModuleVersion, StatusChoices, TimestampedModel


class CrossModuleRule(TimestampedModel):
    rule_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    source_reference = models.CharField(max_length=255)
    natural_language = models.TextField()
    structured_logic = models.JSONField(default=dict)
    depends_on_modules = models.ManyToManyField(ModuleVersion, related_name="cross_module_rules", blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rule_id", "-created_at"]

    def __str__(self) -> str:
        return f"{self.rule_id}@{self.version}"


class GovernanceEvaluation(TimestampedModel):
    assessment_context = models.ForeignKey(
        AssessmentContext,
        on_delete=models.PROTECT,
        related_name="governance_evaluations",
    )
    input_payload = models.JSONField(default=dict)
    itr_summary = models.JSONField(default=dict)
    corporate_summary = models.JSONField(default=dict)
    governance_status = models.CharField(max_length=40)
    governance_actions = models.JSONField(default=list)
    governance_summary = models.JSONField(default=dict)
    rule_trace = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Governance evaluation #{self.pk}"
