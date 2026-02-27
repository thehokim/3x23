from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config.views import serve_site

urlpatterns = [
    path('admin/', admin.site.urls),
    path('forms/', include('submissions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Фронт (статика) — в конце, чтобы не перехватывать admin/forms/media
urlpatterns += [
    path('', serve_site),
    path('<path:path>', serve_site),
]