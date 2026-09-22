from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountEdgeCaseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@example.com', email='student@example.com', password='Strong-pass-123',
        )

    # Confirm every new user gets exactly one profile automatically.
    def test_profile_created_by_signal(self):
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
        self.assertFalse(self.user.profile.is_email_verified)

    # Confirm mismatched passwords are rejected at signup.
    def test_signup_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'A', 'last_name': 'B', 'email': 'new@example.com',
            'password1': 'Strong-pass-123', 'password2': 'Different-pass-456',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='new@example.com').exists())

    # Confirm a wrong password does not log the user in.
    def test_login_wrong_password(self):
        response = self.client.post(reverse('login'), {'username': 'student@example.com', 'password': 'wrong'})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    # Confirm login ignores an unsafe external "next" address.
    def test_login_ignores_external_next(self):
        response = self.client.post(reverse('login'), {
            'username': 'student@example.com', 'password': 'Strong-pass-123', 'next': 'https://evil.example.com/',
        })

        self.assertRedirects(response, reverse('home'))

    # Confirm the verification email can be resent, and not once the email is verified.
    def test_resend_verification(self):
        self.client.force_login(self.user)
        self.client.post(reverse('resend_verification'))
        self.assertEqual(len(mail.outbox), 1)

        Profile.objects.filter(user=self.user).update(is_email_verified=True)
        self.client.post(reverse('resend_verification'))
        self.assertEqual(len(mail.outbox), 1)

    # Confirm a verification link only works once.
    def test_verification_link_single_use(self):
        self.client.force_login(self.user)
        self.client.post(reverse('resend_verification'))
        token = Profile.objects.get(user=self.user).email_token

        self.client.get(reverse('verify_email', args=[token]))
        self.assertEqual(self.client.get(reverse('verify_email', args=[token])).status_code, 404)

    # Confirm password reset for an unknown email shows the same page and sends nothing.
    def test_password_reset_unknown_email(self):
        response = self.client.post(reverse('password_reset'), {'email': 'nobody@example.com'})

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    # Confirm an invalid password reset link shows the expired message.
    def test_invalid_reset_link(self):
        response = self.client.get(reverse('password_reset_confirm', args=['bad', 'bad-token']))

        self.assertContains(response, 'Link expired')

    # Confirm GET logout is not allowed, so a link cannot log users out.
    def test_logout_get_not_allowed(self):
        self.client.force_login(self.user)
        self.client.get(reverse('logout'))

        self.assertIn('_auth_user_id', self.client.session)
