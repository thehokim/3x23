"""
Раздача статического сайта (фронт) из SITE_ROOT.
"""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404


def serve_site(request, path=''):
    """Отдаёт файлы из SITE_ROOT по пути path (it/, en/, es/, index.html и т.д.)."""
    root = Path(settings.SITE_ROOT)
    if not root.exists():
        raise Http404("Site root not found")

    # Безопасность: запрет выхода за пределы root
    path = path.strip('/').replace('..', '')
    full = (root / path).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise Http404()

    if full.is_dir():
        full = full / 'index.html'
    if not full.is_file():
        raise Http404()

    content_type, _ = mimetypes.guess_type(str(full), strict=False)
    content_type = content_type or 'application/octet-stream'
    return FileResponse(full.open('rb'), content_type=content_type)
