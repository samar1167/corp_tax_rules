from django.db import models


class ITRPlaceholder(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.code


class ITREvaluation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    profile = models.JSONField(default=dict)
    selected_form = models.CharField(max_length=20)
    decision_trace = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"ITR evaluation #{self.pk}"


class ITRRegimeEvaluation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    profile = models.JSONField(default=dict)
    applicable_regime = models.CharField(max_length=30)
    decision_trace = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"ITR regime evaluation #{self.pk}"


class ITRTaxComputationEvaluation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    profile = models.JSONField(default=dict)
    applicable_regime = models.CharField(max_length=30)
    total_liability = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    decision_trace = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"ITR tax computation #{self.pk}"
