import uuid
import os
from django.db import models


class ContactSubmission(models.Model):
    # ✅ Теперь choices = "проблемы пациента" (в админке)
    # ✅ Коды НЕ меняем, чтобы данные в БД совпадали с тем, что сохраняет views.py
    POSITION_CHOICES = [
        ("clinic_owner", "Consultation / Консультация / Konsultatsiya"),
        ("lab_owner", "Pain / Боль / Og'riq"),
        ("self_employed", "Swelling / Отёк / Shish"),
        ("buyer", "Implant issue / Проблема с имплантом / Implant bilan muammo"),
        ("dealer", "Crown/bridge issue / Проблема с коронкой/мостом / Kron/most bilan muammo"),
        ("agent", "Warranty / Service / Гарантия / Сервис / Kafolat / Servis"),
        ("other", "Other / Другое / Boshqa"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)

    # max_length=50 оставляю как у тебя — хватает (self_employed = 13)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default="other")

    city = models.CharField(max_length=255)
    province = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    days = models.TextField(blank=True, null=True, verbose_name="Days and times to be contacted")
    privacy1 = models.BooleanField(default=False, verbose_name="Privacy policy accepted")
    privacy2 = models.BooleanField(default=False, verbose_name="Newsletter/Marketing consent")
    source_form_id = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"


def cv_upload_path(instance, filename):
    """Generate upload path for CV files."""
    filename = f"{instance.id}_{filename}"
    year = getattr(instance.created_at, "year", "unknown")
    month = getattr(instance.created_at, "month", "unknown")
    return os.path.join("cv_uploads", str(year), str(month), filename)


class JobApplication(models.Model):
    """Model for Work with Us form submissions."""

    POSITION_CHOICES = [
        ("implantologists_speakers", "Implantologists Speakers"),
        ("italy_abroad_agents", "Italy/Abroad Agents"),
        ("dealer_distributors", "Dealer-Distributors Italy/Abroad"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="First Name")
    surname = models.CharField(max_length=255, verbose_name="Last Name")
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default="other")
    hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contact hours")
    message = models.TextField(blank=True, null=True)
    cv_file = models.FileField(upload_to=cv_upload_path, blank=True, null=True, verbose_name="CV/Resume")
    privacy = models.BooleanField(default=False, verbose_name="Privacy policy accepted")
    source_form_id = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"

    def __str__(self):
        return f"{self.name} {self.surname} - {self.position} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def full_name(self):
        return f"{self.name} {self.surname}"

    @property
    def cv_filename(self):
        if self.cv_file:
            return os.path.basename(self.cv_file.name)
        return None
