from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, EmailValidator
from django.utils import timezone
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
import random
import string

class RecruitmentSettings(models.Model):
    application_start_date = models.DateTimeField()
    application_end_date = models.DateTimeField()
    interview_start_date = models.DateTimeField()
    interview_end_date = models.DateTimeField()
    recruitment_notice = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recruitment Settings'
        verbose_name_plural = 'Recruitment Settings'

    def __str__(self):
        return f"Recruitment Period: {self.application_start_date} - {self.application_end_date}"

class Question(models.Model):
    recruitment_settings = models.ForeignKey(RecruitmentSettings, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    max_length = models.IntegerField(default=500)
    order = models.IntegerField()
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question {self.order}: {self.question_text[:50]}..."

class ApplicantManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일 주소는 필수입니다')
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Applicant(AbstractUser):
    username = models.CharField(max_length=150, unique=True, null=True)  # username field is not used
    email = models.EmailField(
        unique=True,
        verbose_name='이메일',
        help_text='로그인 시 사용할 이메일 주소를 입력해주세요.'
    )
    name = models.CharField(
        max_length=150,
        verbose_name='이름',
        help_text='실명을 입력해주세요.'
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='전화번호',
        help_text='연락 가능한 전화번호를 입력해주세요.'
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        verbose_name='프로필 사진',
        help_text='5MB 이하의 이미지 파일을 업로드해주세요.'
    )
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name='이메일 인증 여부'
    )
    email_verification_token = models.CharField(
        max_length=6,
        blank=True,
        verbose_name='이메일 인증 코드'
    )
    token_generated_at = models.DateTimeField(
        null=True,
        verbose_name='인증 코드 생성 시간'
    )

    objects = ApplicantManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    # Add related_name to avoid clashes with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='applicant_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='applicant_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def generate_verification_code(self):
        code = ''.join(random.choices(string.digits, k=6))
        self.email_verification_token = code
        self.token_generated_at = timezone.now()
        self.save()
        return code

    def verify_email(self):
        self.is_email_verified = True
        self.email_verification_token = ''
        self.save()

    def is_token_valid(self):
        if not self.token_generated_at:
            return False
        return (timezone.now() - self.token_generated_at).total_seconds() < 1800

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        verbose_name = '지원자'
        verbose_name_plural = '지원자 목록'

class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ]

    INTERVIEW_TIME_CHOICES = [
        ('sat_morning', '토요일 오전'),
        ('sat_afternoon', '토요일 오후'),
        ('sun_morning', '일요일 오전'),
        ('sun_afternoon', '일요일 오후'),
    ]

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name='applications')
    recruitment_settings = models.ForeignKey(RecruitmentSettings, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    interview_times = models.JSONField(default=list, help_text='선택한 면접 가능 시간 목록')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['applicant', 'recruitment_settings']

    def __str__(self):
        return f"Application by {self.applicant.name} ({self.status})"

    def submit(self):
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()

class Answer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['application', 'question']

    def __str__(self):
        return f"Answer to {self.question} by {self.application.applicant.username}"
