import re

from django.core import mail
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountTests(TestCase):
    signup_data = {
        'first_name': 'Student',
        'last_name': 'User',
        'email': 'Student@Example.com',
        'password1': 'Strong-pass-123',
        'password2': 'Strong-pass-123',
    }

    # Confirm signup stores a lower-case email and creates a profile.
    def test_signup_creates_user_and_profile(self):
        response = self.client.post(reverse('register'), self.signup_data)

        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='student@example.com')
        self.assertEqual(user.email, 'student@example.com')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    # Confirm the same email with different capitalisation cannot register twice.
    def test_duplicate_email_is_rejected(self):
        self.client.post(reverse('register'), self.signup_data)
        data = dict(self.signup_data, email='STUDENT@example.com')
        response = self.client.post(reverse('register'), data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    # Confirm login ignores email capitalisation.
    def test_login_is_case_insensitive(self):
        User.objects.create_user(username='student@example.com', email='student@example.com', password='Strong-pass-123')
        response = self.client.post(reverse('login'), {
            'username': 'STUDENT@Example.com',
            'password': 'Strong-pass-123',
        })

        self.assertRedirects(response, reverse('home'))

    # Confirm logout works through a POST request.
    def test_logout_with_post(self):
        user = User.objects.create_user(username='student@example.com', password='Strong-pass-123')
        self.client.force_login(user)
        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, '/')
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileAndEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@example.com', email='student@example.com', password='Strong-pass-123',
        )

    # Confirm the profile page requires login and saves edits.
    def test_edit_profile(self):
        self.assertEqual(self.client.get(reverse('profile')).status_code, 302)

        self.client.force_login(self.user)
        response = self.client.post(reverse('profile'), {
            'first_name': 'New', 'last_name': 'Name', 'phone': '9876543210', 'address': 'Hostel 4',
        })

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.profile.address, 'Hostel 4')

    # Confirm an invalid phone number is rejected on the profile page.
    def test_profile_rejects_bad_phone(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('profile'), {
            'first_name': 'New', 'last_name': 'Name', 'phone': 'abc', 'address': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('phone', response.context['profile_form'].errors)

    # Confirm signup sends a verification email and its link verifies the address.
    def test_signup_sends_verification_email(self):
        self.client.post(reverse('register'), dict(AccountTests.signup_data, email='new@example.com'))

        self.assertEqual(len(mail.outbox), 1)
        profile = Profile.objects.get(user__username='new@example.com')
        self.assertIn(profile.email_token, mail.outbox[0].body)

        self.client.get(reverse('verify_email', args=[profile.email_token]))
        profile.refresh_from_db()
        self.assertTrue(profile.is_email_verified)
        self.assertIsNone(profile.email_token)

    # Confirm an unknown verification token is rejected.
    def test_invalid_verification_token(self):
        response = self.client.get(reverse('verify_email', args=['not-a-real-token']))

        self.assertEqual(response.status_code, 404)

    # Confirm the full password reset flow lets the user set a new password.
    def test_password_reset_flow(self):
        response = self.client.post(reverse('password_reset'), {'email': 'student@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        reset_link = re.search(r'https?://[^/]+(/\S+)', mail.outbox[0].body).group(1)
        response = self.client.get(reset_link, follow=True)
        response = self.client.post(response.redirect_chain[-1][0], {
            'new_password1': 'Another-pass-456', 'new_password2': 'Another-pass-456',
        })

        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Another-pass-456'))

    # Confirm login sends the user back to the page they came from.
    def test_login_redirects_to_next(self):
        response = self.client.post(f"{reverse('login')}?next=/orders/", {
            'username': 'student@example.com', 'password': 'Strong-pass-123', 'next': '/orders/',
        })

        self.assertRedirects(response, '/orders/')
