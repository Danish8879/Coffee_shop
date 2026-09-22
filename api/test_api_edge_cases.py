from django.contrib.auth.models import User
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product

ORDER_DETAILS = {
    'first_name': 'Student', 'last_name': 'User', 'email': 'student@example.com',
    'address': '123 College Road', 'phone': '9876543210', 'payment_method': 'cod',
}


class ApiEdgeCaseTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student@example.com', email='student@example.com', password='x')
        self.staff = User.objects.create_user(username='staff@example.com', password='x', is_staff=True)
        self.can = Product.objects.get(name='Spanish Latte')
        self.bean = Product.objects.get(name='Monsoon Malabar')

    def _order(self, items, user=None):
        self.client.force_authenticate(user or self.user)
        return self.client.post('/api/orders/', {**ORDER_DETAILS, 'items': items}, format='json')

    # Confirm the product detail shows its category and option flag.
    def test_product_detail_fields(self):
        data = self.client.get(f'/api/products/{self.bean.id}/').data

        self.assertEqual(data['category']['slug'], 'coffee-beans')
        self.assertTrue(data['has_bean_options'])
        self.assertTrue(data['in_stock'])

    # Confirm the product list is paginated.
    def test_product_list_is_paginated(self):
        data = self.client.get('/api/products/').data

        self.assertEqual(data['count'], 10)
        self.assertIn('next', data)

    # Confirm registering through the API sends the verification email.
    def test_register_sends_verification_email(self):
        self.client.post('/api/auth/register/', {
            'first_name': 'A', 'last_name': 'B', 'email': 'api@example.com', 'password': 'Strong-pass-123',
        })

        self.assertEqual(len(mail.outbox), 1)

    # Confirm the email shown on the profile cannot be changed through the API.
    def test_profile_email_is_read_only(self):
        self.client.force_authenticate(self.user)
        self.client.patch('/api/profile/', {'email': 'changed@example.com'})

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'student@example.com')

    # Confirm quantity limits and unknown products are rejected.
    def test_invalid_order_items(self):
        self.assertEqual(self._order([{'product': self.can.id, 'quantity': 21}]).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._order([{'product': self.can.id, 'quantity': 0}]).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._order([{'product': 99999, 'quantity': 1}]).status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm hidden products cannot be ordered through the API.
    def test_unavailable_product_cannot_be_ordered(self):
        Product.objects.filter(id=self.can.id).update(is_available=False)

        self.assertEqual(self._order([{'product': self.can.id, 'quantity': 1}]).status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm an invalid bean weight is rejected.
    def test_invalid_bean_weight(self):
        response = self._order([{'product': self.bean.id, 'quantity': 1, 'grind': 'whole-beans', 'weight': 300}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm a customer cannot cancel or pay for someone else's order.
    def test_cannot_touch_other_users_order(self):
        order_id = self._order([{'product': self.can.id, 'quantity': 1}]).data['id']
        other = User.objects.create_user(username='other@example.com', password='x')
        self.client.force_authenticate(other)

        self.assertEqual(self.client.post(f'/api/orders/{order_id}/cancel/').status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(f'/api/orders/{order_id}/pay/').status_code, status.HTTP_404_NOT_FOUND)

    # Confirm staff cancelling through the status endpoint returns stock.
    def test_staff_cancel_restores_stock(self):
        order_id = self._order([{'product': self.can.id, 'quantity': 3}]).data['id']
        stock_after_order = Product.objects.get(id=self.can.id).stock

        self.client.force_authenticate(self.staff)
        response = self.client.post(f'/api/orders/{order_id}/status/', {'status': 'cancelled'})

        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(Product.objects.get(id=self.can.id).stock, stock_after_order + 3)

    # Confirm an unknown status value is rejected.
    def test_unknown_status(self):
        order_id = self._order([{'product': self.can.id, 'quantity': 1}]).data['id']
        self.client.force_authenticate(self.staff)

        response = self.client.post(f'/api/orders/{order_id}/status/', {'status': 'shipped'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Confirm orders cannot be edited or deleted through the API.
    def test_orders_cannot_be_edited_or_deleted(self):
        order_id = self._order([{'product': self.can.id, 'quantity': 1}]).data['id']

        self.assertEqual(self.client.patch(f'/api/orders/{order_id}/', {'total_amount': '1.00'}).status_code, 405)
        self.assertEqual(self.client.delete(f'/api/orders/{order_id}/').status_code, 405)

    # Confirm an invalid token is rejected.
    def test_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token not-a-real-token')

        self.assertEqual(self.client.get('/api/orders/').status_code, status.HTTP_401_UNAUTHORIZED)
