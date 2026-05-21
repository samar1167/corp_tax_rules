from django.urls import path

from .views import (
    ITRFormEligibilityView,
    ITRHealthView,
    ITRRecentEvaluationsView,
    ITRRecentRegimeEvaluationsView,
    ITRRecentTaxComputationEvaluationsView,
    ITRRegimeSelectionView,
    ITRTaxComputationView,
)

urlpatterns = [
    path("", ITRHealthView.as_view(), name="itr-health"),
    path("form-eligibility/", ITRFormEligibilityView.as_view(), name="itr-form-eligibility"),
    path("regime-selection/", ITRRegimeSelectionView.as_view(), name="itr-regime-selection"),
    path("tax-computation/", ITRTaxComputationView.as_view(), name="itr-tax-computation"),
    path("evaluations/", ITRRecentEvaluationsView.as_view(), name="itr-evaluations"),
    path("regime-evaluations/", ITRRecentRegimeEvaluationsView.as_view(), name="itr-regime-evaluations"),
    path(
        "tax-computation-evaluations/",
        ITRRecentTaxComputationEvaluationsView.as_view(),
        name="itr-tax-computation-evaluations",
    ),
]
