from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('start/', views.start_application, name='start_application'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('applications/', views.application_list, name='application_list'),
    path('applications/<int:application_id>/', views.view_application, name='view_application'),
    path('answer-questions/', views.answer_questions, name='answer_questions'),
    path('application-complete/', views.application_complete, name='application_complete'),
    
    # 이메일/비밀번호 찾기
    path('find-email/', views.find_email, name='find_email'),
    path('reset-password/', views.reset_password_request, name='reset_password_request'),
    path('reset-password/<str:token>/', views.reset_password_confirm, name='reset_password_confirm'),
] 