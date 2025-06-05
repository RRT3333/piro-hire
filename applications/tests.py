from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Applicant, Application, RecruitmentSettings


class IndexViewTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.recruitment = RecruitmentSettings.objects.create(
            application_start_date=now - timezone.timedelta(days=1),
            application_end_date=now + timezone.timedelta(days=1),
            interview_start_date=now,
            interview_end_date=now,
            recruitment_notice="",
        )
        self.applicant = Applicant.objects.create_user(
            email="test@example.com", password="test", name="Test"
        )
        Application.objects.create(
            applicant=self.applicant, recruitment_settings=self.recruitment
        )

    def test_has_application_context_true_when_application_exists(self):
        self.client.login(username="test@example.com", password="test")
        response = self.client.get(reverse("applications:index"))
        self.assertTrue(response.context["has_application"])

