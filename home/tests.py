from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    # Confirm the home page loads and links to all three categories.
    def test_home_page_links_to_categories(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        for slug in ('coffee-beans', 'canned-coffee', 'brewing-equipment'):
            self.assertContains(response, reverse('product_list_by_category', args=[slug]))

    # Confirm visitors see Login and Sign up, and logged-in users see their account links.
    def test_navigation_depends_on_login(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('login'))
        self.assertNotContains(response, reverse('orders:list'))

        user = User.objects.create_user(username='student@example.com', password='x', first_name='Student')
        self.client.force_login(user)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Welcome, Student')
        self.assertContains(response, reverse('orders:list'))
        self.assertContains(response, reverse('profile'))
