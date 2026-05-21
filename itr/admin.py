from django.contrib import admin

from .models import ITREvaluation, ITRPlaceholder, ITRRegimeEvaluation, ITRTaxComputationEvaluation

admin.site.register(ITRPlaceholder)
admin.site.register(ITREvaluation)
admin.site.register(ITRRegimeEvaluation)
admin.site.register(ITRTaxComputationEvaluation)
