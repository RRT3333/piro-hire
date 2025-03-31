from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Applicant, Application, Answer, Question
import re

class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['name', 'phone_number', 'email', 'birth_date', 'university', 'major', 'grade', 'academic_status']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'academic_status': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'email': '인증 코드가 발송될 이메일 주소입니다.',
            'phone_number': '연락 가능한 휴대폰 번호를 입력해주세요.',
            'grade': '현재 학년을 선택해주세요.',
            'academic_status': '현재 학적 상태를 선택해주세요.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['phone_number'].widget.attrs.update({'class': 'form-control'})
        self.fields['birth_date'].widget.attrs.update({'class': 'form-control'})
        self.fields['university'].widget.attrs.update({'class': 'form-control'})
        self.fields['major'].widget.attrs.update({'class': 'form-control'})

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # 전화번호 형식 검증
            phone_number = re.sub(r'[^0-9]', '', phone_number)
            if not re.match(r'^01[016789][0-9]{7,8}$', phone_number):
                raise forms.ValidationError('올바른 전화번호 형식이 아닙니다.')
        return phone_number

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
    class Meta:
        model = Application
        fields = ['interview_sat_morning', 'interview_sat_afternoon', 'interview_sun_morning', 'interview_sun_afternoon']
        labels = {
            'interview_sat_morning': '토요일 오전 (10:00 ~ 12:00)',
            'interview_sat_afternoon': '토요일 오후 (14:00 ~ 17:00)',
            'interview_sun_morning': '일요일 오전 (10:00 ~ 12:00)',
            'interview_sun_afternoon': '일요일 오후 (14:00 ~ 17:00)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input'

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
        if not Applicant.objects.filter(email=email).exists():
            raise ValidationError('입력하신 이메일로 등록된 계정을 찾을 수 없습니다.')
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

class FindEmailForm(forms.Form):
    name = forms.CharField(
        label='이름',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label='전화번호',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '예: 010-1234-5678'})
    )

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='이메일',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

class PasswordResetConfirmForm(forms.Form):
    new_password1 = forms.CharField(
        label='새 비밀번호',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='8자 이상의 영문, 숫자, 특수문자를 포함해주세요.'
    )
    new_password2 = forms.CharField(
        label='새 비밀번호 확인',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('비밀번호가 일치하지 않습니다.')
            
            # 비밀번호 복잡도 검증
            if len(password1) < 8:
                raise forms.ValidationError('비밀번호는 8자 이상이어야 합니다.')
            if not any(char.isdigit() for char in password1):
                raise forms.ValidationError('비밀번호는 숫자를 포함해야 합니다.')
            if not any(char.isalpha() for char in password1):
                raise forms.ValidationError('비밀번호는 영문자를 포함해야 합니다.')
            if not any(not char.isalnum() for char in password1):
                raise forms.ValidationError('비밀번호는 특수문자를 포함해야 합니다.')

        return cleaned_data

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='이메일',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '이메일 주소를 입력하세요'})
    )
    password = forms.CharField(
        label='비밀번호',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '비밀번호를 입력하세요'})
    )

class SignUpForm(UserCreationForm):
    class Meta:
        model = Applicant
        fields = [
            'photo', 'email', 'name', 'phone_number', 'birth_date',
            'university', 'major', 'grade', 'academic_status'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'photo': '3x4cm 사진을 업로드해주세요.',
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('프로필 사진은 5MB를 초과할 수 없습니다.')
            
            if not photo.content_type.startswith('image/'):
                raise ValidationError('이미지 파일만 업로드 가능합니다.')
        return photo

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Applicant.objects.filter(email=email).exists():
            raise ValidationError('이미 사용 중인 이메일 주소입니다.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['answer_text']
        widgets = {
            'answer_text': forms.Textarea(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.question:
            self.fields['answer_text'].label = self.instance.question.question_text 