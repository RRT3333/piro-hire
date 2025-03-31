from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import RecruitmentSettings, Question, Applicant, Application, Answer

@admin.register(RecruitmentSettings)
class RecruitmentSettingsAdmin(admin.ModelAdmin):
    list_display = ['title', 'application_start_date', 'application_end_date', 'interview_start_date', 'interview_end_date', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        if RecruitmentSettings.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['order', 'question_text', 'recruitment_settings']
    list_filter = ['recruitment_settings']
    ordering = ['recruitment_settings', 'order']

@admin.register(Applicant)
class ApplicantAdmin(UserAdmin):
    list_display = ('email', 'name', 'phone_number', 'university', 'major', 'grade', 'academic_status', 'is_active')
    search_fields = ('email', 'name', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('개인정보', {'fields': ('name', 'phone_number', 'birth_date')}),
        ('학적정보', {'fields': ('university', 'major', 'grade', 'academic_status')}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('중요 일자', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'name', 'phone_number'),
        }),
    )

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.profile_picture.url)
        return "No picture uploaded"
    profile_picture_preview.short_description = '프로필 사진 미리보기'

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'answer_text']
    can_delete = False
    max_num = 0
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'applicant_name',
        'applicant_email',
        'applicant_phone',
        'recruitment_settings',
        'status',
        'get_interview_preferences',
        'get_interview_schedule',
        'created_at'
    ]
    list_filter = ['status', 'recruitment_settings']
    search_fields = ['applicant__email', 'applicant__name', 'applicant__phone_number']
    readonly_fields = [
        'created_at', 'updated_at', 'submitted_at',
        'applicant_details', 'get_interview_preferences',
        'get_interview_schedule'
    ]
    inlines = [AnswerInline]
    fieldsets = (
        ('지원자 정보', {
            'fields': ('applicant_details',)
        }),
        ('지원서 상태', {
            'fields': ('status', 'created_at', 'updated_at', 'submitted_at')
        }),
        ('면접 희망 시간', {
            'fields': (
                'interview_sat_morning', 'interview_sat_afternoon',
                'interview_sun_morning', 'interview_sun_afternoon',
                'get_interview_preferences'
            )
        }),
        ('면접 일정', {
            'fields': (
                'interview_date', 'interview_start_time', 'interview_end_time',
                'interview_location', 'interview_notes', 'get_interview_schedule'
            )
        }),
    )

    def applicant_name(self, obj):
        return obj.applicant.name
    applicant_name.short_description = '이름'
    applicant_name.admin_order_field = 'applicant__name'

    def applicant_email(self, obj):
        return obj.applicant.email
    applicant_email.short_description = '이메일'
    applicant_email.admin_order_field = 'applicant__email'

    def applicant_phone(self, obj):
        return obj.applicant.phone_number
    applicant_phone.short_description = '전화번호'
    applicant_phone.admin_order_field = 'applicant__phone_number'

    def get_interview_preferences(self, obj):
        return obj.get_interview_preferences_display()
    get_interview_preferences.short_description = '면접 희망 시간'

    def get_interview_schedule(self, obj):
        if obj.interview_date:
            return obj.get_interview_schedule_display()
        return '면접 일정 미정'
    get_interview_schedule.short_description = '확정된 면접 일정'

    def applicant_details(self, obj):
        applicant = obj.applicant
        return format_html(
            '<div style="margin-bottom: 10px;">'
            '<strong>이름:</strong> {name}<br>'
            '<strong>이메일:</strong> {email}<br>'
            '<strong>전화번호:</strong> {phone}<br>'
            '<strong>생년월일:</strong> {birth_date}<br>'
            '<strong>학교:</strong> {university}<br>'
            '<strong>전공:</strong> {major}<br>'
            '<strong>학년:</strong> {grade}학년<br>'
            '<strong>학적상태:</strong> {academic_status}'
            '</div>',
            name=applicant.name,
            email=applicant.email,
            phone=applicant.phone_number,
            birth_date=applicant.birth_date,
            university=applicant.university,
            major=applicant.major,
            grade=applicant.grade,
            academic_status=dict(Applicant._meta.get_field('academic_status').choices)[applicant.academic_status]
        )
    applicant_details.short_description = '지원자 상세 정보'

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
