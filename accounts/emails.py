import uuid

from django.core.mail import send_mail
from django.urls import reverse


# Give the user a fresh verification token and email them the link to verify their address.
def send_verification_email(request, user):
    profile = user.profile
    profile.email_token = uuid.uuid4().hex
    profile.save(update_fields=['email_token', 'updated_at'])

    link = request.build_absolute_uri(reverse('verify_email', args=[profile.email_token]))
    send_mail(
        subject='Verify your Coffee E-commerce account',
        message=f'Hi {user.first_name or user.username},\n\nPlease verify your email address by opening this link:\n{link}\n',
        from_email=None,
        recipient_list=[user.email],
    )
