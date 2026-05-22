from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SectorViewSet, CompanyViewSet, MLScoreViewSet, FinancialsViewSet,
    dashboard, company_detail, sector_analysis, health_dashboard, ping
)

router = DefaultRouter()
router.register(r'sectors', SectorViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'scores', MLScoreViewSet)
router.register(r'financials', FinancialsViewSet)

urlpatterns = [
    path('ping/', ping, name='ping'),
    path('', dashboard, name='dashboard'),
    path('company/<str:symbol>/', company_detail, name='company_detail'),
    path('sectors/', sector_analysis, name='sector_analysis'),
    path('health/', health_dashboard, name='health_dashboard'),
    path('api/', include(router.urls)),
]
