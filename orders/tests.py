from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product

from .models import Order


class CheckoutTests(TestCase):
    # Create a user and product that can be used in checkout tests.
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='test-password',
        )
        category, _ = Category.objects.get_or_create(name='Coffee Beans', slug='coffee-beans')
        self.product = Product.objects.create(
            name='Test Coffee',
            category=category,
            description='A test product.',
            price=Decimal('12.50'),
            image='products/test-coffee.jpg',
        )

    # Confirm checkout creates an order, saves price snapshots, and clears the cart.
    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): {'quantity': 2}}
        session.save()

        response = self.client.post(reverse('orders:checkout'), {
            'first_name': 'Student',
            'last_name': 'User',
            'email': 'student@example.com',
            'address': '123 College Road',
            'phone': '9876543210',
        })

        order = Order.objects.get(user=self.user)
        order_item = order.items.get()
        self.assertRedirects(response, reverse('orders:success', args=[order.id]))
        self.assertEqual(order.total_amount, Decimal('25.00'))
        self.assertEqual(order_item.product_name, 'Test Coffee')
        self.assertEqual(order_item.price, Decimal('12.50'))
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.grind, 'whole-beans')
        self.assertEqual(order_item.weight, 250)
        self.assertNotIn('cart', self.client.session)
