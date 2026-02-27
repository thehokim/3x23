from __future__ import annotations

import os
from typing import Dict

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ContactSubmission, JobApplication
from .services.telegram import tg_send_text, tg_send_document


# ========================================================================
# FLAGS
# ========================================================================
VALIDATE_POSITION = True   # ✅ РЕКОМЕНДУЮ True: принимаем только коды/известные подписи
VALIDATE_FORM_ID = False   # пока не используем


# ========================================================================
# CONTACT FORM (patients): codes stored in DB
# ========================================================================
ALLOWED_POSITION_CODES = {
    "clinic_owner",
    "lab_owner",
    "self_employed",
    "buyer",
    "dealer",
    "agent",
    "other",
}

PLACEHOLDER_LABELS = {
    "Select problem",
    "Выберите проблему",
    "Muammoni tanlang",

    # старые
    "Select role",
    "Выберите должность",
    "Выберите Должность",

    # UZ (должность/позиция)
    "Lavozimni tanlang",
    "Select position",
    # RU (опечатка в форме es/pro)
    "Выберите Должност ",
    "Выберите Должность ",
}

# fallback: если где-то ещё отправляется ТЕКСТ, а не код
POSITION_LABEL_TO_CODE = {
    # OLD roles (EN)
    "Clinic Owner": "clinic_owner",
    "Laboratory Owner / Dental Technician": "lab_owner",
    "Self-employed dentist": "self_employed",
    "Buyer": "buyer",
    "Dealer": "dealer",
    "Agent": "agent",
    "Other": "other",

    # OLD roles (RU)
    "Владелец клиники": "clinic_owner",
    "Владелец лаборатории / Зубной техник": "lab_owner",
    "Владелец лаборатории / Зубной специалист": "lab_owner",
    "Самозанятый стоматолог": "self_employed",
    "Стоматолог работающий на себя": "self_employed",
    "Покупатель": "buyer",
    "Дилер": "dealer",
    "Агент": "agent",
    "Другое": "other",

    # OLD roles (UZ)
    "Klinika rahbari": "clinic_owner",
    "Laboratoriya rahbari / Tish Ustasi": "lab_owner",
    "O'zini ish bilan band qilgan stomatolog": "self_employed",
    "Xususiy stomatolog": "self_employed",
    "Xaridor": "buyer",
    "Sotib oluvchi": "buyer",
    "Diler": "dealer",
    "Agent": "agent",
    "Boshqa": "other",

    # NEW patient problems (EN)
    "Consultation": "clinic_owner",
    "Pain": "lab_owner",
    "Swelling": "self_employed",
    "Implant issue (loose/discomfort)": "buyer",
    "Crown/bridge issue": "dealer",
    "Warranty / Service": "agent",
    "Other (problem)": "other",

    # NEW patient problems (RU)
    "Консультация": "clinic_owner",
    "Боль": "lab_owner",
    "Отёк": "self_employed",
    "Проблема с имплантом (шатается/дискомфорт)": "buyer",
    "Проблема с коронкой/мостом": "dealer",
    "Гарантия / Сервис": "agent",
    "Другое": "other",

    # NEW patient problems (UZ)
    "Konsultatsiya": "clinic_owner",
    "Og'riq": "lab_owner",
    "Shish": "self_employed",
    "Implant bilan muammo (bo'shashgan/noqulaylik)": "buyer",
    "Kron/most bilan muammo": "dealer",
    "Kafolat / Servis": "agent",
    "Boshqa": "other",
}


# ========================================================================
# JOB FORM (work with us): codes stored in DB
# ========================================================================
ALLOWED_JOB_CODES = {
    "implantologists_speakers",
    "italy_abroad_agents",
    "dealer_distributors",
    "other",
}

JOB_PLACEHOLDER_LABELS = {
    "Select position",
    "Выбирайте",
    "Выберите должность",
    "Lavozimni tanlang",
    "Ariza berilayotgan lavozim",
}

JOB_LABEL_TO_CODE = {
    # EN
    "Implantologists Speakers": "implantologists_speakers",
    "Italy/Abroad Agents": "italy_abroad_agents",
    "Dealer-Distributors Italy/Abroad": "dealer_distributors",
    "Other": "other",

    # RU (как у тебя на страницах)
    "Лекторы-имплантологи": "implantologists_speakers",
    "Агенты (Зарубежье)": "italy_abroad_agents",
    "Дилеры-дистрибьюторы (Зарубежье)": "dealer_distributors",
    "Другое": "other",

    # UZ (Lavora con noi / Biz bilan ishlang)
    "Implantolog ma'ruzachilar": "implantologists_speakers",
    "Implantolog ma\u2019ruzachilar": "implantologists_speakers",  # Unicode apostrophe
    "Agentlar Italiya/Xorij": "italy_abroad_agents",
    "Diler-distribyutorlar Italiya/Xorij": "dealer_distributors",
    "Boshqa": "other",
}


# ========================================================================
# REVERSE LABEL MAPPING (patient forms send codes, pro forms send label text)
# ========================================================================

# Reverse mapping: DB code → human-readable problem label (for patient forms)
CODE_TO_PROBLEM_LABEL = {
    "en": {
        "clinic_owner": "Consultation",
        "lab_owner": "Pain",
        "self_employed": "Swelling",
        "buyer": "Implant issue (loose/discomfort)",
        "dealer": "Crown/bridge issue",
        "agent": "Warranty / Service",
        "other": "Other",
    },
    "ru": {
        "clinic_owner": "Консультация",
        "lab_owner": "Боль",
        "self_employed": "Отёк",
        "buyer": "Проблема с имплантом (шатается/дискомфорт)",
        "dealer": "Проблема с коронкой/мостом",
        "agent": "Гарантия / Сервис",
        "other": "Другое",
    },
    "uz": {
        "clinic_owner": "Konsultatsiya",
        "lab_owner": "Og'riq",
        "self_employed": "Shish",
        "buyer": "Implant bilan muammo (bo'shashgan/noqulaylik)",
        "dealer": "Kron/most bilan muammo",
        "agent": "Kafolat / Servis",
        "other": "Boshqa",
    },
}


# ========================================================================
# HELPERS
# ========================================================================
def cors(resp: HttpResponse) -> HttpResponse:
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return resp


def get_client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_valid_email(email: str) -> bool:
    return ("@" in email) and ("." in email)


def is_placeholder_value(value: str, placeholder_set: set[str]) -> bool:
    s = (value or "").strip()
    return (not s) or (s in placeholder_set)


def detect_lang(request: HttpRequest) -> str:
    """
    1) form_fields[lang] если есть
    2) иначе по referer: /en/ -> en, /es/ -> ru, /it/ -> uz
    """
    lang = (request.POST.get("form_fields[lang]", "") or "").strip().lower()
    if lang in {"en", "ru", "uz"}:
        return lang

    ref = (request.META.get("HTTP_REFERER", "") or "").lower()
    if "/en/" in ref:
        return "en"
    if "/ru/" in ref:
        return "ru"
    if "/uz/" in ref:
        return "uz"
    return "en"


def map_position_to_db(position: str) -> str:
    s = (position or "").strip()
    if s in ALLOWED_POSITION_CODES:
        return s
    return POSITION_LABEL_TO_CODE.get(s, "")


def validate_position(position: str) -> bool:
    s = (position or "").strip()
    if is_placeholder_value(s, PLACEHOLDER_LABELS):
        return False

    if not VALIDATE_POSITION:
        return True

    return (s in ALLOWED_POSITION_CODES) or (s in POSITION_LABEL_TO_CODE)


def map_job_position_to_db(position: str) -> str:
    s = (position or "").strip()
    if s in ALLOWED_JOB_CODES:
        return s
    return JOB_LABEL_TO_CODE.get(s, "")


def validate_job_position(position: str) -> bool:
    s = (position or "").strip()
    if is_placeholder_value(s, JOB_PLACEHOLDER_LABELS):
        return False

    if not VALIDATE_POSITION:
        return True

    return (s in ALLOWED_JOB_CODES) or (s in JOB_LABEL_TO_CODE)


def get_uploaded_cv_file(request: HttpRequest):
    return request.FILES.get("form_fields[file_cv][]") or request.FILES.get("form_fields[file_cv]")


# ========================================================================
# VIEWS
# ========================================================================
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def contact_form_submission(request: HttpRequest):
    if request.method == "OPTIONS":
        return cors(JsonResponse({"status": "ok"}))

    try:
        lang = detect_lang(request)

        form_id = (request.POST.get("form_id", "") or "").strip()
        first_name = (request.POST.get("form_fields[first_name]", "") or "").strip()
        last_name = (request.POST.get("form_fields[last_name]", "") or "").strip()
        email = (request.POST.get("form_fields[email]", "") or "").strip()
        phone = (request.POST.get("form_fields[phone]", "") or "").strip()
        position = (request.POST.get("form_fields[position]", "") or "").strip()
        city = (request.POST.get("form_fields[city]", "") or "").strip()
        province = (request.POST.get("form_fields[province]", "") or "").strip()
        country = (request.POST.get("form_fields[country]", "") or "").strip()
        message = (request.POST.get("form_fields[message]", "") or "").strip()
        days = (request.POST.get("form_fields[days]", "") or "").strip()
        privacy1 = request.POST.get("form_fields[privacy1]", "") == "on"
        privacy2 = request.POST.get("form_fields[privacy2]", "") == "on"

        errors: Dict[str, str] = {}

        if not first_name:
            errors["first_name"] = "First name is required"
        if not last_name:
            errors["last_name"] = "Last name is required"

        if not email:
            errors["email"] = "Email is required"
        elif not is_valid_email(email):
            errors["email"] = "Invalid email format"

        if not phone:
            errors["phone"] = "Phone is required"

        if not validate_position(position):
            errors["position"] = "Position is required" if not position else f"Invalid position: {position}"

        position_db = map_position_to_db(position)
        if VALIDATE_POSITION and not position_db:
            errors["position"] = f"Invalid position: {position}"

        if not city:
            errors["city"] = "City is required"
        if not province:
            errors["province"] = "Province is required"
        if not country:
            errors["country"] = "Country is required"

        if not privacy1:
            errors["privacy1"] = "Privacy policy must be accepted"
        if not privacy2:
            errors["privacy2"] = "Newsletter consent must be accepted"

        if errors:
            return cors(JsonResponse({"success": False, "errors": errors}, status=400))

        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        submission = ContactSubmission.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            position=position_db or "other",
            city=city,
            province=province,
            country=country,
            message=message if message else None,
            days=days if days else None,
            privacy1=privacy1,
            privacy2=privacy2,
            source_form_id=form_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Telegram (не ломаем заявку если Telegram упал)
        try:
            # Пациентские формы отправляют КОД как value (<option value="clinic_owner">)
            # Про-формы отправляют ТЕКСТ как value (<option value="Владелец клиники">)
            if position in ALLOWED_POSITION_CODES:
                field_label = "Problem"
                labels = CODE_TO_PROBLEM_LABEL.get(lang, CODE_TO_PROBLEM_LABEL["en"])
                position_display = labels.get(position_db or "other", position)
            else:
                field_label = "Position"
                position_display = position

            text = (
                "🦷 NEW CONTACT FORM\n"
                f"🌍 Lang: {lang}\n"
                f"👤 {first_name} {last_name}\n"
                f"📧 {email}\n"
                f"📞 {phone}\n"
                f"📌 {field_label}: {position_display}\n"
                f"📍 {city}, {province}, {country}\n"
                f"🗓 Days: {days or '-'}\n"
                f"💬 Message: {message or '-'}\n"
                f"🧾 Form ID: {form_id or '-'}\n"
                f"🌐 Page: {request.META.get('HTTP_REFERER','-')}\n"
                f"🌐 IP: {ip_address}\n"
            )
            tg_send_text(text)
        except Exception:
            pass

        return cors(JsonResponse({"success": True, "submission_id": str(submission.id)}, status=201))

    except Exception as e:
        return cors(JsonResponse({"success": False, "errors": {"general": str(e)}}, status=500))


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def job_application_submission(request: HttpRequest):
    if request.method == "OPTIONS":
        return cors(JsonResponse({"status": "ok"}))

    try:
        lang = detect_lang(request)

        form_id = (request.POST.get("form_id", "") or "").strip()
        name = (request.POST.get("form_fields[name]", "") or "").strip()
        surname = (request.POST.get("form_fields[surname]", "") or "").strip()
        email = (request.POST.get("form_fields[email]", "") or "").strip()
        phone = (request.POST.get("form_fields[phone]", "") or "").strip()
        position = (request.POST.get("form_fields[position]", "") or "").strip()
        hours = (request.POST.get("form_fields[hours]", "") or "").strip()
        message = (request.POST.get("form_fields[message]", "") or "").strip()
        privacy = request.POST.get("form_fields[privacy]", "") == "on"
        cv_file = get_uploaded_cv_file(request)

        errors: Dict[str, str] = {}

        if not name:
            errors["name"] = "First name is required"
        if not surname:
            errors["surname"] = "Last name is required"

        if not email:
            errors["email"] = "Email is required"
        elif not is_valid_email(email):
            errors["email"] = "Invalid email format"

        if not phone:
            errors["phone"] = "Phone is required"

        if not validate_job_position(position):
            errors["position"] = "Position is required" if not position else f"Invalid position: {position}"

        position_db = map_job_position_to_db(position)
        if VALIDATE_POSITION and not position_db:
            errors["position"] = f"Invalid position: {position}"

        if not privacy:
            errors["privacy"] = "Privacy policy must be accepted"

        if cv_file:
            if cv_file.size > 2 * 1024 * 1024:
                errors["file_cv"] = "CV file too large (max 2MB)"
            else:
                allowed_extensions = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
                ext = os.path.splitext(cv_file.name)[1].lower()
                if ext not in allowed_extensions:
                    errors["file_cv"] = "Invalid file type"

        if errors:
            return cors(JsonResponse({"success": False, "errors": errors}, status=400))

        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        application = JobApplication.objects.create(
            name=name,
            surname=surname,
            email=email,
            phone=phone,
            position=position_db or "other",
            hours=hours if hours else None,
            message=message if message else None,
            privacy=privacy,
            source_form_id=form_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if cv_file:
            application.cv_file = cv_file
            application.save()

        # Telegram
        try:
            text = (
                "💼 NEW JOB APPLICATION\n"
                f"🌍 Lang: {lang}\n"
                f"👤 {name} {surname}\n"
                f"📧 {email}\n"
                f"📞 {phone}\n"
                f"📌 Position: {position}\n"
                f"⏰ Hours: {hours or '-'}\n"
                f"💬 Message: {message or '-'}\n"
                f"🧾 Form ID: {form_id or '-'}\n"
                f"🌐 Page: {request.META.get('HTTP_REFERER','-')}\n"
                f"🌐 IP: {ip_address}\n"
            )
            tg_send_text(text)

            if cv_file:
                tg_send_document(cv_file, caption=f"CV from {name} {surname} ({email})")
        except Exception:
            pass

        return cors(JsonResponse({"success": True, "submission_id": str(application.id)}, status=201))

    except Exception as e:
        return cors(JsonResponse({"success": False, "errors": {"general": str(e)}}, status=500))
