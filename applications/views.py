from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

from .models import RecruitmentSettings, Applicant, Application, Question, Answer
from .forms import ApplicantForm, ApplicationForm, DynamicAnswerForm, EmailVerificationForm, FindEmailForm, PasswordResetRequestForm, PasswordResetConfirmForm, SignUpForm

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
        context['has_application'] = hasattr(request.user, 'application_set') and request.user.application_set.exists()
    
    return render(request, 'applications/index.html', context)

def signup(request):
    if request.user.is_authenticated:
        return redirect('applications:index')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            # 회원가입 직후 이메일 인증 메일 발송
            send_verification_email(user)
            messages.success(request, '회원가입이 완료되었습니다. 이메일로 전송된 인증 코드를 입력해주세요.')
            return redirect('applications:verify_email')
    else:
        form = SignUpForm()
    
    return render(request, 'applications/signup.html', {'form': form})

@login_required
def start_application(request):
    recruitment_settings = get_object_or_404(RecruitmentSettings, is_active=True)
    
    # 현재 활성화된 모집 기간인지 확인
    if not (recruitment_settings.application_start_date <= timezone.now() <= recruitment_settings.application_end_date):
        messages.error(request, '현재 지원 기간이 아닙니다.')
        return redirect('applications:index')
    
    # 기존 지원서 확인
    existing_application = Application.objects.filter(
        applicant=request.user,
        recruitment_settings=recruitment_settings
    ).first()
    
    if existing_application:
        if existing_application.status != 'draft':
            messages.warning(request, '이미 지원서를 제출하셨습니다.')
            return redirect('applications:view_application', application_id=existing_application.id)
        application = existing_application
    else:
        application = Application(
            applicant=request.user,
            recruitment_settings=recruitment_settings
        )
    
    if request.method == 'POST':
        applicant_form = ApplicantForm(request.POST, instance=request.user)
        application_form = ApplicationForm(request.POST, instance=application)
        
        if applicant_form.is_valid() and application_form.is_valid():
            applicant_form.save()
            application = application_form.save()
            messages.success(request, '기본 정보가 저장되었습니다.')
            return redirect('applications:verify_email')
    else:
        applicant_form = ApplicantForm(instance=request.user)
        application_form = ApplicationForm(instance=application)
    
    context = {
        'applicant_form': applicant_form,
        'application_form': application_form,
        'recruitment_settings': recruitment_settings,
    }
    return render(request, 'applications/start_application.html', context)

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
    
    # 현재 활성화된 모집 기간 확인
    recruitment_settings = get_active_recruitment()
    if not recruitment_settings:
        messages.error(request, '현재 지원 기간이 아닙니다.')
        return redirect('applications:index')
    
    # 기존 지원서 확인 또는 새로 생성
    application = Application.objects.filter(
        applicant=applicant,
        recruitment_settings=recruitment_settings
    ).first()
    
    if not application:
        application = Application.objects.create(
            applicant=applicant,
            recruitment_settings=recruitment_settings
        )
    
    questions = Question.objects.filter(recruitment_settings=recruitment_settings)
    
    if request.method == 'POST':
        answer_form = DynamicAnswerForm(request.POST, questions=questions)
        interview_form = ApplicationForm(request.POST, instance=application)
        
        if answer_form.is_valid() and interview_form.is_valid():
            # 면접 시간 선호도 저장
            interview_form.save()
            
            # 답변 저장
            for field_name, value in answer_form.cleaned_data.items():
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
                # 면접 시간을 하나도 선택하지 않은 경우
                if not any([
                    application.interview_sat_morning,
                    application.interview_sat_afternoon,
                    application.interview_sun_morning,
                    application.interview_sun_afternoon
                ]):
                    messages.error(request, '면접 가능 시간을 최소 한 개 이상 선택해주세요.')
                    return redirect('applications:answer_questions')
                
                application.submit()
                messages.success(request, '지원서가 성공적으로 제출되었습니다.')
                return redirect('applications:application_complete')
    else:
        initial_data = {
            f'question_{answer.question_id}': answer.answer_text
            for answer in Answer.objects.filter(application=application)
        }
        answer_form = DynamicAnswerForm(initial=initial_data, questions=questions)
        interview_form = ApplicationForm(instance=application)
    
    return render(request, 'applications/answer_questions.html', {
        'answer_form': answer_form,
        'interview_form': interview_form,
        'application': application,
        'recruitment_settings': recruitment_settings
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
    # 현재 로그인한 사용자의 지원서만 조회 가능
    try:
        application = Application.objects.select_related(
            'applicant',
            'recruitment_settings'
        ).prefetch_related(
            'answer_set__question'  # 질문과 답변을 한 번에 가져옴
        ).get(
            id=application_id,
            applicant=request.user  # 현재 로그인한 사용자의 지원서만 조회
        )
    except Application.DoesNotExist:
        messages.error(request, '존재하지 않거나 접근 권한이 없는 지원서입니다.')
        return redirect('applications:index')
    
    # 면접 희망 시간 정보 가져오기
    interview_times = []
    if application.interview_sat_morning:
        interview_times.append('토요일 오전 (10:00 ~ 12:00)')
    if application.interview_sat_afternoon:
        interview_times.append('토요일 오후 (14:00 ~ 17:00)')
    if application.interview_sun_morning:
        interview_times.append('일요일 오전 (10:00 ~ 12:00)')
    if application.interview_sun_afternoon:
        interview_times.append('일요일 오후 (14:00 ~ 17:00)')
    
    # 답변 정보 정리
    answers = []
    for answer in application.answer_set.all():
        answers.append({
            'question': answer.question.question_text,
            'answer': answer.answer_text,
            'max_length': answer.question.max_length
        })
    
    context = {
        'application': application,
        'interview_times': interview_times,
        'answers': answers,
        'status_display': application.get_status_display(),
        'submitted_at': application.submitted_at,
    }
    
    return render(request, 'applications/view_application.html', context)

def find_email(request):
    if request.method == 'POST':
        form = FindEmailForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            phone_number = form.cleaned_data['phone_number']
            
            try:
                applicant = Applicant.objects.get(name=name, phone_number=phone_number)
                messages.success(request, f'회원님의 이메일은 {applicant.email} 입니다.')
                return redirect('login')
            except Applicant.DoesNotExist:
                messages.error(request, '입력하신 정보와 일치하는 회원이 없습니다.')
    else:
        form = FindEmailForm()
    
    return render(request, 'applications/find_email.html', {'form': form})

def reset_password_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                applicant = Applicant.objects.get(email=email)
                # 비밀번호 재설정 토큰 생성 (24시간 유효)
                token = applicant.generate_password_reset_token()
                
                # 이메일 발송
                subject = '[피로그래밍] 비밀번호 재설정'
                message = render_to_string('applications/email/password_reset.html', {
                    'applicant': applicant,
                    'reset_url': request.build_absolute_uri(
                        reverse('applications:reset_password_confirm', args=[token])
                    )
                })
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=message,
                    fail_silently=False
                )
                
                messages.success(request, '비밀번호 재설정 링크가 이메일로 발송되었습니다.')
                return redirect('login')
            except Applicant.DoesNotExist:
                messages.error(request, '입력하신 이메일과 일치하는 회원이 없습니다.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'applications/reset_password_request.html', {'form': form})

def reset_password_confirm(request, token):
    try:
        # 토큰으로 사용자 찾기
        applicant = Applicant.objects.get(
            password_reset_token=token,
            token_generated_at__gt=timezone.now() - timezone.timedelta(days=1)
        )
        
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                # 새 비밀번호 설정
                applicant.set_password(form.cleaned_data['new_password1'])
                # 토큰 초기화
                applicant.password_reset_token = ''
                applicant.token_generated_at = None
                applicant.save()
                
                messages.success(request, '비밀번호가 성공적으로 변경되었습니다. 새로운 비밀번호로 로그인해주세요.')
                return redirect('login')
        else:
            form = PasswordResetConfirmForm()
        
        return render(request, 'applications/reset_password_confirm.html', {'form': form})
    
    except Applicant.DoesNotExist:
        messages.error(request, '유효하지 않거나 만료된 링크입니다.')
        return redirect('login')

@login_required
def application_list(request):
    applications = Application.objects.filter(applicant=request.user)
    return render(request, 'applications/application_list.html', {'applications': applications})
