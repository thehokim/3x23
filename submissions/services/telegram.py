# submissions/services/telegram.py
import requests
from django.conf import settings


def tg_send_text(text: str) -> bool:
    """Send text message to Telegram (во все чаты из TELEGRAM_CHAT_IDS)."""
    if not getattr(settings, "TELEGRAM_ENABLED", False):
        return False

    chat_ids = getattr(settings, "TELEGRAM_CHAT_IDS", None) or [getattr(settings, "TELEGRAM_CHAT_ID", "")]
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    ok = True
    for chat_id in chat_ids:
        if not chat_id:
            continue
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        try:
            r = requests.post(url, data=payload, timeout=10)
            if r.status_code != 200:
                ok = False
        except Exception:
            ok = False
    return ok


def tg_send_document(file_obj, caption: str = "") -> bool:
    """
    Send document to Telegram (во все чаты из TELEGRAM_CHAT_IDS).
    file_obj: Django UploadedFile (request.FILES['...'])
    """
    if not getattr(settings, "TELEGRAM_ENABLED", False):
        return False

    chat_ids = getattr(settings, "TELEGRAM_CHAT_IDS", None) or [getattr(settings, "TELEGRAM_CHAT_ID", "")]
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument"
    ok = True
    for chat_id in chat_ids:
        if not chat_id:
            continue
        try:
            file_obj.seek(0)
            files = {"document": (file_obj.name, file_obj.file, file_obj.content_type)}
            data = {"chat_id": chat_id, "caption": caption}
            r = requests.post(url, data=data, files=files, timeout=20)
            if r.status_code != 200:
                ok = False
        except Exception:
            ok = False
    return ok