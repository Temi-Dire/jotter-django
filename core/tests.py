import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerification

PASSWORD = 'Str0ng-pass-123'


def code_from_last_email():
    return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)


class RegistrationFlowTests(TestCase):
    def register(self, username='ada', email='ada@example.com'):
        return self.client.post(reverse('register'), {
            'first_name': 'Ada', 'last_name': 'Obi', 'username': username,
            'email': email, 'password1': PASSWORD, 'password2': PASSWORD,
        })

    def test_register_sends_code_and_goes_to_verify(self):
        response = self.register()
        self.assertRedirects(response, reverse('verify_email'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ada@example.com', mail.outbox[0].to)
        self.assertFalse(User.objects.get(username='ada').verification.is_verified)

    def test_correct_code_verifies_and_logs_in(self):
        self.register()
        response = self.client.post(reverse('verify_email'), {'code': code_from_last_email()})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.get(username='ada').verification.is_verified)
        self.assertContains(self.client.get(reverse('dashboard')), 'Hello, Ada')

    def test_wrong_code_is_rejected(self):
        self.register()
        code = code_from_last_email()
        wrong = '000000' if code != '000000' else '111111'
        response = self.client.post(reverse('verify_email'), {'code': wrong})
        self.assertContains(response, 'not correct')
        self.assertFalse(User.objects.get(username='ada').verification.is_verified)

    def test_expired_code_is_rejected(self):
        self.register()
        code = code_from_last_email()
        EmailVerification.objects.update(code_sent_at=timezone.now() - timedelta(minutes=11))
        response = self.client.post(reverse('verify_email'), {'code': code})
        self.assertContains(response, 'expired')

    def test_too_many_attempts_locks_code(self):
        self.register()
        code = code_from_last_email()
        EmailVerification.objects.update(attempts=5)
        response = self.client.post(reverse('verify_email'), {'code': code})
        self.assertContains(response, 'Too many wrong attempts')

    def test_duplicate_email_is_rejected(self):
        self.register()
        self.client.post(reverse('logout'))
        self.client.session.flush()
        response = self.register(username='ada2', email='ADA@example.com')
        self.assertContains(response, 'already exists')

    def test_resend_waits_then_sends(self):
        self.register()
        self.client.post(reverse('resend_otp'))
        self.assertEqual(len(mail.outbox), 1)  # too soon
        EmailVerification.objects.update(code_sent_at=timezone.now() - timedelta(seconds=61))
        self.client.post(reverse('resend_otp'))
        self.assertEqual(len(mail.outbox), 2)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bola', 'bola@example.com', PASSWORD, first_name='Bola')

    def test_unverified_user_is_sent_to_verify(self):
        response = self.client.post(reverse('login'), {'username': 'bola', 'password': PASSWORD})
        self.assertRedirects(response, reverse('verify_email'))
        self.assertEqual(len(mail.outbox), 1)

    def test_verified_user_can_log_in_with_email(self):
        EmailVerification.objects.create(user=self.user, is_verified=True)
        response = self.client.post(reverse('login'), {'username': 'bola@example.com', 'password': PASSWORD})
        self.assertRedirects(response, reverse('dashboard'))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse('login'), {'username': 'bola', 'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'correct username')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_creates_post(self):
        EmailVerification.objects.create(user=self.user, is_verified=True)
        self.client.force_login(self.user)
        self.client.post(reverse('dashboard'), {'title': 'First post', 'body': 'Hello'})
        self.assertEqual(self.user.posts.count(), 1)
        self.assertContains(self.client.get(reverse('home')), 'First post')

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
