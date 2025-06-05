from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import Applicant

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 로그인은 이메일을 기준으로만 조회합니다
            user = Applicant.objects.get(Q(email=username))
            if user.check_password(password):
                return user
        except Applicant.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Applicant.objects.get(pk=user_id)
        except Applicant.DoesNotExist:
            return None 