from django.conf import settings
from django.core.mail import send_mail

from .models import EmailVerification


def send_otp(user):
    """Create a new code for this user and email it to them."""
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    code = verification.new_code()
    send_mail(
        subject='Your Jotter verification code',
        message=(
            f'Hi {user.first_name or user.username},\n\n'
            f'Your verification code is: {code}\n\n'
            f'It expires in {settings.OTP_EXPIRY_MINUTES} minutes. '
            'If you did not create an account, you can ignore this email.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
