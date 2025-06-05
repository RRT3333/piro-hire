from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.auth.models import User

from .models import RecruitmentSettings, Applicant, Application, Question, Answer
from .forms import ApplicantForm, ApplicationForm, DynamicAnswerForm, EmailVerificationForm

def get_active_recruitment():
    return RecruitmentSettings.objects.filter(
        is_active=True,
        application_start_date__lte=timezone.now(),
        application_end_date__gte=timezone.now()
    ).first()

def index(request):
    recruitment = get_active_recruitment()
    if not recruitment:
        return render(request, 'applications/recruitment_closed.html')
    
    context = {
        'recruitment': recruitment,
    }
    
    if request.user.is_authenticated:
        context['has_application'] = request.user.applications.exists()
    
    return render(request, 'applications/index.html', context)

def start_application(request):
    recruitment = get_active_recruitment()
    if not recruitment:
        return redirect('applications:index')
    
    # 이미 로그인한 사용자의 경우
    if request.user.is_authenticated:
        # 지원서가 있는 경우 질문 답변 페이지로 리다이렉트
        if hasattr(request.user, 'applications') and request.user.applications.filter(recruitment_settings=recruitment).exists():
            return redirect('applications:answer_questions')
        
        # 지원서가 없는 경우 기존 정보로 폼 초기화
        applicant_form = ApplicantForm(instance=request.user)
    else:
        # 새로운 사용자의 경우 빈 폼
        applicant_form = ApplicantForm()
    
    application_form = ApplicationForm()
    
    if request.method == 'POST':
        applicant_form = ApplicantForm(request.POST, request.FILES, instance=request.user if request.user.is_authenticated else None)
        application_form = ApplicationForm(request.POST)
        
        if applicant_form.is_valid() and application_form.is_valid():
            with transaction.atomic():
                applicant = applicant_form.save(commit=False)
                if not request.user.is_authenticated:
                    # 새로운 사용자의 경우 임시 비밀번호 설정
                    temp_password = User.objects.make_random_password()
                    applicant.set_password(temp_password)
                applicant.save()
                
                # 기존 지원서가 있는지 확인
                application, created = Application.objects.get_or_create(
                    applicant=applicant,
                    recruitment_settings=recruitment,
                    defaults={'status': 'draft'}
                )
                
                # 면접 시간 업데이트
                application.interview_times = application_form.cleaned_data['interview_times']
                application.save()
                
                if not request.user.is_authenticated:
                    # 새로운 사용자 로그인 처리
                    login(request, applicant)
                
                # 이메일 인증 코드 발송
                send_verification_email(applicant)
                
                messages.success(request, '이메일로 인증 코드가 발송되었습니다. 이메일을 확인해주세요.')
                return redirect('applications:verify_email')
    
    return render(request, 'applications/start_application.html', {
        'applicant_form': applicant_form,
        'application_form': application_form,
        'recruitment': recruitment,
    })

@login_required
def verify_email(request):
    applicant = request.user
    if applicant.is_email_verified:
        return redirect('applications:answer_questions')
    
    if request.method == 'POST':
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            if applicant.is_token_valid() and applicant.email_verification_token == form.cleaned_data['verification_code']:
                applicant.verify_email()
                messages.success(request, '이메일이 성공적으로 인증되었습니다.')
                return redirect('applications:answer_questions')
            else:
                messages.error(request, '잘못된 인증 코드이거나 만료된 코드입니다.')
    else:
        form = EmailVerificationForm()
    
    return render(request, 'applications/verify_email.html', {
        'form': form,
        'applicant': applicant
    })

@login_required
def resend_verification_email(request):
    applicant = request.user
    if applicant.is_email_verified:
        return JsonResponse({'status': 'error', 'message': '이미 인증된 이메일입니다.'})
    
    send_verification_email(applicant)
    return JsonResponse({'status': 'success', 'message': '인증 이메일이 재전송되었습니다.'})

def send_verification_email(applicant):
    verification_code = applicant.generate_verification_code()
    subject = '[피로그래밍] 이메일 인증'
    message = render_to_string('applications/email/verification.html', {
        'applicant': applicant,
        'verification_code': verification_code
    })
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [applicant.email],
        html_message=message,
        fail_silently=False
    )

@login_required
def answer_questions(request):
    applicant = request.user
    if not applicant.is_email_verified:
        return redirect('applications:verify_email')
    
    application = get_object_or_404(Application, applicant=applicant)
    questions = Question.objects.filter(recruitment_settings=application.recruitment_settings)
    
    if request.method == 'POST':
        form = DynamicAnswerForm(request.POST, questions=questions)
        if form.is_valid():
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('question_'):
                    question_id = int(field_name.split('_')[1])
                    question = Question.objects.get(id=question_id)
                    Answer.objects.update_or_create(
                        application=application,
                        question=question,
                        defaults={'answer_text': value}
                    )
            
            if 'save_draft' in request.POST:
                messages.success(request, '임시저장되었습니다.')
                return redirect('applications:answer_questions')
            else:
                application.submit()
                messages.success(request, '지원서가 성공적으로 제출되었습니다.')
                return redirect('applications:application_complete')
    else:
        initial_data = {
            f'question_{answer.question_id}': answer.answer_text
            for answer in Answer.objects.filter(application=application)
        }
        form = DynamicAnswerForm(initial=initial_data, questions=questions)
    
    return render(request, 'applications/answer_questions.html', {
        'form': form,
        'application': application
    })

@login_required
def application_complete(request):
    application = get_object_or_404(Application, applicant=request.user)
    if application.status != 'submitted':
        return redirect('applications:answer_questions')
    
    return render(request, 'applications/application_complete.html', {
        'application': application
    })

@login_required
def view_application(request, application_id):
    application = get_object_or_404(Application, id=application_id, applicant=request.user)
    answers = Answer.objects.filter(application=application).select_related('question')
    
    return render(request, 'applications/view_application.html', {
        'application': application,
        'answers': answers
    })
