from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    path('contact/', views.contact_form_submission, name='contact_form'),
    path('job-application/', views.job_application_submission, name='job_application'),
]