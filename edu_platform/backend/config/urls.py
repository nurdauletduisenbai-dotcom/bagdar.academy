from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.news.sitemap import sitemap_xml

admin.site.site_header = 'bagdar.academy'
admin.site.site_title = 'bagdar.academy'


def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'bagdar_academy_api'})


def ready_check(request):
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    return JsonResponse({
        'status': 'ready' if db_ok else 'not_ready',
        'database': 'connected' if db_ok else 'error',
    }, status=200 if db_ok else 503)


urlpatterns = [
    # Корень -> Swagger UI со всеми эндпоинтами
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False)),

    # Health & Readiness Probes
    path('health/', health_check, name='health'),
    path('ready/', ready_check, name='ready'),

    # SEO: карта публичных страниц сайта (nginx проксирует /sitemap.xml сюда)
    path('sitemap.xml', sitemap_xml, name='sitemap'),

    # Django Admin
    path('admin/', admin.site.urls),

    # OpenAPI 3 Documentation on /docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 Versioned Endpoints
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/orgs/', include('apps.organizations.urls')),
    path('api/v1/courses/', include('apps.courses.urls')),
    path('api/v1/videos/', include('apps.videos.urls')),
    path('api/v1/tests/', include('apps.assessments.urls')),
    path('api/v1/parents/', include('apps.accounts.parent_urls')),
    path('api/v1/progress/', include('apps.progress.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/news/', include('apps.news.urls')),
    path('api/v1/', include('apps.content.urls')),
    path('api/v1/', include('apps.questions.urls')),
    path('api/v1/', include('apps.assignments.urls')),
    path('api/v1/', include('apps.schedule.urls')),
    path('api/v1/', include('apps.notifications.urls')),
]
