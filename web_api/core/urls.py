# file: web_api/core/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from analytics.views import register

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analytics.urls')),
    # Auth
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register, name='register'),
    # Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
