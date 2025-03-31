from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, EmailValidator, RegexValidator
from django.utils import timezone
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from PIL import Image
import os
from PIL import ExifTags
from django.core.exceptions import ValidationError
import magic
import pillow_heif

class RecruitmentSettings(models.Model):
    title = models.CharField('모집 제목', max_length=200)
    description = models.TextField('모집 설명')
    application_start_date = models.DateTimeField('지원 시작일')
    application_end_date = models.DateTimeField('지원 마감일')
    interview_start_date = models.DateTimeField('면접 시작일')
    interview_end_date = models.DateTimeField('면접 종료일')
    is_active = models.BooleanField('활성화 여부', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '모집 설정'
        verbose_name_plural = '모집 설정 목록'

    def __str__(self):
        return self.title

class Question(models.Model):
    recruitment_settings = models.ForeignKey(RecruitmentSettings, on_delete=models.CASCADE, related_name='questions', verbose_name='모집 기수')
    question_text = models.TextField('질문')
    max_length = models.IntegerField(default=500)
    order = models.PositiveIntegerField('순서')
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '질문'
        verbose_name_plural = '질문 목록'
        ordering = ['order']

    def __str__(self):
        return self.question_text

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

def validate_image_file(value):
    # 파일 MIME 타입 확인
    file_mime = magic.from_buffer(value.read(1024), mime=True)
    value.seek(0)  # 파일 포인터 리셋

    # 허용된 이미지 타입
    valid_mime_types = ['image/jpeg', 'image/png', 'image/heic', 'image/heif']
    
    if file_mime not in valid_mime_types:
        raise ValidationError('JPG, PNG, HEIC 또는 HEIF 형식의 이미지만 업로드 가능합니다.')
    
    # 파일 크기 제한 (5MB)
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('파일 크기는 5MB를 초과할 수 없습니다.')

class Applicant(AbstractUser):
    name = models.CharField('이름', max_length=100, blank=True)
    email = models.EmailField('이메일', unique=True)
    photo = models.ImageField(
        upload_to='applicant_photos/%Y/%m/', 
        verbose_name='프로필 사진', 
        help_text='3x4cm 사진을 업로드해주세요. (JPG, PNG, HEIC 형식, 최대 5MB)',
        null=True, 
        blank=True,
        validators=[validate_image_file]
    )
    phone_number = models.CharField(
        '전화번호',
        max_length=11,
        validators=[RegexValidator(r'^\d{11}$', '올바른 전화번호를 입력해주세요.')],
        help_text='"-" 없이 숫자만 입력해주세요.',
        null=True,
        blank=True
    )
    birth_date = models.DateField('생년월일', null=True, blank=True)
    university = models.CharField('대학교', max_length=100, blank=True)
    major = models.CharField('전공', max_length=100, blank=True)
    grade = models.IntegerField(
        '학년', 
        choices=[(i, f'{i}학년') for i in range(1, 5)],
        null=True,
        blank=True
    )
    academic_status = models.CharField(
        '학적상태',
        max_length=20,
        choices=[
            ('attending', '재학'),
            ('leave', '휴학'),
            ('graduated', '졸업'),
            ('expected_graduation', '졸업예정'),
        ],
        null=True,
        blank=True
    )
    
    email_verification_token = models.CharField(max_length=6, blank=True)
    token_generated_at = models.DateTimeField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    
    password_reset_token = models.UUIDField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = '지원자'
        verbose_name_plural = '지원자 목록'
    
    def __str__(self):
        return f'{self.name} ({self.email})'
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        
        # 기존 이미지가 있다면 삭제
        try:
            this = Applicant.objects.get(id=self.id)
            if this.photo != self.photo and this.photo:
                this.photo.delete(save=False)
        except:
            pass

        super().save(*args, **kwargs)
        
        # 이미지 처리
        if self.photo:
            file_path = self.photo.path
            file_name, file_ext = os.path.splitext(file_path)
            
            try:
                # HEIC/HEIF 파일 처리
                if file_ext.lower() in ['.heic', '.heif']:
                    heif_file = pillow_heif.read_heif(file_path)
                    img = Image.frombytes(
                        heif_file.mode,
                        heif_file.size,
                        heif_file.data,
                        "raw",
                    )
                    
                    # HEIC/HEIF 파일을 JPG로 변환
                    new_path = file_name + '.jpg'
                    self.photo.name = os.path.basename(new_path)
                    img.save(new_path, 'JPEG', quality=95)
                    
                    # 원본 HEIC/HEIF 파일 삭제
                    os.remove(file_path)
                    file_path = new_path
                else:
                    img = Image.open(file_path)

                # EXIF 방향 정보 처리
                try:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break
                    exif = dict(img._getexif().items())

                    if orientation in exif:
                        if exif[orientation] == 2:
                            img = img.transpose(Image.FLIP_LEFT_RIGHT)
                        elif exif[orientation] == 3:
                            img = img.rotate(180)
                        elif exif[orientation] == 4:
                            img = img.transpose(Image.FLIP_TOP_BOTTOM)
                        elif exif[orientation] == 5:
                            img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(90)
                        elif exif[orientation] == 6:
                            img = img.rotate(270)
                        elif exif[orientation] == 7:
                            img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(270)
                        elif exif[orientation] == 8:
                            img = img.rotate(90)
                except (AttributeError, KeyError, IndexError):
                    pass

                # 이미지 크기 및 비율 조정
                width, height = img.size
                target_ratio = 3/4
                current_ratio = width/height

                if current_ratio > target_ratio:  # 너무 넓은 경우
                    new_width = int(height * target_ratio)
                    left = (width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, height))
                elif current_ratio < target_ratio:  # 너무 높은 경우
                    new_height = int(width / target_ratio)
                    top = (height - new_height) // 2
                    img = img.crop((0, top, width, top + new_height))

                # 최종 크기로 리사이징 (300x400px)
                output_size = (300, 400)
                img = img.resize(output_size, Image.Resampling.LANCZOS)

                # 이미지 최적화 및 저장
                img.save(file_path, 'JPEG', quality=85, optimize=True)
                
            except Exception as e:
                # 이미지 처리 중 오류 발생 시 이미지 삭제
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.photo = None
                self.save()
                raise ValidationError(f'이미지 처리 중 오류가 발생했습니다: {str(e)}')
    
    def generate_verification_code(self):
        code = ''.join(random.choices(string.digits, k=6))
        self.email_verification_token = code
        self.token_generated_at = timezone.now()
        self.save()
        return code
    
    def is_token_valid(self):
        if not self.token_generated_at:
            return False
        return timezone.now() <= self.token_generated_at + timezone.timedelta(minutes=30)
    
    def verify_email(self):
        self.is_email_verified = True
        self.email_verification_token = ''
        self.token_generated_at = None
        self.save()
    
    def generate_password_reset_token(self):
        token = uuid.uuid4()
        self.password_reset_token = token
        self.token_generated_at = timezone.now()
        self.save()
        return token

class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('submitted', '제출완료'),
        ('document_screening', '서류심사중'),
        ('document_passed', '서류합격'),
        ('document_failed', '서류불합격'),
        ('interview_scheduled', '면접예정'),
        ('interview_completed', '면접완료'),
        ('final_passed', '최종합격'),
        ('final_failed', '최종불합격'),
    ]
    
    applicant = models.ForeignKey(
        Applicant,
        on_delete=models.CASCADE,
        verbose_name='지원자'
    )
    recruitment_settings = models.ForeignKey(
        RecruitmentSettings,
        on_delete=models.PROTECT,
        verbose_name='모집 기수'
    )
    status = models.CharField(
        '상태',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    submitted_at = models.DateTimeField('제출일', null=True, blank=True)
    
    # 면접 관련 필드
    interview_sat_morning = models.BooleanField('토요일 오전', default=False)
    interview_sat_afternoon = models.BooleanField('토요일 오후', default=False)
    interview_sun_morning = models.BooleanField('일요일 오전', default=False)
    interview_sun_afternoon = models.BooleanField('일요일 오후', default=False)
    
    interview_date = models.DateField('면접 날짜', null=True, blank=True)
    interview_start_time = models.TimeField('면접 시작 시간', null=True, blank=True)
    interview_end_time = models.TimeField('면접 종료 시간', null=True, blank=True)
    interview_location = models.CharField('면접 장소', max_length=200, blank=True)
    interview_notes = models.TextField('면접 참고사항', blank=True)
    
    class Meta:
        verbose_name = '지원서'
        verbose_name_plural = '지원서 목록'
    
    def __str__(self):
        return f'{self.applicant.name}의 지원서'
    
    def submit(self):
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save()
    
    def get_interview_schedule_display(self):
        if not all([self.interview_date, self.interview_start_time, self.interview_end_time]):
            return None
        
        weekday = ['월', '화', '수', '목', '금', '토', '일'][self.interview_date.weekday()]
        return f"{self.interview_date.strftime('%Y년 %m월 %d일')}({weekday}) {self.interview_start_time.strftime('%H:%M')} - {self.interview_end_time.strftime('%H:%M')}"
    
    def get_interview_preferences_display(self):
        times = []
        if self.interview_sat_morning:
            times.append('토요일 오전')
        if self.interview_sat_afternoon:
            times.append('토요일 오후')
        if self.interview_sun_morning:
            times.append('일요일 오전')
        if self.interview_sun_afternoon:
            times.append('일요일 오후')
        return ', '.join(times) if times else '선택된 시간 없음'

class Answer(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, verbose_name='지원서')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='질문')
    answer_text = models.TextField('답변')
    
    class Meta:
        verbose_name = '답변'
        verbose_name_plural = '답변 목록'
    
    def __str__(self):
        return f'{self.application.applicant.name}의 답변'
