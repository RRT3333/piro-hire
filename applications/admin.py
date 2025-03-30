from django.contrib import admin
from django.utils.html import format_html
from .models import RecruitmentSettings, Question, Applicant, Application, Answer

@admin.register(RecruitmentSettings)
class RecruitmentSettingsAdmin(admin.ModelAdmin):
    list_display = ['application_start_date', 'application_end_date', 'interview_start_date', 'interview_end_date', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        if RecruitmentSettings.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'question_text', 'max_length', 'is_required', 'recruitment_settings']
    list_filter = ['recruitment_settings', 'is_required']
    ordering = ['recruitment_settings', 'order']

@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'phone_number', 'is_email_verified']
    list_filter = ['is_email_verified']
    search_fields = ['email', 'name', 'phone_number']
    readonly_fields = ['is_email_verified', 'email_verification_token', 'token_generated_at', 'profile_picture_preview']
    fieldsets = [
        ('기본 정보', {'fields': ['email', 'name', 'phone_number', 'profile_picture', 'profile_picture_preview']}),
        ('인증 정보', {'fields': ['is_email_verified', 'email_verification_token', 'token_generated_at']}),
        ('권한', {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
    ]

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.profile_picture.url)
        return "No picture uploaded"
    profile_picture_preview.short_description = '프로필 사진 미리보기'

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'recruitment_settings', 'status', 'get_interview_times', 'created_at']
    list_filter = ['status', 'recruitment_settings']
    search_fields = ['applicant__email', 'applicant__name']
    readonly_fields = ['created_at', 'updated_at', 'submitted_at']

    def get_interview_times(self, obj):
        times_dict = dict(Application.INTERVIEW_TIME_CHOICES)
        return ', '.join(times_dict[time] for time in obj.interview_times)
    get_interview_times.short_description = '면접 가능 시간'

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['get_applicant_name', 'get_question_text', 'get_answer_preview']
    list_filter = ['application__recruitment_settings', 'question']
    search_fields = ['application__applicant__email', 'application__applicant__name', 'answer_text']

    def get_applicant_name(self, obj):
        return obj.application.applicant.name
    get_applicant_name.short_description = '지원자'
    get_applicant_name.admin_order_field = 'application__applicant__name'

    def get_question_text(self, obj):
        return obj.question.question_text[:50]
    get_question_text.short_description = '질문'
    get_question_text.admin_order_field = 'question__question_text'

    def get_answer_preview(self, obj):
        return obj.answer_text[:100] + '...' if len(obj.answer_text) > 100 else obj.answer_text
    get_answer_preview.short_description = '답변 미리보기'
