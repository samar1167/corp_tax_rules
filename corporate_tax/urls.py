from django.urls import path

from .views import (
    CorporateTaxConceptEvaluationView,
    CorporateTaxHealthView,
    CorporateTaxRecentEvaluationsView,
)

urlpatterns = [
    path("", CorporateTaxHealthView.as_view(), name="corporate-tax-health"),
    path("concept-evaluation/", CorporateTaxConceptEvaluationView.as_view(), name="corporate-tax-concept-evaluation"),
    path("evaluations/", CorporateTaxRecentEvaluationsView.as_view(), name="corporate-tax-evaluations"),
]
