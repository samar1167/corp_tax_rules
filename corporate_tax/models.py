from django.db import models


class CorporateTaxPlaceholder(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.code


class CorporateTaxEvaluation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    profile = models.JSONField(default=dict)
    entity_type = models.CharField(max_length=40)
    regime_track = models.CharField(max_length=40)
    filing_route = models.CharField(max_length=60)
    decision_trace = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Corporate tax evaluation #{self.pk}"
