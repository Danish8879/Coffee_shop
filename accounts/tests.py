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
