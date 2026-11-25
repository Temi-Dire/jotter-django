import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):  # two underscores on each side
        return self.title


class EmailVerification(models.Model):
    """Tracks whether a user has confirmed their email, and their current OTP code."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification',
    )
    is_verified = models.BooleanField(default=False)
    # We store a hash of the code, never the code itself (like a password).
    code_hash = models.CharField(max_length=128, blank=True)
    code_sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        status = 'verified' if self.is_verified else 'not verified'
        return f'{self.user.username} ({status})'

    def new_code(self):
        """Create a fresh 6-digit code, save its hash, and return the plain code to email."""
        code = f'{secrets.randbelow(1_000_000):06d}'
        self.code_hash = make_password(code)
        self.code_sent_at = timezone.now()
        self.attempts = 0
        self.save()
        return code

    def is_expired(self):
        if not self.code_sent_at:
            return True
        return timezone.now() > self.code_sent_at + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    def seconds_until_resend(self):
        if not self.code_sent_at:
            return 0
        ready_at = self.code_sent_at + timedelta(seconds=settings.OTP_RESEND_SECONDS)
        return max(0, int((ready_at - timezone.now()).total_seconds()))

    def check_code(self, code):
        """Return (ok, error_message)."""
        if not self.code_hash or self.is_expired():
            return False, 'This code has expired. Request a new one below.'
        if self.attempts >= settings.OTP_MAX_ATTEMPTS:
            return False, 'Too many wrong attempts. Request a new code below.'
        if check_password(code, self.code_hash):
            self.is_verified = True
            self.code_hash = ''
            self.attempts = 0
            self.save()
            return True, ''
        self.attempts += 1
        self.save()
        left = settings.OTP_MAX_ATTEMPTS - self.attempts
        return False, f'That code is not correct. {left} attempt(s) left.'
