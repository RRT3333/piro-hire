from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import Applicant

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # username 필드에 이메일이 들어올 수 있으므로 둘 다 체크
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