from django.db import models


class CorporateTaxPlaceholder(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.code
