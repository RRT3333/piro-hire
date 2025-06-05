from django.test import TestCase
from django.utils import timezone

from .models import Applicant, RecruitmentSettings, Application


class ApplicationModelTests(TestCase):
    def test_submit_updates_status_and_time(self):
        """Application.submit should set status and submitted_at."""
        applicant = Applicant.objects.create_user(
            email="applicant@example.com",
            password="testpass",
            name="Test User",
            phone_number="01012345678",
        )

        now = timezone.now()
        recruitment = RecruitmentSettings.objects.create(
            application_start_date=now,
            application_end_date=now,
            interview_start_date=now,
            interview_end_date=now,
            recruitment_notice="Notice",
        )

        application = Application.objects.create(
            applicant=applicant,
            recruitment_settings=recruitment,
        )

        application.submit()

        self.assertEqual(application.status, "submitted")
        self.assertIsNotNone(application.submitted_at)
