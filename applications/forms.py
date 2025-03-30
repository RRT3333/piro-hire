from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from .models import Applicant, Application, Answer, Question

class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['email', 'name', 'phone_number', 'profile_picture']
        help_texts = {
            'email': '인증 코드가 발송될 이메일 주소입니다.',
            'phone_number': '연락 가능한 휴대폰 번호를 입력해주세요.',
            'profile_picture': '3x4 증명사진을 업로드해주세요.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['phone_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['profile_picture'].widget.attrs.update({'class': 'form-control'})

    def clean_profile_picture(self):
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            # 파일 크기 체크 (5MB 제한)
            if profile_picture.size > 5 * 1024 * 1024:
                raise ValidationError('프로필 사진은 5MB를 초과할 수 없습니다.')
            
            # 이미지 파일 타입 체크
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if hasattr(profile_picture, 'content_type') and profile_picture.content_type not in allowed_types:
                raise ValidationError('JPG, PNG, GIF 형식의 이미지만 업로드 가능합니다.')
            
        return profile_picture

class ApplicationForm(forms.ModelForm):
    interview_times = forms.MultipleChoiceField(
        choices=Application.INTERVIEW_TIME_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='면접 가능 시간',
        help_text='가능한 시간을 모두 선택해주세요.'
    )

    class Meta:
        model = Application
        fields = ['interview_times']
        help_texts = {
            'interview_times': '면접 가능한 시간을 모두 선택해주세요.',
        }

class EmailVerificationForm(forms.Form):
    verification_code = forms.CharField(
        label='인증 코드',
        max_length=6,
        min_length=6,
        help_text='이메일로 발송된 6자리 인증 코드를 입력해주세요.'
    )

class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if not Applicant.objects.filter(email=email, is_email_verified=True).exists():
            raise ValidationError("인증된 이메일 주소가 아닙니다.")
        return email

class DynamicAnswerForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        if questions:
            for question in questions:
                field_name = f'question_{question.id}'
                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 5,
                        'maxlength': question.max_length
                    }),
                    required=question.is_required,
                    max_length=question.max_length
                ) 