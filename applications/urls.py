from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.index, name='index'),
    path('start/', views.start_application, name='start_application'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('questions/', views.answer_questions, name='answer_questions'),
    path('complete/', views.application_complete, name='application_complete'),
    path('view/<int:application_id>/', views.view_application, name='view_application'),
] 