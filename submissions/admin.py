import csv
from django.contrib import admin
from django.http import HttpResponse
from .models import ContactSubmission
from django.utils.html import format_html
from .models import JobApplication


def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contact_submissions.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Created At', 'First Name', 'Last Name', 'Email', 'Phone',
        'Position', 'City', 'Province', 'Country', 'Message', 'Days',
        'Privacy Policy', 'Newsletter Consent', 'IP Address', 'User Agent', 'Form ID'
    ])
    
    for submission in queryset:
        writer.writerow([
            str(submission.id),
            submission.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            submission.first_name,
            submission.last_name,
            submission.email,
            submission.phone,
            submission.get_position_display(),
            submission.city,
            submission.province,
            submission.country,
            submission.message or '',
            submission.days or '',
            'Yes' if submission.privacy1 else 'No',
            'Yes' if submission.privacy2 else 'No',
            submission.ip_address or '',
            submission.user_agent or '',
            submission.source_form_id or '',
        ])
    
    return response


export_csv.short_description = "Export selected submissions to CSV"


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'first_name',
        'last_name',
        'email',
        'phone',
        'position',
        'city',
        'country',
        'privacy1',
        'privacy2',
    ]
    
    list_filter = [
        'position',
        'country',
        'created_at',
        'privacy1',
        'privacy2',
    ]
    
    search_fields = [
        'first_name',
        'last_name',
        'email',
        'phone',
        'city',
        'country',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'ip_address',
        'user_agent',
        'source_form_id',
    ]
    
    actions = [export_csv]
    
    def has_add_permission(self, request):
        return False
    


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'name',
        'surname',
        'email',
        'phone',
        'position',
        'has_cv',
        'privacy',
    ]
    
    list_filter = [
        'position',
        'created_at',
        'privacy',
    ]
    
    search_fields = [
        'name',
        'surname',
        'email',
        'phone',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'ip_address',
        'user_agent',
        'source_form_id',
        'cv_download_link',
    ]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'surname', 'email', 'phone')
        }),
        ('Application Details', {
            'fields': ('position', 'hours', 'message')
        }),
        ('CV/Resume', {
            'fields': ('cv_file', 'cv_download_link')
        }),
        ('Privacy', {
            'fields': ('privacy',)
        }),
        ('Metadata', {
            'fields': ('id', 'source_form_id', 'ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_cv(self, obj):
        """Simple boolean indicator for CV."""
        if obj.cv_file:
            return '✓'
        return '✗'
    has_cv.short_description = 'CV'
    
    def cv_download_link(self, obj):
        """Show download link for CV - only in detail view."""
        if obj.cv_file:
            try:
                url = obj.cv_file.url
                filename = obj.cv_filename or 'Download'
                return format_html(
                    '<a href="{0}" target="_blank" download>📥 Download CV: {1}</a>',
                    url,
                    filename
                )
            except Exception as e:
                return f"CV file exists but error: {str(e)}"
        return "No CV uploaded"
    cv_download_link.short_description = 'CV Download'